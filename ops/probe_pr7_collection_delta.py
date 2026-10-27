"""Compare frozen source collection rows to the later synthetic QA target, read-only."""
import asyncio
from decimal import Decimal
import json
import re
import sys

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.models import (ActionCoverageReview, CollectorJob, CorporateActionVersion, DataCoverageSnapshot,
    DataSource, FundamentalFact, FxRateVersion, MacroObservation, PriceDailyVersion, ProviderSyncState,
    SourceReviewEvidence)
from app.services.collection_audit import collection_checkpoint
from app.services.fundamentals import digest

MODELS = (DataSource, SourceReviewEvidence, CollectorJob, ProviderSyncState, DataCoverageSnapshot,
          PriceDailyVersion, FxRateVersion, FundamentalFact, MacroObservation, CorporateActionVersion,
          ActionCoverageReview)


async def rows(db, model):
    result = (await db.scalars(select(model))).all()
    return {str(row.id): jsonable_encoder({column.name: getattr(row, column.name)
            for column in model.__table__.columns}, custom_encoder={Decimal: str}) for row in result}


async def main(control):
    assert get_settings().app_env == 'staging'
    frozen_name = control['frozen_database']
    assert re.fullmatch(r'pr7_compare_[a-f0-9]{12}', frozen_name)
    assert frozen_name != get_engine().url.database
    frozen_engine = create_async_engine(get_engine().url.set(database=frozen_name), echo=False)
    result = {'status': 'FROZEN_COLLECTION_ROWS_PRESERVED_WITH_EXPLICIT_QA_ADDITIONS', 'tables': {}}
    try:
        async with AsyncSession(frozen_engine) as before, get_session_factory()() as after:
            for db in (before, after):
                await db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            old = await collection_checkpoint(before)
            assert old['collections_history_hash'] == control['source_collections_hash']
            current = await collection_checkpoint(after)
            for model in MODELS:
                old_rows, new_rows = await rows(before, model), await rows(after, model)
                assert old_rows.keys() <= new_rows.keys(), 'BASELINE_COLLECTION_ROW_REMOVED:' + model.__tablename__
                changed = []
                for identifier, original in old_rows.items():
                    actual = new_rows[identifier]
                    columns = [key for key in original if original[key] != actual[key]]
                    if columns:
                        assert model is DataSource and original['slug'] == 'MANUAL_CSV' and set(columns) <= {'last_success'}, 'BASELINE_COLLECTION_ROW_CHANGED:' + model.__tablename__
                        changed.append({'row_hash_before': digest(original), 'row_hash_after': digest(actual), 'columns': columns})
                added = [row for identifier, row in new_rows.items() if identifier not in old_rows]
                for row in added:
                    if model is DataSource:
                        assert row['slug'].startswith('TEST_P10_') and row['type'] == 'MANUAL'
                        assert row['scope'] == 'Only self-authored synthetic local test documents'
                    elif model in (PriceDailyVersion, ActionCoverageReview):
                        assert row['instrument_id'] == control['fresh_instrument_id']
                    elif model is FxRateVersion:
                        assert row['base_currency'] == 'USD' and row['quote_currency'] == 'CHF'
                        assert Decimal(row['rate']) == Decimal('0.9')
                    else:
                        assert not added, 'UNEXPECTED_QA_COLLECTION_ADDITION:' + model.__tablename__
                result['tables'][model.__tablename__] = {'baseline_rows': len(old_rows), 'added_rows': len(added),
                    'added_rows_hash': digest(sorted(added, key=digest)), 'reviewed_operational_changes': changed}
            result['source_collections_hash'] = old['collections_history_hash']
            result['post_qa_collections_hash'] = current['collections_history_hash']
            print(json.dumps(result))
    finally:
        await frozen_engine.dispose()
        await get_engine().dispose()


if __name__ == '__main__':
    asyncio.run(main(json.loads(sys.stdin.readline())))
