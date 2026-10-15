from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NewsArticle, NewsMappingVersion


async def archived_news(
    db: AsyncSession, instrument_id: UUID, cutoff: datetime, limit: int
) -> list[NewsArticle]:
    versions = (
        await db.scalars(
            select(NewsMappingVersion)
            .where(
                NewsMappingVersion.instrument_id == instrument_id,
                NewsMappingVersion.observed_at <= cutoff,
                NewsMappingVersion.created_at <= cutoff,
            )
            .order_by(
                NewsMappingVersion.observed_at.desc(),
                NewsMappingVersion.created_at.desc(),
                NewsMappingVersion.id.desc(),
            )
            .limit(1000)
        )
    ).all()
    heads: dict[UUID, NewsMappingVersion] = {}
    for version in versions:
        heads.setdefault(version.article_id, version)
    ids = [aid for aid, version in heads.items() if version.mapping_status == "CONFIRMED"]
    return list(
        (
            await db.scalars(
                select(NewsArticle)
                .where(
                    NewsArticle.id.in_(ids),
                    NewsArticle.known_at <= cutoff,
                    NewsArticle.observed_at <= cutoff,
                    NewsArticle.retrieved_at <= cutoff,
                    NewsArticle.created_at <= cutoff,
                )
                .order_by(NewsArticle.known_at.desc())
                .limit(limit)
            )
        ).all()
    )
