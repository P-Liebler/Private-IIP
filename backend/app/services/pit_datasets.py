import asyncio
import hashlib
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from statistics import stdev
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.features import FEATURE_VERSION
from app.backtesting.validation import available
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import (
    ActionCoverageReview,
    DatasetVersion,
    FeatureSnapshot,
    FxRateVersion,
    Instrument,
    UniverseMembershipVersion,
)
from app.schemas.pit import DatasetInput
from app.services.fundamentals import digest
from app.services.market_calendar import MarketCalendarService
from app.services.market_queries import MarketQueryService
from app.services.pit_evidence import ENTITIES, EvidenceService
from app.services.pit_features import FeatureSnapshotService, json_value
from app.services.pit_universe import UniverseService
from app.services.raw_ingestion import RawIngestionService


@lru_cache(maxsize=1)
def code_manifest() -> dict[str, Any]:
    files = sorted(Path("app").rglob("*.py"))
    return {
        "git_commit": get_settings().code_commit,
        "code_hash": digest({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}),
        "dependencies": Path("requirements.lock").read_text(),
        "supporting_dependencies": Path("requirements-assistant.lock").read_text(),
        "random_seed": None,
        "code_snapshot_contract": "PROCESS_FIRST_BUILD; restart after code changes",
    }


class DatasetBuilder:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.calendar = MarketCalendarService()
        self.features = FeatureSnapshotService(db)
        self.evidence = EvidenceService(db)

    async def owned(self, dataset_id: UUID, user_id: UUID) -> DatasetVersion:
        row = await self.db.get(DatasetVersion, dataset_id)
        if row is None or row.user_id != user_id:
            raise AppError(404, "DATASET_NOT_FOUND", "Dataset not found")
        return row

    async def build(self, config: DatasetInput, user_id: UUID) -> DatasetVersion:
        await UniverseService(self.db).owned(config.universe_id, user_id)
        locked = await self.db.scalar(text("SELECT pg_try_advisory_xact_lock(608613)"))
        if not locked:
            raise AppError(409, "BUILD_LIMIT", "A dataset build is already active")
        async with asyncio.timeout(get_settings().p6_timeout_seconds):
            return await self._build(config, user_id)

    async def _build(self, config: DatasetInput, user_id: UUID) -> DatasetVersion:
        memberships = list(
            (
                await self.db.scalars(
                    select(UniverseMembershipVersion)
                    .where(UniverseMembershipVersion.universe_id == config.universe_id)
                    .order_by(
                        UniverseMembershipVersion.observed_at.desc(),
                        UniverseMembershipVersion.id.desc(),
                    )
                )
            ).all()
        )
        ids = {r.instrument_id for r in memberships} | {config.benchmark_id}
        if len(ids) > get_settings().p6_max_instruments:
            raise AppError(422, "BUILD_LIMIT", "Too many instruments")
        instruments = {i: await self.db.get(Instrument, i) for i in sorted(ids)}
        for instrument in instruments.values():
            if instrument is None or not instrument.exchange:
                raise AppError(
                    422, "CALENDAR_UNAVAILABLE", "All instruments need an explicit exchange"
                )
        sessions = sorted(
            {
                d
                for instrument in instruments.values()
                if instrument
                for d in self.calendar.sessions_between(
                    instrument.exchange or "", config.start, config.end
                )
            }
        )
        if len(sessions) > get_settings().p6_max_sessions:
            raise AppError(422, "BUILD_LIMIT", "Too many sessions")
        now = datetime.now(UTC)
        rows: list[dict[str, Any]] = []
        market: dict[str, Any] = {}
        actions = {}
        excluded: Counter[str] = Counter()
        pinned: dict[str, set[str]] = {kind: set() for kind in ENTITIES}
        feature_ids = set()
        coverage_ids = set()
        # Ex-post outcome store is separate from historical decision features.
        for iid, instrument in instruments.items():
            assert instrument and instrument.exchange
            series = await self.features.prices(
                iid, config.start, config.end, now, config.availability_mode
            )
            aa, proof = await self.features.actions(
                iid, config.start, config.end, now, config.availability_mode
            )
            actions[str(iid)] = aa if config.availability_mode != "STRICT_PIT" else []
            if proof:
                coverage_ids.add(proof)
            for action in aa:
                pinned["action"].add(action["id"])
            for price in series:
                day = date.fromisoformat(price["date"])
                cutoff = self.calendar.session_close(instrument.exchange, day) + timedelta(
                    minutes=30
                )
                # Reconstruction pins today's series with explicit history limits.
                if config.availability_mode == "STRICT_PIT":
                    historic = await self.features.prices(
                        iid, day, day, cutoff, config.availability_mode
                    )
                    if not historic:
                        continue
                    price = historic[-1]
                day_actions, day_coverage = await self.features.actions(
                    iid,
                    config.start,
                    day,
                    cutoff if config.availability_mode == "STRICT_PIT" else now,
                    config.availability_mode,
                )
                if day_coverage:
                    pinned["coverage"].add(day_coverage)
                if config.availability_mode == "STRICT_PIT":
                    for action in day_actions:
                        if action["date"] == day.isoformat():
                            actions[str(iid)].append(action)
                            pinned["action"].add(action["id"])
                fx = await MarketQueryService(self.db).fx(
                    price["currency"],
                    config.base_currency,
                    day,
                    cutoff if config.availability_mode == "STRICT_PIT" else now,
                )
                fx = json_value(fx)
                for leg in cast(list[dict[str, Any]], fx.get("legs", [])):
                    pinned["fx"].add(leg["id"])
                valid_fx = fx.get("status") == "AVAILABLE"
                if config.availability_mode == "STRICT_PIT":
                    for leg in fx.get("legs", []):
                        review = await self.evidence.latest("fx", UUID(leg["id"]), cutoff)
                        fx_row = await self.db.get(FxRateVersion, UUID(leg["id"]))
                        if (
                            review is None
                            or fx_row is None
                            or not available(
                                "STRICT_PIT",
                                cutoff,
                                fx_row.known_at,
                                fx_row.observed_at,
                                review.level,
                                review.created_at,
                            )
                        ):
                            valid_fx = False
                        if review:
                            pinned["evidence"].add(str(review.id))
                nxt = self.calendar.next_session(instrument.exchange, day)
                fill_fx: dict[str, Any] = {}
                for execution_type, execution_time in (
                    ("open", self.calendar.session_open(instrument.exchange, day)),
                    ("close", self.calendar.session_close(instrument.exchange, day)),
                ):
                    conversion = json_value(
                        await MarketQueryService(self.db).fx(
                            price["currency"],
                            config.base_currency,
                            day,
                            execution_time if config.availability_mode == "STRICT_PIT" else now,
                        )
                    )
                    valid_conversion = conversion.get("status") == "AVAILABLE"
                    for leg in conversion.get("legs", []):
                        pinned["fx"].add(leg["id"])
                        if config.availability_mode == "STRICT_PIT":
                            review = await self.evidence.latest(
                                "fx", UUID(leg["id"]), execution_time
                            )
                            version = await self.db.get(FxRateVersion, UUID(leg["id"]))
                            if (
                                not review
                                or not version
                                or not available(
                                    "STRICT_PIT",
                                    execution_time,
                                    version.known_at,
                                    version.observed_at,
                                    review.level,
                                    review.created_at,
                                )
                            ):
                                valid_conversion = False
                            if review:
                                pinned["evidence"].add(str(review.id))
                    fill_fx[execution_type] = {
                        "rate": conversion.get("rate") if valid_conversion else None,
                        "provenance": conversion,
                    }
                market.setdefault(price["date"], {})[str(iid)] = {
                    **price,
                    "action_coverage": day_coverage,
                    "fill_fx": fill_fx,
                    "fx": fx.get("rate") if valid_fx else None,
                    "fx_provenance": fx,
                    "is_session": True,
                    "open_timestamp": self.calendar.session_open(
                        instrument.exchange, day
                    ).isoformat(),
                    "close_timestamp": self.calendar.session_close(
                        instrument.exchange, day
                    ).isoformat(),
                    "signal_generated_at": (cutoff + timedelta(microseconds=1)).isoformat(),
                    "information_cutoff_at": cutoff.isoformat(),
                    "next_session": nxt.isoformat(),
                    "next_open_timestamp": self.calendar.session_open(
                        instrument.exchange, nxt
                    ).isoformat(),
                }
                pinned["price"].add(price["id"])
                if price.get("availability_review_id"):
                    pinned["evidence"].add(price["availability_review_id"])
        for day in sessions:
            for iid, instrument in instruments.items():
                if iid == config.benchmark_id:
                    continue
                assert instrument and instrument.exchange
                if not self.calendar.is_session(instrument.exchange, day):
                    continue
                cutoff = self.calendar.session_close(instrument.exchange, day) + timedelta(
                    minutes=30
                )
                candidates = [
                    m
                    for m in memberships
                    if m.instrument_id == iid
                    and (
                        config.availability_mode != "STRICT_PIT"
                        or (m.known_at <= cutoff and m.observed_at <= cutoff)
                    )
                ]
                latest: dict[date, UniverseMembershipVersion] = {}
                for m in candidates:
                    latest.setdefault(m.valid_from, m)
                valid = [
                    m
                    for m in latest.values()
                    if m.valid_from <= day
                    and (m.valid_to is None or day <= m.valid_to)
                    and m.membership_status == "LISTED"
                ]
                exits = [
                    m.valid_from
                    for m in latest.values()
                    if m.membership_status in {"REMOVED", "DELISTED"}
                    and m.valid_from <= day
                    and (m.valid_to is None or day <= m.valid_to)
                ]
                if exits:
                    valid = [m for m in valid if m.valid_from > max(exits)]
                if not valid:
                    if not exits and any(
                        m.instrument_id == iid
                        and m.valid_from <= day
                        and (m.valid_to is None or day <= m.valid_to)
                        and m.membership_status == "LISTED"
                        for m in memberships
                    ):
                        excluded["UNVERIFIED_MEMBERSHIP"] += 1
                        rows.append(
                            {
                                "date": day.isoformat(),
                                "instrument_id": str(iid),
                                "membership_id": None,
                                "features": {},
                                "information_cutoff_at": cutoff.isoformat(),
                                "eligible": False,
                                "exclusions": ["UNVERIFIED_MEMBERSHIP"],
                                "target": {
                                    "status": "TARGET_UNAVAILABLE",
                                    "reason": "UNVERIFIED_MEMBERSHIP",
                                },
                            }
                        )
                    continue
                if len(valid) != 1:
                    excluded["AMBIGUOUS_MEMBERSHIP"] += 1
                    continue
                membership = valid[0]
                review = await self.evidence.latest(
                    "membership",
                    membership.id,
                    cutoff if config.availability_mode == "STRICT_PIT" else None,
                )
                reasons = []
                if config.availability_mode == "STRICT_PIT" and not available(
                    config.availability_mode,
                    cutoff,
                    membership.known_at,
                    membership.observed_at,
                    review.level if review else "UNVERIFIED",
                    review.created_at if review else None,
                ):
                    reasons.append("UNVERIFIED_MEMBERSHIP")
                universe_review = await self.evidence.latest(
                    "universe",
                    config.universe_id,
                    cutoff if config.availability_mode == "STRICT_PIT" else None,
                )
                complete = bool(
                    universe_review
                    and universe_review.level.startswith("VERIFIED_")
                    and universe_review.evidence.get("includes_delisted") is True
                    and universe_review.evidence.get("valid_from", "9999")
                    <= day.isoformat()
                    <= universe_review.evidence.get("valid_to", "0000")
                )
                if config.availability_mode == "STRICT_PIT" and not complete:
                    reasons.append("SURVIVORSHIP_BIAS_RISK")
                pinned["membership"].add(str(membership.id))
                if review:
                    pinned["evidence"].add(str(review.id))
                if universe_review:
                    pinned["evidence"].add(str(universe_review.id))
                bar = market.get(day.isoformat(), {}).get(str(iid))
                if not bar:
                    reasons.append("MISSING_PRICE / UNVERIFIED_AVAILABILITY")
                elif bar["fx"] is None:
                    reasons.append("MISSING_FX")
                _, proof = await self.features.actions(
                    iid, config.start, day, cutoff, config.availability_mode
                )
                if proof is None:
                    reasons.append("CORPORATE_ACTION_COVERAGE_UNVERIFIED")
                snapshot = await self.features.build(
                    iid, cutoff, config.availability_mode, config.benchmark_id
                )
                feature_ids.add(str(snapshot.id))
                for kind, entries in snapshot.result["input_version_ids"].items():
                    singular = {
                        "prices": "price",
                        "facts": "fact",
                        "actions": "action",
                        "estimates": "estimate",
                        "news": "news",
                        "macro": "macro",
                        "mapping": "mapping",
                        "evidence": "evidence",
                        "coverage": "coverage",
                        "benchmark_prices": "price",
                        "benchmark_actions": "action",
                        "benchmark_coverage": "coverage",
                    }.get(kind)
                    if singular:
                        pinned[singular].update(entries)
                target = await self.target(iid, config.benchmark_id, day, cutoff, config)
                for kind, entries in target.get("input_versions", {}).items():
                    pinned[kind].update(entries)
                row = {
                    "date": day.isoformat(),
                    "instrument_id": str(iid),
                    "membership_id": str(membership.id),
                    "feature_snapshot_id": str(snapshot.id),
                    "features": snapshot.result["features"],
                    "information_cutoff_at": cutoff.isoformat(),
                    "eligible": not reasons,
                    "exclusions": reasons,
                    "target": target,
                }
                rows.append(row)
                for reason in reasons:
                    excluded[reason] += 1
        quality = {
            "total_observations": len(rows),
            "valid_observations": sum(r["eligible"] for r in rows),
            "excluded_observations": sum(not r["eligible"] for r in rows),
            "exclusion_reasons": dict(excluded),
            "missing_features": sum(
                sum(f["missing_flag"] for f in r["features"].values()) for r in rows
            ),
            "unavailable_targets": sum(r["target"]["status"] != "AVAILABLE" for r in rows),
            "survivorship_risk": config.availability_mode != "STRICT_PIT"
            or bool(excluded["SURVIVORSHIP_BIAS_RISK"]),
        }
        manifest = {
            **code_manifest(),
            "calendar_version": self.calendar.version,
            "feature_version": FEATURE_VERSION,
            "target_version": f"total-return-next-open-{config.target_horizon}-v2",
            "action_policy": "raw+explicit_actions-v1",
            "execution_policy": "next-open-v1",
            "fx_policy": "P3-dated-bounded-carry",
            "availability_policy": config.availability_mode,
            "versions": {k: sorted(v) for k, v in pinned.items()},
            "feature_snapshot_ids": sorted(feature_ids),
            "coverage_ids": sorted(coverage_ids),
            "market": market,
            "actions": actions,
            "universe_id": str(config.universe_id),
            "quality_policy": "hard-gates-before-scores-v1",
        }
        version_hashes: dict[str, dict[str, str]] = {}
        for kind, version_ids in pinned.items():
            if not version_ids:
                continue
            model = ENTITIES[kind]
            versions = (
                await self.db.scalars(
                    select(model)
                    .where(model.id.in_([UUID(value) for value in sorted(version_ids)]))
                    .execution_options(populate_existing=True)
                )
            ).all()
            version_hashes[kind] = {
                str(version.id): digest(
                    json_value(
                        {
                            column.name: getattr(version, column.name)
                            for column in version.__table__.columns
                        }
                    )
                )
                for version in versions
            }
            if len(versions) != len(version_ids):
                raise AppError(409, "PINNED_VERSION_MISSING", "Input disappeared during build")
        manifest["version_hashes"] = version_hashes
        configuration = config.model_dump(mode="json")
        universe = await UniverseService(self.db).owned(config.universe_id, user_id)
        configuration["data_context"] = (
            "SYNTHETIC_SIMULATION_NOT_REAL_ARCHIVE"
            if universe.configuration.get("synthetic")
            else "USER_ARCHIVE"
        )
        content = digest(
            {"configuration": configuration, "manifest": manifest, "rows": rows, "quality": quality}
        )
        existing = (
            await self.db.scalars(
                select(DatasetVersion).where(
                    DatasetVersion.user_id == user_id, DatasetVersion.content_hash == content
                )
            )
        ).first()
        if existing:
            return existing
        dataset = DatasetVersion(
            user_id=user_id,
            universe_id=config.universe_id,
            content_hash=content,
            configuration=configuration,
            manifest=manifest,
            rows=rows,
            quality=quality,
        )
        self.db.add(dataset)
        await self.db.flush()
        return dataset

    async def target(
        self, iid: UUID, benchmark_id: UUID, day: date, cutoff: datetime, config: DatasetInput
    ) -> dict[str, Any]:
        instrument = await self.db.get(Instrument, iid)
        assert instrument and instrument.exchange
        start = self.calendar.next_session(instrument.exchange, day)
        end = self.calendar.horizon(instrument.exchange, day, config.target_horizon)
        contract = {
            "signal_as_of": cutoff.isoformat(),
            "label_start": self.calendar.session_open(instrument.exchange, start).isoformat(),
            "label_end": self.calendar.session_close(instrument.exchange, end).isoformat(),
            "label_available_at": None,
            "horizon_sessions": config.target_horizon,
            "definition_version": "next-open-total-return-v2",
        }
        now = datetime.now(UTC)
        if self.calendar.session_close(instrument.exchange, end) > now:
            return {**contract, "status": "TARGET_UNAVAILABLE", "reason": "LABEL_WINDOW_NOT_ENDED"}
        values = []
        realized_volatility = None
        target_versions: dict[str, list[str]] = {
            k: [] for k in ("price", "action", "fx", "coverage", "evidence")
        }
        inputs: list[str] = []
        availability: list[datetime] = []
        for instrument_id in (iid, benchmark_id):
            series = await self.features.prices(
                instrument_id, start, end, now, config.availability_mode
            )
            aa, coverage = await self.features.actions(
                instrument_id, start, end, now, config.availability_mode
            )
            expected = self.calendar.sessions_between(instrument.exchange, start, end)
            if (
                not coverage
                or [p["date"] for p in series] != [d.isoformat() for d in expected]
                or not series[0].get("open")
            ):
                return {
                    **contract,
                    "status": "TARGET_UNAVAILABLE",
                    "reason": "INCOMPLETE_ALIGNED_TOTAL_RETURN_INPUTS",
                }
            tr = self.features.total_return(series, aa)
            if tr is None:
                return {**contract, "status": "TARGET_UNAVAILABLE", "reason": "AMBIGUOUS_ACTIONS"}
            # Entry at next open; subsequent session close returns include actions once.
            tr = [
                v * Decimal(str(series[0]["close"])) / Decimal(str(series[0]["open"])) for v in tr
            ]
            start_fx = await MarketQueryService(self.db).fx(
                series[0]["currency"], config.base_currency, start, now
            )
            end_fx = await MarketQueryService(self.db).fx(
                series[-1]["currency"], config.base_currency, end, now
            )
            if start_fx.get("status") != "AVAILABLE" or end_fx.get("status") != "AVAILABLE":
                return {**contract, "status": "TARGET_UNAVAILABLE", "reason": "MISSING_FX"}
            for fx in (start_fx, end_fx):
                for leg in cast(list[dict[str, Any]], fx.get("legs", [])):
                    assert isinstance(leg, dict)
                    target_versions["fx"].append(str(leg["id"]))
                    fx_row = await self.db.get(FxRateVersion, leg["id"])
                    if fx_row:
                        availability.extend([fx_row.known_at, fx_row.observed_at])
                    review = await self.evidence.latest("fx", leg["id"])
                    if config.availability_mode == "STRICT_PIT" and (
                        review is None
                        or fx_row is None
                        or not available(
                            "STRICT_PIT",
                            now,
                            fx_row.known_at,
                            fx_row.observed_at,
                            review.level,
                            review.created_at,
                        )
                    ):
                        return {
                            **contract,
                            "status": "TARGET_UNAVAILABLE",
                            "reason": "UNVERIFIED_FX_AVAILABILITY",
                        }
                    if review:
                        target_versions["evidence"].append(str(review.id))
                        availability.append(review.created_at)
            target_versions["price"].extend(p["id"] for p in series)
            target_versions["action"].extend(a["id"] for a in aa)
            target_versions["coverage"].append(coverage)
            proof_row = await self.db.get(ActionCoverageReview, UUID(coverage))
            if proof_row:
                availability.append(proof_row.created_at)
            for p in series:
                if p.get("availability_review_id"):
                    target_versions["evidence"].append(p["availability_review_id"])
                    review = await self.evidence.latest("price", UUID(p["id"]))
                    if review:
                        availability.append(review.created_at)
            if instrument_id == iid:
                daily_base: list[Decimal] = []
                for p, level in zip(series, tr, strict=True):
                    fx = await MarketQueryService(self.db).fx(
                        p["currency"], config.base_currency, date.fromisoformat(p["date"]), now
                    )
                    if fx.get("status") != "AVAILABLE":
                        daily_base = []
                        break
                    daily_base.append(level * Decimal(str(fx["rate"])))
                    for leg in cast(list[dict[str, Any]], fx.get("legs", [])):
                        assert isinstance(leg, dict)
                        target_versions["fx"].append(str(leg["id"]))
                        fx_row = await self.db.get(FxRateVersion, leg["id"])
                        review = await self.evidence.latest("fx", leg["id"])
                        if config.availability_mode == "STRICT_PIT" and (
                            review is None
                            or fx_row is None
                            or not available(
                                "STRICT_PIT",
                                now,
                                fx_row.known_at,
                                fx_row.observed_at,
                                review.level,
                                review.created_at,
                            )
                        ):
                            daily_base = []
                            break
                        if fx_row:
                            availability.extend([fx_row.known_at, fx_row.observed_at])
                        if review:
                            target_versions["evidence"].append(str(review.id))
                            availability.append(review.created_at)
                    if not daily_base:
                        break
                if len(daily_base) == config.target_horizon:
                    entry = Decimal(str(series[0]["close"])) * Decimal(str(start_fx["rate"]))
                    returns = [daily_base[0] / entry - 1] + [
                        b / a - 1 for a, b in zip(daily_base, daily_base[1:], strict=False)
                    ]
                    realized_volatility = str(stdev(returns) * Decimal(252).sqrt())
            value = (
                tr[-1]
                / Decimal(str(series[0]["close"]))
                * Decimal(str(end_fx["rate"]))
                / Decimal(str(start_fx["rate"]))
                - 1
            )
            values.append(value)
            inputs.extend(p["id"] for p in series)
            inputs.extend(a["id"] for a in aa)
            availability.extend(datetime.fromisoformat(p["known_at"]) for p in series)
            availability.extend(datetime.fromisoformat(p["observed_at"]) for p in series)
        excess = values[0] - values[1]
        return {
            **contract,
            "status": "AVAILABLE",
            "label_available_at": max(
                availability + [self.calendar.session_close(instrument.exchange, end)]
            ).isoformat(),
            "instrument_return": str(values[0]),
            "benchmark_return": str(values[1]),
            "excess_return": str(excess),
            "classification": int(excess > 0),
            "realized_volatility": realized_volatility,
            "volatility_status": "AVAILABLE"
            if realized_volatility is not None
            else "TARGET_UNAVAILABLE",
            "input_versions": {k: sorted(set(v)) for k, v in target_versions.items()},
            "inputs": inputs,
        }

    async def rebuild(self, dataset_id: UUID, user_id: UUID) -> dict[str, Any]:
        dataset = await self.owned(dataset_id, user_id)
        if dataset.configuration.get("composition_version"):
            from app.ml.datasets import compose_windows

            windows = []
            for reference in dataset.manifest["windows"]:
                child = await self.owned(UUID(reference["id"]), user_id)
                if child.configuration.get("composition_version"):
                    raise AppError(409, "NESTED_COMPOSITION_FORBIDDEN", "Invalid pinned window")
                await self.rebuild(child.id, user_id)
                if child.content_hash != reference["content_hash"]:
                    raise AppError(409, "PINNED_WINDOW_CHANGED", "Window content changed")
                windows.append(
                    {
                        "id": str(child.id),
                        "content_hash": child.content_hash,
                        "configuration": child.configuration,
                        "manifest": child.manifest,
                        "rows": child.rows,
                        "quality": child.quality,
                    }
                )
            if compose_windows(windows)["content_hash"] != dataset.content_hash:
                raise AppError(409, "COMPOSITION_HASH_MISMATCH", "Window composition changed")
        for kind, ids in dataset.manifest["versions"].items():
            for value in ids:
                model = ENTITIES[kind]
                row = await self.db.get(model, UUID(value))
                if row is None:
                    raise AppError(409, "PINNED_VERSION_MISSING", f"Missing pinned {kind} {value}")
                expected = dataset.manifest.get("version_hashes", {}).get(kind, {}).get(value)
                if expected is None:
                    raise AppError(
                        409,
                        "PINNED_VERSION_HASH_MISSING",
                        "Legacy artifact lacks pinned content evidence",
                    )
                content = digest(
                    json_value(
                        {column.name: getattr(row, column.name) for column in row.__table__.columns}
                    )
                )
                if content != expected:
                    raise AppError(409, "PINNED_VERSION_CHANGED", f"Pinned {kind} content changed")
                if hasattr(row, "raw_ingestion_id"):
                    await RawIngestionService(self.db).get_verified(row.raw_ingestion_id)
        for value in dataset.manifest["feature_snapshot_ids"]:
            row = await self.db.get(FeatureSnapshot, UUID(value))
            if row is None or digest(row.result) != row.content_hash:
                raise AppError(409, "PINNED_FEATURE_MISSING", "Feature version missing or modified")
        content = digest(
            {
                "configuration": dataset.configuration,
                "manifest": dataset.manifest,
                "rows": dataset.rows,
                "quality": dataset.quality,
            }
        )
        if content != dataset.content_hash:
            raise AppError(409, "MANIFEST_HASH_MISMATCH", "Pinned dataset content changed")
        return {
            "status": "VERIFIED_PINNED_REPLAY",
            "content_hash": content,
            "rows": len(dataset.rows),
            "current_data_used": False,
        }
