from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.research import view
from app.models import ResearchSnapshot, RiskSnapshot
from app.models.recommendations import (
    InvestmentProfileVersion,
    Recommendation,
    RecommendationBacktest,
    RecommendationRuleVersion,
    RecommendationStrategyReview,
)
from app.recommendations.backtesting import replay_archived
from app.services.fundamentals import digest


async def recommendation_checkpoint(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    content: dict[str, Any] = {}
    for model in (
        InvestmentProfileVersion,
        Recommendation,
        RecommendationBacktest,
        RecommendationStrategyReview,
    ):
        rows = (
            await db.scalars(select(model).where(model.user_id == user_id).order_by(model.id))
        ).all()
        content[model.__tablename__] = [view(row) for row in rows]
        if model is Recommendation:
            for row in rows:
                recommendation = cast(Recommendation, row)
                replay_archived(recommendation)
                profile = await db.get(InvestmentProfileVersion, recommendation.profile_version_id)
                risk = await db.get(RiskSnapshot, recommendation.risk_snapshot_id)
                research = await db.get(ResearchSnapshot, recommendation.research_snapshot_id)
                rule = await db.get(RecommendationRuleVersion, recommendation.rule_version_id)
                assert profile and profile.user_id == user_id
                assert (
                    profile.content_hash
                    == digest(profile.preferences)
                    == recommendation.input_manifest["profile_hash"]
                )
                assert (
                    risk
                    and risk.user_id == user_id
                    and risk.content_hash == recommendation.input_manifest["risk_hash"]
                )
                assert (
                    research
                    and research.input_hash == recommendation.input_manifest["research_hash"]
                )
                assert (
                    rule
                    and rule.content_hash
                    == digest(rule.configuration)
                    == recommendation.input_manifest["rule_hash"]
                )
    rules = (
        await db.scalars(select(RecommendationRuleVersion).order_by(RecommendationRuleVersion.id))
    ).all()
    content["rules"] = [view(r) for r in rules]
    return {
        "recommendation_history_hash": digest(content),
        "recommendation_count": len(content["recommendations"]),
        "profile_count": len(content["investment_profile_versions"]),
    }
