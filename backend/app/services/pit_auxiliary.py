from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.features import feature
from app.backtesting.validation import available
from app.models import AnalystEstimate, MacroObservation, NewsArticle, NewsMappingVersion
from app.services.pit_evidence import EvidenceService


class AuxiliaryFeatures:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.evidence = EvidenceService(db)

    async def calculate(
        self, instrument_id: UUID, cutoff: datetime
    ) -> tuple[dict[str, Any], dict[str, list[str]]]:
        values = {}
        inputs: dict[str, list[str]] = {
            "estimates": [],
            "news": [],
            "macro": [],
            "mapping": [],
            "evidence": [],
        }
        estimates = list(
            (
                await self.db.scalars(
                    select(AnalystEstimate)
                    .where(
                        AnalystEstimate.instrument_id == instrument_id,
                        AnalystEstimate.known_at <= cutoff,
                        AnalystEstimate.observed_at <= cutoff,
                    )
                    .order_by(AnalystEstimate.observed_at.desc(), AnalystEstimate.id.desc())
                )
            ).all()
        )
        valid = []
        for estimate in estimates:
            review = await self.evidence.latest("estimate", estimate.id, cutoff)
            if review and available(
                "STRICT_PIT",
                cutoff,
                estimate.known_at,
                estimate.observed_at,
                review.level,
                review.created_at,
            ):
                valid.append(estimate)
                inputs["evidence"].append(str(review.id))
        for name, kind, days in [
            ("EPS_revision_30d", "EPS", 30),
            ("EPS_revision_90d", "EPS", 90),
            ("target_change", "PRICE_TARGET", 30),
            ("recommendation_change", "RECOMMENDATION", 30),
        ]:
            choices = [
                r for r in valid if r.estimate_type == kind and r.target_period >= cutoff.date()
            ]
            current = choices[0] if choices else None
            old = next(
                (
                    r
                    for r in choices
                    if current
                    and r.target_period == current.target_period
                    and r.unit == current.unit
                    and r.currency == current.currency
                    and r.observed_at <= cutoff - timedelta(days=days)
                ),
                None,
            )
            ids = [str(r.id) for r in (current, old) if r]
            number = None
            if current and old:
                old_cutoff = cutoff - timedelta(days=days)
                old_review = await self.evidence.latest("estimate", old.id, old_cutoff)
                if old_review and available(
                    "STRICT_PIT",
                    old_cutoff,
                    old.known_at,
                    old.observed_at,
                    old_review.level,
                    old_review.created_at,
                ):
                    if kind == "RECOMMENDATION":
                        number = current.value - old.value
                    elif old.value > 0:
                        number = current.value / old.value - 1
                    inputs["evidence"].append(str(old_review.id))
            values[name] = feature(number, ids, "NO_COMPATIBLE_HISTORICAL_ESTIMATE")
            inputs["estimates"].extend(ids)
        # Quantitative sentiment remains unavailable without immutable verified model outputs.
        mappings = list(
            (
                await self.db.scalars(
                    select(NewsMappingVersion)
                    .where(
                        NewsMappingVersion.instrument_id == instrument_id,
                        NewsMappingVersion.observed_at <= cutoff,
                    )
                    .order_by(NewsMappingVersion.observed_at.desc())
                )
            ).all()
        )
        latest: dict[UUID, NewsMappingVersion] = {}
        for mapping in mappings:
            latest.setdefault(mapping.article_id, mapping)
        count = 0
        for aid, mapping in latest.items():
            if mapping.mapping_status != "CONFIRMED":
                continue
            article = await self.db.get(NewsArticle, aid)
            if (
                article is None
                or article.duplicate_of_id
                or not cutoff - timedelta(days=7) <= article.known_at <= cutoff
                or article.observed_at > cutoff
            ):
                continue
            review = await self.evidence.latest("news", article.id, cutoff)
            if review and available(
                "STRICT_PIT",
                cutoff,
                article.known_at,
                article.observed_at,
                review.level,
                review.created_at,
            ):
                count += 1
                inputs["news"].append(str(article.id))
                inputs["mapping"].append(str(mapping.id))
                inputs["evidence"].append(str(review.id))
        # Without feed coverage, publish only explicitly observed positive counts.
        values["news_volume"] = feature(
            Decimal(count) if count else None, inputs["news"], "NEWS_COVERAGE_UNVERIFIED"
        )
        values["news_volume"]["coverage_scope"] = "VERIFIED_OBSERVED_ARCHIVE_ONLY"
        macro = list(
            (
                await self.db.scalars(
                    select(MacroObservation)
                    .where(
                        MacroObservation.known_at <= cutoff,
                        MacroObservation.observed_at <= cutoff,
                        MacroObservation.observation_date <= cutoff.date(),
                    )
                    .order_by(
                        MacroObservation.observation_date.desc(),
                        MacroObservation.observed_at.desc(),
                    )
                )
            ).all()
        )
        selected = set()
        for observation in macro:
            if observation.series in selected:
                continue
            if (cutoff.date() - observation.observation_date).days > 31:
                continue
            review = await self.evidence.latest("macro", observation.id, cutoff)
            if review and available(
                "STRICT_PIT",
                cutoff,
                observation.known_at,
                observation.observed_at,
                review.level,
                review.created_at,
            ):
                values[observation.series] = feature(
                    Decimal(observation.value), [str(observation.id)]
                )
                values[observation.series]["unit"] = observation.unit
                values[observation.series]["observation_date"] = (
                    observation.observation_date.isoformat()
                )
                inputs["macro"].append(str(observation.id))
                inputs["evidence"].append(str(review.id))
                selected.add(observation.series)
        return values, {k: sorted(set(v)) for k, v in inputs.items()}
