import json
import re
from typing import Any

from app.core.errors import AppError
from app.schemas.assistant import EvidenceFact, ModelSelection

SECRET_PATTERNS = [
    re.compile(
        r"(?i)\b(?:password|passwort|api[_ -]?key|secret|token|totp|otp|2fa)\s*[:=]\s*[^\s,;]+"
    ),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
]
EXPLANATIONS = {
    "DATA_LIMITS": "Fehlende oder veraltete Eingaben erlauben keine belastbare Aussage.",
    "FORECAST_GATE": (
        "Ohne validierte Produktionsprognose und Strategieabnahme gibt es keine "
        "freigegebene Anlageempfehlung."
    ),
    "RISK_DEFINITION": (
        "Historische Risikokennzahlen beschreiben beobachtete Schwankungen; sie "
        "garantieren keine zukünftigen Ergebnisse."
    ),
    "SOURCE_QUOTE": (
        "Dokumentauszüge belegen den gespeicherten Text. Daraus werden keine ungeprüften"
        " Finanzkennzahlen übernommen."
    ),
    "READ_ONLY": (
        "Der Assistent liest und erklärt. Er ändert keine Transaktionen, "
        "Quellenfreigaben oder Risikogrenzen."
    ),
}


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def safe_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [safe_value(v) for v in value]
    if isinstance(value, dict):
        return {k: safe_value(v) for k, v in value.items()}
    return value


def validate_selection(selection: ModelSelection, facts: list[EvidenceFact]) -> list[EvidenceFact]:
    available = {fact.id: fact for fact in facts}
    if len(set(selection.fact_ids)) != len(selection.fact_ids) or any(
        i not in available for i in selection.fact_ids
    ):
        raise AppError(
            502, "LLM_OUTPUT_REJECTED", "The model returned unverifiable evidence references"
        )
    return [available[i] for i in selection.fact_ids]


def render_answer(facts: list[EvidenceFact], selection: ModelSelection) -> str:
    selected = validate_selection(selection, facts)
    lines = []
    for fact in selected:
        value = (
            json.dumps(fact.value, ensure_ascii=False, default=str)
            if not isinstance(fact.value, str)
            else fact.value
        )
        lines.append(f"{fact.label}: {value}" + (f" {fact.unit}" if fact.unit else ""))
        if fact.limitation:
            lines.append(fact.limitation)
    lines.extend(EXPLANATIONS[key] for key in selection.explanation_keys)
    if not selected:
        lines.insert(0, "Ich kann das mit den verfügbaren Daten nicht verifizieren.")
    bounded: list[str] = []
    size = 0
    for line in lines:
        if size + len(line) > 11500:
            bounded.append("Weitere Belege stehen in den verknuepften strukturierten Ergebnissen.")
            break
        bounded.append(line)
        size += len(line) + 2
    return redact("\n\n".join(bounded))
