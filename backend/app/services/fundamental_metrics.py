"""Deterministic, period-compatible P5 mathematics; all outputs carry input IDs."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.models import FundamentalFact

METRIC_RULE = "research-math-v1"


def unavailable(reason: str, inputs: list[str] | None = None) -> dict[str, Any]:
    return {
        "value": None,
        "status": "DATA_UNAVAILABLE",
        "reason": reason,
        "inputs": inputs or [],
        "rule_version": METRIC_RULE,
    }


def output(value: Decimal, facts: list[FundamentalFact], unit: str = "RATIO") -> dict[str, Any]:
    return {
        "value": str(value),
        "status": "AVAILABLE",
        "unit": unit,
        "inputs": [str(f.id) for f in facts],
        "period_end": str(max(f.period_end for f in facts)),
        "known_at": str(max(f.known_at for f in facts)),
        "retrieved_at": str(max(f.retrieved_at for f in facts)),
        "rule_version": METRIC_RULE,
    }


def compatible(facts: list[FundamentalFact], *, mixed: bool = False) -> bool:
    if not facts or any(f.value is None or f.validation_status == "REJECTED" for f in facts):
        return False
    money = {f.currency for f in facts if f.currency}
    if len(money) != 1:
        return False
    if mixed:
        return len({f.period_end for f in facts}) == 1
    return len({(f.period_start, f.period_end, f.period_type) for f in facts}) == 1


class FundamentalMetricsService:
    def __init__(self, facts: list[FundamentalFact]) -> None:
        self.facts = facts

    def cash_flow_series(self, period: str) -> list[tuple[Decimal, list[FundamentalFact]]]:
        groups: dict[tuple[object, ...], list[FundamentalFact]] = {}
        for fact in self.facts:
            if fact.period_type == period and fact.metric in {
                "free_cash_flow",
                "operating_cash_flow",
                "capex",
            }:
                groups.setdefault((fact.period_start, fact.period_end, fact.currency), []).append(
                    fact
                )
        result: list[tuple[Decimal, list[FundamentalFact]]] = []
        for rows in groups.values():
            reported = [f for f in rows if f.metric == "free_cash_flow"]
            operating = [f for f in rows if f.metric == "operating_cash_flow"]
            capex = [f for f in rows if f.metric == "capex"]
            derived = None
            if len(operating) == len(capex) == 1 and compatible([operating[0], capex[0]]):
                assert operating[0].value is not None and capex[0].value is not None
                if capex[0].value >= 0:
                    derived = operating[0].value - capex[0].value
            if len(reported) == 1 and reported[0].value is not None:
                if derived is None or reported[0].value == derived:
                    result.append((reported[0].value, reported))
            elif not reported and derived is not None:
                result.append((derived, [operating[0], capex[0]]))
        result.sort(key=lambda pair: pair[1][0].period_end)
        latest_end = max((f.period_end for rows in groups.values() for f in rows), default=None)
        if not result or result[-1][1][0].period_end != latest_end:
            return []
        if len({rows[0].currency for _, rows in result if rows[0].period_end == latest_end}) > 1:
            return []
        return result

    def latest(self, metric: str, period: str = "ANNUAL") -> FundamentalFact | None:
        rows = [f for f in self.facts if f.metric == metric and f.period_type == period]
        latest = max(rows, key=lambda f: (f.period_end, f.known_at), default=None)
        same_end = [f for f in rows if latest and f.period_end == latest.period_end]
        if len({(f.period_start, f.currency, f.unit) for f in same_end}) > 1:
            return None
        return latest

    def bundle(
        self, metrics: list[str], period: str = "ANNUAL", mixed: bool = False
    ) -> list[FundamentalFact]:
        rows = [
            self.latest(
                metric,
                "INSTANT"
                if mixed
                and metric
                in {
                    "total_assets",
                    "total_equity",
                    "total_debt",
                    "cash",
                    "current_assets",
                    "current_liabilities",
                    "inventory",
                }
                else period,
            )
            for metric in metrics
        ]
        return [r for r in rows if r is not None] if all(rows) else []

    def ratio(
        self,
        numerator: str,
        denominator: str,
        period: str = "ANNUAL",
        *,
        mixed: bool = False,
        positive: bool = True,
    ) -> dict[str, Any]:
        rows = self.bundle([numerator, denominator], period, mixed)
        if (
            not compatible(rows, mixed=mixed)
            or rows[1].value is None
            or (rows[1].value <= 0 if positive else rows[1].value == 0)
        ):
            return unavailable("Missing, incompatible inputs or undefined denominator")
        assert rows[0].value is not None
        return output(rows[0].value / rows[1].value, rows)

    def growth(self, metric: str, period: str) -> dict[str, Any]:
        if metric == "free_cash_flow":
            series = self.cash_flow_series(period)
            if not series:
                return unavailable("Missing comparable FCF periods")
            current_value, current_rows = series[-1]
            flow_current = current_rows[0]
            flow_previous = [
                (v, rows)
                for v, rows in series[:-1]
                if 350 <= (flow_current.period_end - rows[0].period_end).days <= 380
                and rows[0].currency == flow_current.currency
                and rows[0].period_start is not None
                and flow_current.period_start is not None
                and abs(
                    (flow_current.period_end - flow_current.period_start).days
                    - (rows[0].period_end - rows[0].period_start).days
                )
                <= 7
            ]
            if len(flow_previous) != 1 or flow_previous[0][0] <= 0:
                return unavailable("Missing/ambiguous FCF base or nonpositive prior FCF")
            return output(
                current_value / flow_previous[0][0] - 1, [*current_rows, *flow_previous[0][1]]
            )
        current = self.latest(metric, period)
        if current is None or current.period_start is None:
            return unavailable("Missing current duration")
        previous = [
            f
            for f in self.facts
            if f.metric == metric
            and f.period_type == period
            and 350 <= (current.period_end - f.period_end).days <= 380
            and f.period_start is not None
            and abs(
                (current.period_end - current.period_start).days
                - (f.period_end - f.period_start).days
            )
            <= 7
            and f.currency == current.currency
            and f.unit == current.unit
        ]
        if (
            len(previous) != 1
            or previous[0].value is None
            or previous[0].value <= 0
            or current.value is None
        ):
            return unavailable(
                "Missing/ambiguous comparable prior period or nonpositive growth base"
            )
        return output(current.value / previous[0].value - 1, [current, previous[0]])

    def ttm(self, metric: str) -> dict[str, Any]:
        if metric == "free_cash_flow":
            series = self.cash_flow_series("QUARTER")[-4:]
            rows = [pair[1][0] for pair in series]
            if (
                len(rows) != 4
                or len({f.currency for f in rows}) != 1
                or any(
                    right.period_start != left.period_end + timedelta(days=1)
                    for left, right in zip(rows, rows[1:], strict=False)
                )
            ):
                return unavailable("Four contiguous comparable FCF quarters required")
            return output(
                sum((v for v, _ in series), Decimal(0)),
                [f for _, inputs in series for f in inputs],
                "MONEY",
            )
        rows = sorted(
            [f for f in self.facts if f.metric == metric and f.period_type == "QUARTER"],
            key=lambda f: f.period_end,
        )[-4:]
        if (
            len(rows) != 4
            or len({f.currency for f in rows}) != 1
            or len({f.unit for f in rows}) != 1
            or any(f.period_start is None or f.value is None for f in rows)
        ):
            return unavailable("Four comparable discrete quarters required; YTD excluded")
        if any(
            right.period_start != left.period_end + timedelta(days=1)
            for left, right in zip(rows, rows[1:], strict=False)
        ):
            return unavailable("TTM gap or overlap")
        assert rows[0].period_start is not None
        if not 330 <= (rows[-1].period_end - rows[0].period_start).days + 1 <= 400:
            return unavailable("TTM duration incompatible")
        return output(
            sum((f.value for f in rows if f.value is not None), Decimal(0)), rows, rows[0].unit
        )

    def calculate(self, period: str = "ANNUAL") -> dict[str, dict[str, Any]]:
        result = {
            name: self.ratio(n, d, period, mixed=mixed)
            for name, n, d, mixed in [
                ("gross_margin", "gross_profit", "revenue", False),
                ("operating_margin", "operating_income", "revenue", False),
                ("net_margin", "net_income", "revenue", False),
                ("fcf_margin", "free_cash_flow", "revenue", False),
                ("ROE", "net_income", "total_equity", True),
                ("ROA", "net_income", "total_assets", True),
                ("debt_to_equity", "total_debt", "total_equity", True),
                ("current_ratio", "current_assets", "current_liabilities", True),
            ]
        }
        for name, metric in [
            ("revenue_growth_yoy", "revenue"),
            ("eps_growth_yoy", "eps_diluted"),
            ("fcf_growth_yoy", "free_cash_flow"),
        ]:
            result[name] = self.growth(metric, period)
        for name, names in [
            ("free_cash_flow", ["operating_cash_flow", "capex"]),
            ("net_debt", ["total_debt", "cash"]),
            ("quick_ratio", ["current_assets", "inventory", "current_liabilities"]),
            (
                "ROIC",
                [
                    "operating_income",
                    "income_tax",
                    "pretax_income",
                    "total_debt",
                    "total_equity",
                    "cash",
                ],
            ),
        ]:
            rows = self.bundle(names, period, mixed=name != "free_cash_flow")
            if not compatible(rows, mixed=name != "free_cash_flow"):
                result[name] = unavailable("Missing or incompatible required components")
                continue
            values = [f.value for f in rows]
            assert all(v is not None for v in values)
            a = [Decimal(str(v)) for v in values]
            if name == "free_cash_flow":
                result[name] = (
                    output(a[0] - a[1], rows, "MONEY")
                    if a[1] >= 0
                    else unavailable("Capex requires positive cash-outflow convention")
                )
            elif name == "net_debt":
                result[name] = output(a[0] - a[1], rows, "MONEY")
            elif name == "quick_ratio":
                result[name] = (
                    output((a[0] - a[1]) / a[2], rows)
                    if a[2] > 0
                    else unavailable("Nonpositive current liabilities")
                )
            else:
                capital = a[3] + a[4] - a[5]
                result[name] = (
                    output(a[0] * (1 - a[1] / a[2]) / capital, rows)
                    if capital > 0 and a[2] > 0 and 0 <= a[1] / a[2] <= 1
                    else unavailable("Undefined tax rate or invested capital")
                )
        if result["fcf_margin"]["value"] is None and result["free_cash_flow"]["value"] is not None:
            rows = self.bundle(["operating_cash_flow", "capex", "revenue"], period)
            if compatible(rows) and rows[2].value is not None and rows[2].value > 0:
                result["fcf_margin"] = output(
                    Decimal(result["free_cash_flow"]["value"]) / rows[2].value, rows
                )
        flows = self.cash_flow_series(period)
        if flows:
            result["free_cash_flow"] = output(flows[-1][0], flows[-1][1], "MONEY")
        else:
            result["free_cash_flow"] = unavailable("Missing FCF inputs or definition conflict")
        revenue = self.latest("revenue", period)
        if (
            flows
            and revenue
            and revenue.value is not None
            and revenue.value > 0
            and compatible([*flows[-1][1], revenue])
        ):
            result["fcf_margin"] = output(flows[-1][0] / revenue.value, [*flows[-1][1], revenue])
        else:
            result["fcf_margin"] = unavailable("Missing/incompatible FCF and revenue")
        return result


def valuation(
    facts: list[FundamentalFact], price: dict[str, Any] | None, as_of: date, share_class: str | None
) -> dict[str, dict[str, Any]]:
    names = [
        "market_cap",
        "enterprise_value",
        "P/E",
        "Forward P/E",
        "P/S",
        "P/B",
        "EV/EBITDA",
        "EV/Revenue",
        "EV/FCF",
        "FCF Yield",
        "Earnings Yield",
        "PEG",
    ]
    result = {name: unavailable("Required verified input unavailable") for name in names}
    service = FundamentalMetricsService(facts)
    shares = service.latest("shares_outstanding", "INSTANT")
    if (
        price is None
        or shares is None
        or shares.value is None
        or shares.value <= 0
        or (as_of - shares.period_end).days > 550
        or not share_class
        or shares.evidence.get("share_class") != share_class
        or shares.evidence.get("split_basis_date") != str(price["date"])
        or (as_of - price["date"]).days > 7
    ):
        result["market_cap"] = unavailable(
            "Missing/stale price or unverified class/share split basis"
        )
        return result
    cap = Decimal(str(price["close"])) * shares.value

    def value(number: Decimal, rows: list[FundamentalFact], unit: str = "RATIO") -> dict[str, Any]:
        return {
            **output(number, rows, unit),
            "price_version": str(price["id"]),
            "price_date": str(price["date"]),
            "as_of": str(as_of),
        }

    result["market_cap"] = value(cap, [shares], "MONEY")

    def annual(metric: str) -> FundamentalFact | None:
        fact = service.latest(metric)
        if fact and fact.currency == price["currency"] and (as_of - fact.period_end).days <= 550:
            return fact
        return None

    for name, metric in [("P/E", "net_income"), ("P/S", "revenue"), ("P/B", "total_equity")]:
        f = service.latest(metric, "INSTANT") if metric == "total_equity" else annual(metric)
        if (
            f
            and f.currency == price["currency"]
            and f.value is not None
            and f.value > 0
            and (as_of - f.period_end).days <= 550
        ):
            result[name] = value(cap / f.value, [shares, f])
    ni = annual("net_income")
    if ni and ni.value is not None:
        result["Earnings Yield"] = value(ni.value / cap, [shares, ni])
    flows = service.cash_flow_series("ANNUAL")
    fcf_inputs: list[FundamentalFact] = []
    fcf_value: Decimal | None = None
    if (
        flows
        and flows[-1][1][0].currency == price["currency"]
        and (as_of - flows[-1][1][0].period_end).days <= 550
    ):
        fcf_value, fcf_inputs = flows[-1]
        result["FCF Yield"] = value(fcf_value / cap, [shares, *fcf_inputs])
    components = [
        service.latest(m, "INSTANT")
        for m in ["total_debt", "cash", "preferred_equity", "minority_interest"]
    ]
    if all(components):
        rows = [f for f in components if f is not None]
        if (
            compatible(rows)
            and rows[0].currency == price["currency"]
            and (as_of - rows[0].period_end).days <= 550
        ):
            a = [Decimal(str(f.value)) for f in rows]
            ev = cap + a[0] - a[1] + a[2] + a[3]
            result["enterprise_value"] = value(ev, [shares, *rows], "MONEY")
            if fcf_value is not None and fcf_value > 0:
                result["EV/FCF"] = value(ev / fcf_value, [shares, *rows, *fcf_inputs])
            for name, metric in [
                ("EV/EBITDA", "ebitda"),
                ("EV/Revenue", "revenue"),
            ]:
                f = annual(metric)
                if f and f.value is not None and f.value > 0:
                    result[name] = value(ev / f.value, [shares, *rows, f])
    return result
