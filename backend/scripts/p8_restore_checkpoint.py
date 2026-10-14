import argparse
import asyncio
import json
from uuid import UUID

from app.db.session import get_engine, get_session_factory
from app.models import Portfolio
from app.services.risk_audit import history_checkpoint


async def main(portfolio_id: UUID) -> None:
    try:
        async with get_session_factory()() as db:
            portfolio = await db.get(Portfolio, portfolio_id)
            assert portfolio is not None
            print(
                json.dumps(
                    await history_checkpoint(db, portfolio.user_id, portfolio.id, verify=True)
                )
            )
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("portfolio_id", type=UUID)
    asyncio.run(main(parser.parse_args().portfolio_id))
