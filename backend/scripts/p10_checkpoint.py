import argparse
import asyncio
import json
from uuid import UUID

from app.assistant.audit import intelligence_checkpoint
from app.db.session import get_engine, get_session_factory
from app.models import Portfolio


async def main(identifier: UUID) -> None:
    try:
        async with get_session_factory()() as db:
            portfolio = await db.get(Portfolio, identifier)
            assert portfolio
            print(json.dumps(await intelligence_checkpoint(db, portfolio.user_id)))
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("portfolio_id", type=UUID)
    asyncio.run(main(parser.parse_args().portfolio_id))
