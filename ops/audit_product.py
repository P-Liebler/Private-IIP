"""Inventory actual frontend routes and backend declarations; no provider requests.

Static state detection is deliberately labelled as inspection, not E2E evidence.
"""
import ast
import json
from pathlib import Path
import re


GOALS = {
    "analyses": "Vorhandene Portfolioanalysen und ihre Voraussetzungen öffnen",
    "login": "Privat anmelden und zweiten Faktor bestätigen",
    "dashboard": "Vermögen, Datenprobleme und nächste Aufgabe verstehen",
    "portfolios": "Portfolio, Konten, Bestände und Buchungen verwalten",
    "instruments": "Instrumentidentität suchen und prüfen",
    "instrument": "Instrument, Kurse und belegte Analysen prüfen",
    "watchlists": "Beobachtungslisten und private Notizen verwalten",
    "research": "Nachvollziehbare Fundamentals und Scores vergleichen",
    "news": "Archivierte Nachrichten und Originalquellen finden",
    "backtests": "Historische Datensätze und Strategien reproduzierbar prüfen",
    "models": "Experimentelle Modelle und Validierung nachvollziehen",
    "recommendations": "Gesperrte oder zulässige strukturierte Bewertungen prüfen",
    "assistant": "Vorhandene Evidenz erklären lassen",
    "documents": "Eigene zulässige Dokumente archivieren und durchsuchen",
    "alerts": "Benachrichtigungen und Regeln verwalten",
    "daily-brief": "Belegte Tageszusammenfassung ansehen",
    "optimizer": "Portfoliohypothese ohne Buchung simulieren",
    "time-machine": "Damals tatsächlich verfügbare Historie prüfen",
    "imports": "Zulässige Originaldateien prüfen und importieren",
    "data-quality": "Datenlücken und ihre Korrektur finden",
    "data-operations": "Begrenzte Datenaufträge und Verfügbarkeit prüfen",
    "settings": "Konto, Sicherheit, Darstellung und Quellen verwalten",
    "system": "Autorisierte Betriebs- und Freigabezustände prüfen",
}
EXPERIMENTAL = {"models", "recommendations", "assistant", "optimizer", "time-machine"}


def inventory(root=Path(".")):
    routes = []
    app = root / "frontend/web/app"
    for path in sorted(app.rglob("page.tsx")):
        parts = [p for p in path.relative_to(app).parts[:-1] if not p.startswith("(")]
        route = "/" + "/".join(parts)
        text = path.read_text(encoding="utf-8")
        module = parts[0] if parts else "root"
        helpers = re.findall(r'from ["\'](@/lib/api[^"\']*)', text)
        sources = [(path, text)]
        for helper in helpers:
            target = root / "frontend/web" / (helper.removeprefix("@/") + ".ts")
            if target.exists():
                sources.append((target, target.read_text(encoding="utf-8")))
        references = sorted(set(re.findall(r'["\'`](/[^\s"\'`<>]*)["\'`]',
                                           "\n".join(s for _, s in sources))))
        routes.append({
            "route": route, "source": path.as_posix(),
            "user_goal": GOALS.get(module, "Weiterleitung zur privaten Startansicht"),
            "data_source": "Authentifizierte bestehende API; lokale kanonische Daten, Ledger oder private Evidenz. Keine Livewerte aus der UI.",
            "api_helper_sources": [p.as_posix() for p, _ in sources[1:]],
            "literal_route_references": references,
            "loading_state_inspected": bool(re.search(r"isPending|isLoading|busy|loading", text)),
            "empty_state_inspected": bool(re.search(r"Keine|keine|Noch kein|length\s*===?\s*0", text)),
            "error_state_inspected": bool(re.search(r"isError|error|catch", text)),
            "success_state_inspected": bool(re.search(r"data|result|notice|message", text)),
            "permission": "Session; Betriebs-/Daten-/ML-Aktionen zusätzlich serverseitige Allowlist",
            "mobile_acceptance": "NOT_TESTED",
            "e2e_scope": "Synthetische Browserfälle; konkrete Routen-/Aktionsabdeckung und aktuelle Ergebnisse im PR6-Abnahmebericht prüfen",
            "baseline_status": "EXPERIMENTAL" if module in EXPERIMENTAL else "WORKING" if module == "login" else "PARTIAL",
            "limitations": "Reale Quellen-/Daten-/Modell-/Strategie-/Securitygates bleiben unabhängig; statischer Befund ist kein Funktionspass.",
        })
    endpoints = []
    for path in sorted((root / "backend/app/api").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        prefix = ""
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                for keyword in node.value.keywords:
                    if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant):
                        prefix = str(keyword.value.value)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                if decorator.func.attr not in {"get", "post", "put", "patch", "delete"}:
                    continue
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    endpoints.append({"method": decorator.func.attr.upper(),
                                      "path": prefix + str(decorator.args[0].value),
                                      "source": path.as_posix(), "function": node.name})
    return {"scope": "STATIC_INSPECTION_NOT_FUNCTIONAL_ACCEPTANCE", "routes": routes, "endpoints": endpoints}


if __name__ == "__main__":
    output = Path("docs/ux/ROUTE_API_INVENTORY.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    value = inventory()
    output.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Inspected {len(value['routes'])} routes and {len(value['endpoints'])} API declarations")
