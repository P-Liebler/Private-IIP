"""Argo-only, first-use schema bootstrap. Refuse to touch nonempty unknown DB."""
import asyncio
import os
import subprocess
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

URL = os.environ["DATABASE_URL"]
HEADS = set(ScriptDirectory.from_config(Config("/app/alembic.ini")).get_heads())
if len(HEADS) != 1:
    raise RuntimeError("Refusing multi-head/empty Alembic configuration")

async def inspect():
    engine = create_async_engine(URL, pool_pre_ping=True, hide_parameters=True)
    try:
        async with engine.connect() as conn:
            found = (await conn.execute(text("""
                SELECT n.nspname, c.relname FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname NOT IN ('pg_catalog','information_schema')
                  AND n.nspname NOT LIKE 'pg_toast%'
                  AND n.nspname NOT LIKE 'pg_temp_%'
                  AND c.relkind IN ('r','p','v','m','S','f')
            """))).all()
            version = ("public", "alembic_version") in found
            if version:
                installed = set((await conn.execute(text(
                    "SELECT version_num FROM public.alembic_version"
                ))).scalars().all())
                if installed == HEADS:
                    return "ready"
                raise RuntimeError("Existing schema differs: manual reviewed migration required")
            if found:
                raise RuntimeError("Nonempty database without version: refusing any writes")
            return "empty"
    finally:
        await engine.dispose()

state = asyncio.run(inspect())
if state == "empty":
    print("Empty database verified; initializing Alembic schema")
    subprocess.run(["alembic", "upgrade", "head"], cwd="/app", check=True)
    if asyncio.run(inspect()) != "ready":
        raise RuntimeError("Fresh Alembic initialization verification failed")
print("Schema is ready at exact pinned head")
