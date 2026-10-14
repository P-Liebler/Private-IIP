from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from app.backtesting.baselines import ranking
from app.backtesting.metrics import metrics
from app.backtesting.validation import validate_execution
from app.schemas.pit import BacktestInput

D = Decimal
ENGINE_VERSION = "long-only-v1"


def run_backtest(
    dataset: dict[str, Any], config: BacktestInput, compare: bool = True
) -> dict[str, Any]:
    """Pure simulation from a pinned dataset. Decision rows never see fill data."""
    cash = config.initial_capital
    positions: dict[str, Decimal] = {}
    pending: list[dict[str, Any]] = []
    fills = []
    orders = []
    signals = []
    equity = []
    warnings = []
    costs = D(0)
    traded = D(0)
    receivables = []
    applied = set()
    configuration = dataset["configuration"]
    market = dataset["market"]
    benchmark_id = configuration["benchmark_id"]
    features = dataset["rows"]
    sessions = sorted(market)
    if not sessions or not any(r["eligible"] for r in features):
        return {
            "status": "REJECTED",
            "data_context": configuration.get("data_context", "USER_ARCHIVE"),
            "warnings": ["NO_ELIGIBLE_DATA / HISTORICAL_AVAILABILITY_UNVERIFIED"],
            "signals": [],
            "orders": [],
            "fills": [],
            "equity": [],
            "metrics": metrics([], cash, D(0), D(0), 0, config.risk_free_annual),
        }
    for index, day in enumerate(sessions):
        bars = market.get(day, {})
        common_cutoff = max(
            (datetime.fromisoformat(b["information_cutoff_at"]) for b in bars.values()),
            default=None,
        )
        # Corporate action entitlement uses shares held before today's fills.
        for iid, quantity in list(positions.items()):
            for action in dataset["actions"].get(iid, []):
                if action["date"] != day or action["id"] in applied:
                    continue
                applied.add(action["id"])
                if action["type"] == "SPLIT":
                    positions[iid] *= D(action["ratio"])
                    for order in pending:
                        if order["instrument_id"] == iid:
                            order["quantity"] = str(D(order["quantity"]) * D(action["ratio"]))
                elif action["type"] == "DIVIDEND":
                    if not action["payment_date"]:
                        warnings.append("DIVIDEND_PAYMENT_UNAVAILABLE")
                        continue
                    receivables.append(
                        {
                            "instrument_id": iid,
                            "amount": quantity * D(action["cash_amount"]),
                            "date": action["payment_date"],
                            "currency": action["currency"],
                        }
                    )
        for payment in list(receivables):
            if payment["date"] <= day:
                bar = bars.get(payment["instrument_id"])
                if bar and bar.get("fx") is not None and bar["currency"] == payment["currency"]:
                    cash += payment["amount"] * D(bar["fx"])
                    receivables.remove(payment)
                else:
                    warnings.append("MISSING_DIVIDEND_FX")
        for order in list(pending):
            if order["execution_date"] != day:
                continue
            pending.remove(order)
            iid = order["instrument_id"]
            bar = bars.get(iid)
            field = "open" if config.execution_policy == "NEXT_OPEN" else "close"
            conversion = (
                bar.get("fill_fx", {}).get(
                    field, {"rate": bar.get("fx"), "provenance": bar.get("fx_provenance")}
                )
                if bar
                else {}
            )
            fill_rate = conversion.get("rate")
            price = D(bar[field]) if bar and bar.get(field) is not None else None
            if (
                bar is None
                or fill_rate is None
                or ("action_coverage" in bar and bar["action_coverage"] is None)
            ):
                order["status"] = "NO_FILL"
                warnings.append("EXECUTION_UNAVAILABLE")
                continue
            timestamp = datetime.fromisoformat(bar[field + "_timestamp"])
            try:
                validate_execution(
                    datetime.fromisoformat(order["signal_generated_at"]),
                    datetime.fromisoformat(order["information_cutoff_at"]),
                    datetime.fromisoformat(order["tradable_at"]),
                    timestamp,
                    price,
                    bar["is_session"],
                )
            except ValueError as error:
                order["status"] = "NO_FILL"
                warnings.append(str(error))
                continue
            assert price is not None
            sign = D(1) if order["side"] == "BUY" else D(-1)
            adjustment = config.spread_bps / 20000 + config.slippage_bps / 10000
            adjusted = price * (1 + sign * adjustment) * D(fill_rate)
            qty = D(order["quantity"])
            if order["side"] == "BUY":
                qty = min(qty, max(D(0), (cash - config.commission) / adjusted))
            else:
                qty = min(qty, positions.get(iid, D(0)))
            if qty <= 0:
                order["status"] = "NO_FILL"
                warnings.append("INSUFFICIENT_CASH_OR_POSITION")
                continue
            amount = qty * adjusted
            if order["side"] == "SELL" and cash + amount < config.commission:
                order["status"] = "NO_FILL"
                warnings.append("INSUFFICIENT_CASH_FOR_COMMISSION")
                continue
            implicit = qty * price * D(fill_rate) * adjustment
            if order["side"] == "BUY":
                cash -= amount + config.commission
                positions[iid] = positions.get(iid, D(0)) + qty
            else:
                cash += amount - config.commission
                positions[iid] -= qty
            costs += config.commission + implicit
            traded += qty * price * D(fill_rate)
            order["status"] = "FILLED" if qty == D(order["quantity"]) else "PARTIAL_FILL"
            fills.append(
                {
                    **order,
                    "quantity": str(qty),
                    "execution_price": str(price),
                    "base_execution_price": str(adjusted),
                    "execution_price_timestamp": timestamp.isoformat(),
                    "price_version_id": bar["id"],
                    "raw_ingestion_id": bar["raw_ingestion_id"],
                    "fx": conversion["provenance"],
                    "commission": str(config.commission),
                    "spread_slippage_cost": str(implicit),
                }
            )
        value = cash
        incomplete = False
        for iid, quantity in positions.items():
            if quantity == 0:
                continue
            bar = bars.get(iid)
            if (
                not bar
                or bar.get("fx") is None
                or ("action_coverage" in bar and bar["action_coverage"] is None)
            ):
                incomplete = True
                warnings.append("MISSING_PRICE_OR_FX")
                continue
            value += quantity * D(bar["close"]) * D(bar["fx"])
        for p in receivables:
            bar = bars.get(p["instrument_id"])
            if not bar or bar.get("fx") is None:
                incomplete = True
            else:
                value += p["amount"] * D(bar["fx"])
        equity.append(
            {
                "date": day,
                "value": None if incomplete else str(value),
                "cash": str(cash),
                "positions": {k: str(v) for k, v in positions.items()},
                "receivables": len(receivables),
            }
        )
        rows = [r for r in features if r["date"] == day and r["eligible"]]
        if index % config.rebalance_sessions != 0 or incomplete:
            continue
        if config.strategy == "BENCHMARK_ONLY":
            chosen = [benchmark_id] if benchmark_id in bars else []
        else:
            chosen = ranking(rows, config.strategy, config.top_n)
        day_rows = [r for r in features if r["date"] == day]
        legitimate_exit = config.strategy == "EQUAL_WEIGHT" and not day_rows and bool(positions)
        if not chosen and not legitimate_exit:
            warnings.append("BASELINE_UNAVAILABLE")
            continue
        weight = min(config.max_position_weight, D(1) / len(chosen)) if chosen else D(0)
        # Quantity derives solely from signal-time close/FX, never tomorrow's open.
        targets = {}
        for iid in chosen:
            bar = bars.get(iid)
            if not bar or bar.get("fx") is None:
                warnings.append("SIGNAL_PRICE_OR_FX_UNAVAILABLE")
                continue
            targets[iid] = value * weight / (D(bar["close"]) * D(bar["fx"]))
        for iid in sorted(set(positions) | set(targets)):
            bar = bars.get(iid)
            if not bar:
                continue
            delta = targets.get(iid, D(0)) - positions.get(iid, D(0))
            if abs(delta) < D("0.00000001"):
                continue
            assert common_cutoff is not None
            signal = {
                "instrument_id": iid,
                "signal_generated_at": (common_cutoff + timedelta(microseconds=1)).isoformat(),
                "information_cutoff_at": common_cutoff.isoformat(),
                "tradable_at": bar["next_open_timestamp"],
                "execution_price_type": config.execution_policy,
                "execution_price_timestamp": None,
                "price_input_version_id": bar["id"],
            }
            signals.append(signal)
            order = {
                **signal,
                "execution_date": bar["next_session"],
                "quantity": str(abs(delta)),
                "side": "BUY" if delta > 0 else "SELL",
                "status": "PENDING",
            }
            orders.append(order)
            pending.append(order)
        # Free cash before buys without permitting leverage.
        pending.sort(key=lambda o: (o["execution_date"], o["side"] != "SELL", o["instrument_id"]))
    for order in pending:
        order["status"] = "NO_FILL"
        warnings.append("EXECUTION_OUTSIDE_WINDOW")
    benchmark_curve = None
    if compare and config.strategy != "BENCHMARK_ONLY":
        bc = config.model_copy(update={"strategy": "BENCHMARK_ONLY"})
        comparator = run_backtest(dataset, bc, False)
        if (
            comparator["status"] in {"STRICT_PIT_VALID", "RECONSTRUCTED_WITH_LIMITATIONS"}
            and comparator["fills"]
            and len(comparator["equity"]) == len(equity)
            and all(p["value"] is not None for p in comparator["equity"])
        ):
            benchmark_curve = [D(p["value"]) for p in comparator["equity"]]
        else:
            warnings.append("BENCHMARK_BASELINE_UNAVAILABLE")
    status = (
        "INCOMPLETE"
        if warnings
        else "STRICT_PIT_VALID"
        if configuration["availability_mode"] == "STRICT_PIT"
        else "RECONSTRUCTED_WITH_LIMITATIONS"
    )
    if dataset["quality"].get("excluded_observations", 0):
        status = "INCOMPLETE"
    computed_metrics = metrics(
        equity,
        config.initial_capital,
        traded,
        costs,
        len(fills),
        config.risk_free_annual,
        benchmark_curve,
    )
    if not fills:
        for name in (
            "Total Return",
            "CAGR",
            "Sharpe",
            "Sortino",
            "Volatility",
            "Alpha",
            "Beta",
            "Win Rate",
            "Excess Return",
        ):
            computed_metrics[name] = None
        computed_metrics["status"] = "INSUFFICIENT_DATA"
    total = dataset["quality"].get("total_observations")
    valid = dataset["quality"].get("valid_observations")
    computed_metrics["Coverage"] = str(D(valid) / D(total)) if total and valid is not None else None
    computed_metrics["Missing Observations"] = dataset["quality"].get("excluded_observations")
    return {
        "status": status,
        "data_context": configuration.get("data_context", "USER_ARCHIVE"),
        "engine_version": ENGINE_VERSION,
        "warnings": sorted(set(warnings)),
        "signals": signals,
        "orders": orders,
        "fills": fills,
        "equity": equity,
        "benchmark_equity": [str(v) for v in benchmark_curve] if benchmark_curve else None,
        "cash": str(cash),
        "positions": {k: str(v) for k, v in positions.items()},
        "metrics": computed_metrics,
    }
