# PR6 – Kuratierte Funktionsmatrix

Stand 23.10.2026. Das [statische Inventar](ROUTE_API_INVENTORY.json) enthält 31 Routen und 215 API-Deklarationen einschließlich Pfad, Servicefunktion, direkter Referenzen und Zustandssuchhinweise. Regexbefunde sind keine Funktionsabnahme: ausgelagerte Komponenten können Zustände enthalten. Folgende Zuordnung ergänzt Ziele, tatsächliche lokale Datenpfade und Testumfang. Testdateien liegen unter `frontend/web/e2e/`.

**WORKING** gilt nur im explizit geprüften synthetischen Umfang. **PARTIAL** bezeichnet nutzbare Teilfunktionen mit offener vollständiger Aktions-/Zustandsabnahme; **EXPERIMENTAL** behält sein fachliches Gate. Die Routen-Smokeprüfung belegt Shell/Erreichbarkeit und Breite, keinen Erfolg aller Aktionen.

| Route | Benutzerziel / lokaler Datenpfad | E2E-Datei | Status / Grenze |
| --- | --- | --- | --- |
| / | Geschützter Einstieg/Weiterleitung | product-ux | PARTIAL; Session |
| /login | Cookie-Login über /auth/login | portfolio, product-ux | WORKING; kein Token im Browserstorage |
| /dashboard | CHF-Neubewertung über /portfolio-dashboard und Portfolio-APIs | portfolio, product-ux | PARTIAL; Teilwerte/Historienrekonstruktion explizit |
| /portfolios | Eigene Portfolios auflisten/anlegen | portfolio | WORKING im geprüften Umfang |
| /portfolios/new | Ressourcen und CSV im geführten Ablauf | product-ux | PARTIAL; Anfängerabnahme offen |
| /portfolios/[id] | Ledger, Konto, Bewertung, Abgleich, P8 | portfolio, private-beta, intelligence | PARTIAL; Preis/FX/Action-Gates |
| /instruments | Lokale Identitäten suchen | research, private-beta | PARTIAL; Mehrdeutigkeit nicht automatisch akzeptieren |
| /instrument/[id] | Kurse, Coverage, Fundamentals, Actions, Forecast | research, forecasts | PARTIAL; keine globale Versorgung |
| /imports | Bestehende Raw-first-Preview/Commit-APIs | private-beta | WORKING mit synthetischen Originalen |
| /data-quality | Qualitätsprüfung und konkrete Reparaturaktionen | portfolio, private-beta | PARTIAL; fehlend bleibt fehlend |
| /data-operations | Begrenzte /data-operations/jobs und Preview | data-operations | PARTIAL; echte Quellen BLOCKED |
| /data-operations/readiness | Archiv-/Coverage-Readiness | data-operations, validation | PARTIAL; keine Finanzvalidierung |
| /watchlists | Private Listen, lokale Suche, Notizen | research | PARTIAL; Entfernung/Archivierung bestätigt |
| /news | Kanonische Nachrichten filtern | research | PARTIAL; kein neuer Feed freigegeben |
| /research | Versionierte Fakten/deterministische Regeln | research | PARTIAL; unvollständige Scores gesperrt |
| /analyses | Einstieg in eigene Portfolioanalysen | product-ux | PARTIAL; eigenes Portfolio erforderlich |
| /backtests | Gepinnte P6-Datasets/Ausführung | backtests | EXPERIMENTAL; PIT-/Ausführungsgates |
| /models | P7-Registry und Training | forecasts | EXPERIMENTAL; ML-Rolle, keine Promotion |
| /models/validation | Präregistrierte Experimente/Reviews | validation | EXPERIMENTAL; echte OOS-Evidenz fehlt |
| /models/forward-validation | Tatsächlich erzeugte SHADOW-Evidenz | validation | EXPERIMENTAL; Automatik aus |
| /recommendations | Profile und harte P9-Gates | recommendations | EXPERIMENTAL; keine reale Empfehlung validiert |
| /recommendations/validation | Strategieevidenz/Operatorreview | validation | EXPERIMENTAL; synthetisch genügt nicht |
| /assistant | Read-only Tools, gespeicherte Evidenz, lokales Modell | intelligence | EXPERIMENTAL; Ausfälle explizit |
| /documents | Rechtegeprüfte Originale/Retrieval/Rückzug | intelligence, product-ux | PARTIAL; Aufbewahrung ist keine physische Löschung |
| /alerts | Persistente Regeln und Meldungen | intelligence | PARTIAL; unavailable ist nicht false |
| /daily-brief | Archivierter regelbasierter Bericht | intelligence | PARTIAL; ohne LLM nutzbar |
| /optimizer | P8/P6-Simulation ohne Ledgerwrite | intelligence | EXPERIMENTAL; keine Order |
| /time-machine | Strict/reconstructed Archivinspektion | intelligence | EXPERIMENTAL; kein Rückdatieren |
| /settings | Konto, Sicherheit und Theme | system-status, product-ux | PARTIAL; echte Recovery separat |
| /settings/data-sources | Rechte, Scope, getrennte Aktivierung | data-operations | PARTIAL; Datenoperator |
| /system/status | Geschützter Betriebszustand | system-status | PARTIAL; eigene Ops-Rolle, kein Zielhostbeweis |

## Zustände und Rechte

Gemeinsame Query-/Mutationbehandlung liefert Lade-, Fehler-, Pending- und Erfolgszustände. Explizite Empty States bestehen unter anderem für fehlende Portfolios, Kurven, Positionen und Betreiberrechte. Finanzwerte bleiben bei fehlender Grundlage `null`/nicht verfügbar. Formular-/Gateverletzungen behalten ihre technischen Codes in Details und erhalten Benutzererklärungen. Nicht jede Transport-/Validierungsantwort ist auf jeder Seite browserseitig injiziert worden; verbleibende vollständige Fehlerraumabnahme ist offen.

Alle geschützten Routen verlangen Session und Besitzrechte. Daten-, ML- und Operationsrollen sind unabhängig; Backendgates gelten auch bei Deep-Links. Mobile Positionskarten enthalten dieselben fachlichen Angaben wie die Desktoptabelle. Die 390-/1440-Routen-Smokes und 360–1920-Themeprüfung sind am 23.10. im beschriebenen Umfang bestanden; am 26.10. zusätzlicher Normalmodus-Sichtlauf auf 390/1440 px ohne Seitenfehler. Datierung und konkrete Ausführungen stehen im Gesamtbericht. Vollständige manuelle Screenreader-/Anfängerabnahme bleibt offen.
