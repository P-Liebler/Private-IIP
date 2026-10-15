from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import User
from app.models.recommendations import InvestmentProfileVersion
from app.schemas.recommendations import InvestmentPreferences, ProfileUpdate
from app.services.audit import audit_service
from app.services.fundamentals import digest

UNITS = {
    "investment_horizon": "exchange sessions; P7 horizons 30/90",
    "minimum_liquidity": "shares per session; 20-session mean volume proxy",
    "maximum_new_investment": "base_currency per candidate evaluation",
    "commission_base": "base_currency per hypothetical order",
    "spread_bps": "basis points per order notional",
    "slippage_bps": "basis points per order notional",
    "maximum_portfolio_volatility": "annualized standard deviation fraction",
    "weights_cash_turnover": "fractions of complete positive portfolio NAV",
    "currency_exposure": "absolute net accounting translation weight including cash",
}
CLASSIFICATION = {
    "soft": ["risk_tolerance", "preferred_universe"],
    "informational": ["base_currency", "investment_horizon"],
    "hard": [
        "confirmed",
        "max_single_position_weight",
        "max_sector_weight",
        "max_country_weight",
        "max_currency_exposure",
        "minimum_liquidity",
        "maximum_portfolio_volatility",
        "minimum_cash_reserve",
        "maximum_new_investment",
        "maximum_turnover",
        "excluded_instruments",
        "excluded_sectors",
    ],
}


class PreferenceService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def latest(self) -> InvestmentProfileVersion | None:
        return cast(
            InvestmentProfileVersion | None,
            await self.db.scalar(
                select(InvestmentProfileVersion)
                .where(InvestmentProfileVersion.user_id == self.user_id)
                .order_by(
                    InvestmentProfileVersion.created_at.desc(), InvestmentProfileVersion.id.desc()
                )
                .limit(1)
            ),
        )

    async def current(self) -> dict[str, Any]:
        row = await self.latest()
        user = await self.db.get(User, self.user_id)
        assert user
        return {
            "id": row.id if row else None,
            "preferences": row.preferences
            if row
            else InvestmentPreferences(base_currency=user.base_currency).model_dump(mode="json"),
            "created_at": row.created_at if row else None,
            "units": UNITS,
            "classification": CLASSIFICATION,
            "status": "CONFIRMED"
            if row and row.preferences["confirmed"]
            else "UNCONFIRMED_DEFAULTS",
        }

    async def save(self, request: ProfileUpdate) -> InvestmentProfileVersion:
        await self.db.get(User, self.user_id, with_for_update=True)
        previous = await self.latest()
        if request.expected_version_id != (previous.id if previous else None):
            raise AppError(409, "PROFILE_VERSION_CONFLICT", "Refresh the profile before saving")
        data = request.preferences.model_dump(mode="json")
        row = InvestmentProfileVersion(
            user_id=self.user_id,
            previous_id=previous.id if previous else None,
            preferences=data,
            content_hash=digest(data),
        )
        self.db.add(row)
        await self.db.flush()
        audit_service.record(
            self.db,
            event="investment_profile.versioned",
            resource="investment_profile",
            resource_id=str(row.id),
            actor_user_id=self.user_id,
        )
        await self.db.commit()
        return row
