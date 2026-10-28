"""Read-only row comparison against a separately restored frozen QA database."""
import asyncio
from datetime import datetime
from decimal import Decimal
import json
import re
import sys
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.assistant.audit import intelligence_checkpoint
from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.models import (
    AlertEvaluation, AlertEvent, AlertRule, AlertRuleVersion, AssistantConversation,
    AssistantMessage, AssistantToolCall, ChunkEmbedding, DailyBrief, DailyBriefConfig,
    DocumentChunk, DocumentRemoval, DocumentRightsReview, FinancialEventVersion,
    Notification, OptimizerRun, ResearchDocument, User,
)
from app.services.fundamentals import digest

MODELS = (AssistantConversation, AssistantMessage, AssistantToolCall, DocumentRightsReview,
          ResearchDocument, FinancialEventVersion, AlertRule, AlertRuleVersion, AlertEvaluation,
          AlertEvent, Notification, DailyBriefConfig, DailyBrief, OptimizerRun,
          DocumentChunk, ChunkEmbedding, DocumentRemoval)


async def rows(db, model):
    result = (await db.scalars(select(model))).all()
    primary = list(model.__table__.primary_key.columns)
    return {str(tuple(str(getattr(row, column.name)) for column in primary)):
        jsonable_encoder({column.name: getattr(row, column.name) for column in model.__table__.columns},
                         custom_encoder={Decimal: str}) for row in result}


async def main(control):
    assert get_settings().app_env == 'staging'
    name = control['frozen_database']
    assert re.fullmatch(r'pr8_compare_[a-f0-9]{12}', name) and name != get_engine().url.database
    engine = create_async_engine(get_engine().url.set(database=name), echo=False)
    result = {'status': 'ARCHIVED_CONTENT_PRESERVED_WITH_REVIEWED_SCHEDULER_PROGRESS', 'tables': {}}
    try:
        async with AsyncSession(engine) as before, get_session_factory()() as after:
            for db in (before, after):
                await db.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            assert control['username'].startswith('restore_')
            user_id = await before.scalar(select(User.id).where(User.username == control['username']))
            assert user_id is not None
            old = await intelligence_checkpoint(before, user_id)
            assert old['intelligence_history_hash'] == control['baseline_intelligence_hash']
            current = await intelligence_checkpoint(after, user_id)
            for model in MODELS:
                original, actual = await rows(before, model), await rows(after, model)
                assert original.keys() <= actual.keys(), 'ARCHIVED_ROW_REMOVED:' + model.__tablename__
                progress = []
                for key, value in original.items():
                    changed = {column for column in value if actual[key][column] != value[column]}
                    if changed:
                        assert model is AlertRule and changed == {'last_checked_at'}, 'ARCHIVED_ROW_CHANGED:' + model.__tablename__
                        stamp = datetime.fromisoformat(actual[key]['last_checked_at'])
                        assert stamp.tzinfo and (value['last_checked_at'] is None or stamp >= datetime.fromisoformat(value['last_checked_at']))
                        progress.append({'before_hash': digest(value), 'after_hash': digest(actual[key]),
                                         'fields': sorted(changed)})
                additions = [row for key, row in actual.items() if key not in original]
                # This review is exclusively for the scheduler's versioned
                # evaluation/brief records, not arbitrary newly changed data.
                assert not additions or model in {AlertEvaluation, AlertEvent, Notification, DailyBrief}, 'UNEXPECTED_APPEND:' + model.__tablename__
                result['tables'][model.__tablename__] = {'baseline_count': len(original),
                    'added_count': len(additions), 'added_content_hash': digest(sorted(additions, key=digest)),
                    'reviewed_scheduler_progress': progress}
            result.update(baseline_intelligence_hash=old['intelligence_history_hash'],
                          post_runtime_intelligence_hash=current['intelligence_history_hash'])
            print(json.dumps(result))
    finally:
        await engine.dispose()
        await get_engine().dispose()


if __name__ == '__main__':
    asyncio.run(main(json.loads(sys.stdin.readline())))
