import asyncio
import secrets
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.assistant.orchestration import AssistantService
from app.db.session import get_engine, get_session_factory
from app.models import AssistantConversation, AssistantMessage, User
from app.schemas.assistant import ChatInput, ConversationCreate, ModelSelection


@pytest.mark.integration
def test_untrusted_model_output_falls_back_and_cancelled_stream_is_archived():
    async def run():
        from app.services.auth import AuthService

        async with get_session_factory()() as db:
            user = await AuthService(db).create_user(
                "p10_" + uuid4().hex[:12], secrets.token_urlsafe(32)
            )
            uid = user.id
            try:

                class ForgedModel:
                    async def select(self, question, facts):
                        return ModelSelection(
                            fact_ids=["invented_citation_and_financial_claim"]
                        ), "TEST_ONLY_FORGED"

                service = AssistantService(db, uid, llm=ForgedModel())
                conversation = await service.create(
                    ConversationCreate(title="TEST model injection")
                )
                cid = conversation.id
                events = [e async for e in service.stream(cid, ChatInput(question="Unknown data"))]
                assert events[-1]["type"] == "done"
                assert events[-1]["status"] == "LLM_OUTPUT_REJECTED"
                assert "invented_citation" not in str(events)
                started = asyncio.Event()

                class SlowModel:
                    async def select(self, question, facts):
                        started.set()
                        await asyncio.Event().wait()

                slow = AssistantService(db, uid, llm=SlowModel())
                second = await slow.create(ConversationCreate(title="TEST cancellation"))
                second_id = second.id

                async def consume():
                    async for _ in slow.stream(second_id, ChatInput(question="Unknown data")):
                        pass

                task = asyncio.create_task(consume())
                await asyncio.wait_for(started.wait(), 10)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
                async with get_session_factory()() as independent:
                    status = await independent.scalar(
                        select(AssistantMessage.status).where(
                            AssistantMessage.conversation_id == second_id,
                            AssistantMessage.role == "ASSISTANT",
                        )
                    )
                    assert status == "CANCELLED"
            finally:
                await db.rollback()
                await db.execute(
                    delete(AssistantConversation).where(AssistantConversation.user_id == uid)
                )
                await db.execute(delete(User).where(User.id == uid))
                await db.commit()

    async def disposed():
        try:
            await run()
        finally:
            await get_engine().dispose()

    asyncio.run(disposed())
