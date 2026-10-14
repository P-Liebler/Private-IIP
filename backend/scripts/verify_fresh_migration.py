"""Verify all Alembic migrations on a disposable PostgreSQL database.

Run only in a local development container whose database role may CREATE DATABASE.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from uuid import uuid4

import asyncpg
from sqlalchemy.engine import make_url

from app.core.config import get_settings


async def main() -> None:
    current = make_url(get_settings().database_url)
    name = f"p4_migration_test_{uuid4().hex[:12]}"
    admin = current.set(drivername="postgresql", database="postgres")
    target = current.set(drivername="postgresql", database=name)
    connection = await asyncpg.connect(admin.render_as_string(hide_password=False))
    try:
        await connection.execute(f"CREATE DATABASE {name}")
        try:
            environment = {
                **os.environ,
                "DATABASE_URL": target.set(drivername="postgresql+asyncpg").render_as_string(
                    hide_password=False
                ),
            }
            subprocess.run(["alembic", "upgrade", "head"], check=True, env=environment)
            disposable = await asyncpg.connect(target.render_as_string(hide_password=False))
            try:
                revision = await disposable.fetchval("SELECT version_num FROM alembic_version")
                tables = await disposable.fetchval(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name = ANY($1::text[])",
                    [
                        "users",
                        "sessions",
                        "audit_events",
                        "data_sources",
                        "instruments",
                        "raw_ingestions",
                        "price_daily",
                        "price_daily_versions",
                        "corporate_actions",
                        "corporate_action_versions",
                        "fx_rates",
                        "fx_rate_versions",
                        "data_quarantine",
                        "benchmarks",
                        "portfolios",
                        "portfolio_accounts",
                        "transactions",
                        "portfolio_action_applications",
                        "cash_balances",
                        "position_snapshots",
                        "portfolio_snapshots",
                        "filings",
                        "fundamental_fact_versions",
                        "research_snapshots",
                        "research_metrics",
                        "watchlists",
                        "watchlist_items",
                        "news_articles",
                        "news_instruments",
                        "analyst_estimate_snapshots",
                        "availability_reviews",
                        "action_coverage_reviews",
                        "universe_definitions",
                        "universe_membership_versions",
                        "feature_snapshots",
                        "dataset_versions",
                        "backtest_runs",
                        "macro_observation_versions",
                        "news_mapping_versions",
                        "walk_forward_splits",
                        "pit_jobs",
                    ],
                )
                assert revision == "0012_pit_immutability" and tables == 41
                print(f"Fresh migration verified: {revision}; {tables} required tables")
            finally:
                await disposable.close()
        finally:
            await connection.execute(f"DROP DATABASE {name} WITH (FORCE)")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
