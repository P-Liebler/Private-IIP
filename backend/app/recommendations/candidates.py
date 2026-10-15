from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import UniverseDefinition, UniverseMembershipVersion, Watchlist, WatchlistItem
from app.schemas.recommendations import RecommendationInput


async def candidates(
    db: AsyncSession,
    user_id: UUID,
    request: RecommendationInput,
    held: list[UUID],
    cutoff: datetime,
) -> list[UUID]:
    result = set(held) | set(request.instrument_ids)
    if request.watchlist_id:
        watchlist = await db.get(Watchlist, request.watchlist_id)
        if not watchlist or watchlist.user_id != user_id or watchlist.archived:
            raise AppError(404, "WATCHLIST_NOT_FOUND", "Watchlist not found")
        result.update(
            (
                await db.scalars(
                    select(WatchlistItem.instrument_id)
                    .where(WatchlistItem.watchlist_id == watchlist.id)
                    .limit(21)
                )
            ).all()
        )
    if request.universe_id:
        universe = await db.get(UniverseDefinition, request.universe_id)
        if not universe or universe.user_id != user_id:
            raise AppError(404, "UNIVERSE_NOT_FOUND", "Universe not found")
        rows = (
            await db.scalars(
                select(UniverseMembershipVersion)
                .where(
                    UniverseMembershipVersion.universe_id == universe.id,
                    UniverseMembershipVersion.known_at <= cutoff,
                    UniverseMembershipVersion.observed_at <= cutoff,
                    UniverseMembershipVersion.created_at <= cutoff,
                )
                .order_by(UniverseMembershipVersion.observed_at.desc())
                .limit(2000)
            )
        ).all()
        superseded = {r.replaces_id for r in rows if r.replaces_id}
        result.update(
            r.instrument_id
            for r in rows
            if r.id not in superseded
            and r.membership_status == "LISTED"
            and r.valid_from <= cutoff.date()
            and (r.valid_to is None or r.valid_to >= cutoff.date())
        )
    if len(result) > 20:
        raise AppError(422, "CANDIDATE_LIMIT", "Select at most 20 candidates including holdings")
    return sorted(result, key=str)
