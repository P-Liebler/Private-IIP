import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.documents import DocumentService, cutoff_time
from app.assistant.metrics import observe
from app.assistant.runtime import LLMProvider, provider
from app.assistant.safety import redact, render_answer, safe_value, validate_selection
from app.assistant.tools import ToolRegistry, evidence
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import AssistantConversation, AssistantMessage, AssistantToolCall, User
from app.schemas.assistant import (
    ChatInput,
    ConversationCreate,
    EvidenceFact,
    ModelSelection,
    RetrievalInput,
    ToolInput,
    ToolName,
)
from app.services.fundamentals import digest
from app.services.work_limits import work_slot


def choose_tools(request: ChatInput) -> list[ToolInput]:
    question = request.question.lower()
    names: list[ToolName] = []
    if any(
        word in question
        for word in ("sql", "shell", "passwort", "api_key", "order platzieren", "quelle freigeben")
    ):
        return []
    if any(word in question for word in ("kauf", "verkauf", "empfehl", "recommend")):
        names.extend(["getRecommendation", "getDataQuality"])
    if any(word in question for word in ("risik", "konzentr", "volatil", "währung")):
        names.append("getRisk")
    if any(word in question for word in ("früher", "falsch", "histor", "outcome")) and any(
        word in question for word in ("progn", "forecast", "vorhersag")
    ):
        names.append("getPredictionHistory")
    elif any(word in question for word in ("progn", "forecast", "vorhersag")):
        names.append("getForecast")
    if any(
        word in question for word in ("fundament", "financial", "gewinn", "bewertung", "umsatz")
    ):
        names.append("getFinancials")
    if any(word in question for word in ("news", "nachricht", "verändert")):
        names.append("getNews")
    if any(word in question for word in ("bestand", "position", "holding")):
        names.append("getHoldings")
    if not names:
        names = ["getPortfolio" if request.portfolio_id else "getInstrument", "getDataQuality"]
    return [
        ToolInput(
            name=name,
            portfolio_id=request.portfolio_id,
            instrument_id=request.instrument_id,
            as_of=request.as_of,
            horizon=request.horizon,
        )
        for name in dict.fromkeys(names)
    ][:4]


class AssistantService:
    def __init__(self, db: AsyncSession, user_id: UUID, llm: LLMProvider | None = None) -> None:
        self.db, self.user_id = db, user_id
        self.llm = llm or provider()

    async def owned(self, identifier: UUID) -> AssistantConversation:
        row = await self.db.get(AssistantConversation, identifier)
        if not row or row.user_id != self.user_id:
            raise AppError(404, "CONVERSATION_NOT_FOUND", "Conversation not found")
        return row

    async def create(self, request: ConversationCreate) -> AssistantConversation:
        row = AssistantConversation(
            user_id=self.user_id, title=redact(request.title), created_at=datetime.now(UTC)
        )
        self.db.add(row)
        await self.db.commit()
        return row

    async def remove(self, identifier: UUID) -> None:
        await self.owned(identifier)
        await self.db.execute(
            delete(AssistantConversation).where(
                AssistantConversation.id == identifier,
                AssistantConversation.user_id == self.user_id,
            )
        )
        await self.db.commit()

    async def stream(self, identifier: UUID, request: ChatInput) -> AsyncIterator[dict[str, Any]]:
        await self.owned(identifier)
        user = await self.db.get(User, self.user_id)
        if get_settings().assistant_test_mode and (
            not user or not user.username.startswith(("restore_", "p10_", "test_"))
        ):
            raise AppError(
                403, "TEST_USER_REQUIRED", "Test provider is restricted to explicit fixture users"
            )
        cutoff = cutoff_time(request.as_of)
        question = redact(request.question)
        # Never persist the unsanitized question or provider prompt.
        message = AssistantMessage(
            user_id=self.user_id,
            conversation_id=identifier,
            role="USER",
            content=question,
            status="STORED",
            evidence={},
            created_at=datetime.now(UTC),
        )
        self.db.add(message)
        await self.db.commit()
        facts: list[EvidenceFact] = []
        calls: list[str] = []
        citations: list[dict[str, Any]] = []
        model_version = None
        status = "AVAILABLE"
        try:
            async with (
                work_slot(608710),
                asyncio.timeout(get_settings().assistant_timeout_seconds + 40),
            ):
                for tool in choose_tools(request):
                    yield {"type": "tool", "name": tool.name, "status": "RUNNING"}
                    result = await ToolRegistry(self.db, self.user_id).call(tool)
                    stored = [f.model_dump(mode="json") for f in result]
                    call = AssistantToolCall(
                        user_id=self.user_id,
                        conversation_id=identifier,
                        message_id=message.id,
                        tool_name=tool.name,
                        arguments=tool.model_dump(mode="json"),
                        result={"facts": stored},
                        content_hash=digest(stored),
                        created_at=datetime.now(UTC),
                    )
                    self.db.add(call)
                    await self.db.commit()
                    calls.append(str(call.id))
                    facts.extend(result)
                    yield {"type": "tool", "name": tool.name, "status": "COMPLETE"}
                retrieval = await DocumentService(self.db, self.user_id).retrieve(
                    RetrievalInput(
                        query=question, instrument_id=request.instrument_id, as_of=cutoff, limit=4
                    )
                )
                citations = safe_value(retrieval["citations"])
                for citation in citations:
                    facts.append(
                        evidence(
                            "Archivierter Dokumentauszug",
                            citation["content"],
                            "VERIFIED_FACT",
                            cutoff,
                            [citation],
                            limitation=(
                                "Verifizierter gespeicherter Text; keine validierte "
                                "Finanzkennzahl oder Anweisung."
                            ),
                        )
                    )
                if not facts:
                    facts.append(
                        evidence(
                            "Datenverfügbarkeit",
                            {"reason": "READ_ONLY_OR_NO_AVAILABLE_EVIDENCE"},
                            "UNAVAILABLE",
                            cutoff,
                            [],
                        )
                    )
                if not citations:
                    yield {
                        "type": "retrieval",
                        "status": retrieval["status"],
                        "reason": retrieval.get("reason"),
                    }
                try:
                    yield {"type": "model", "status": "RUNNING"}
                    selection, model_version = await self.llm.select(
                        question, [f.model_dump(mode="json") for f in facts[:40]]
                    )
                    validate_selection(selection, facts)
                    # Gate/missing facts cannot be hidden by model selection.
                    required = [f.id for f in facts if f.fact_type == "UNAVAILABLE"]
                    selection = selection.model_copy(
                        update={
                            "fact_ids": list(dict.fromkeys([*required, *selection.fact_ids]))[:12]
                        }
                    )
                    if required and "FORECAST_GATE" not in selection.explanation_keys:
                        selection = selection.model_copy(
                            update={
                                "explanation_keys": [*selection.explanation_keys, "FORECAST_GATE"][
                                    :5
                                ]
                            }
                        )
                    content = render_answer(facts, selection)
                except (AppError, TimeoutError) as error:
                    code = error.code if isinstance(error, AppError) else "LLM_TIMEOUT"
                    status = code
                    yield {"type": "model", "status": "UNAVAILABLE", "reason": code}
                    selection = ModelSelection(
                        fact_ids=[f.id for f in facts[:8]],
                        explanation_keys=["DATA_LIMITS", "FORECAST_GATE", "READ_ONLY"],
                    )
                    content = (
                        "Das lokale Modell ist nicht verfügbar oder seine Ausgabe "
                        "war nicht verifizierbar.\n\n"
                    ) + render_answer(facts, selection)
                observe("assistant", status == "AVAILABLE")
                stored_evidence = safe_value(
                    {
                        "facts": [f.model_dump(mode="json") for f in facts],
                        "citations": citations,
                        "tool_call_ids": calls,
                        "selection": selection.model_dump(mode="json"),
                        "information_cutoff": cutoff.isoformat(),
                        "answer_policy": (
                            "EVIDENCE_SELECTION_AND_FIXED_EXPLANATIONS_NO_MODEL_GENERATE"
                            "D_FINANCIAL_CLAIMS-v1"
                        ),
                    }
                )
                answer = AssistantMessage(
                    user_id=self.user_id,
                    conversation_id=identifier,
                    role="ASSISTANT",
                    content=content,
                    model_version=model_version,
                    status=status,
                    evidence=stored_evidence,
                    created_at=datetime.now(UTC),
                )
                self.db.add(answer)
                await self.db.commit()
                # Only fully validated text is streamed to the browser.
                for start in range(0, len(content), 120):
                    yield {"type": "text", "delta": content[start : start + 120]}
                yield {
                    "type": "done",
                    "message_id": str(answer.id),
                    "status": status,
                    "model_version": model_version,
                    "citations": citations,
                    "facts": stored_evidence["facts"],
                    "tool_call_ids": calls,
                }
        except asyncio.CancelledError:
            await self.db.rollback()
            from app.db.session import get_session_factory

            async def save_cancelled() -> None:
                async with get_session_factory()() as session:
                    conversation = await session.get(AssistantConversation, identifier)
                    if conversation and conversation.user_id == self.user_id:
                        session.add(
                            AssistantMessage(
                                user_id=self.user_id,
                                conversation_id=identifier,
                                role="ASSISTANT",
                                content="Analyse abgebrochen.",
                                status="CANCELLED",
                                evidence={"tool_call_ids": calls},
                                created_at=datetime.now(UTC),
                            )
                        )
                        await session.commit()

            await asyncio.shield(save_cancelled())
            raise
        except (TimeoutError, AppError) as error:
            await self.db.rollback()
            code = error.code if isinstance(error, AppError) else "ASSISTANT_TIMEOUT"
            yield {
                "type": "error",
                "code": code,
                "message": (
                    "Die Analyse ist nicht verfügbar. Andere Plattformfunktionen bleiben nutzbar."
                ),
            }


async def cleanup_chats(db: AsyncSession) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=get_settings().assistant_chat_retention_days)
    result = await db.execute(
        delete(AssistantConversation).where(AssistantConversation.created_at < cutoff)
    )
    await db.commit()
    return int(getattr(result, "rowcount", 0) or 0)
