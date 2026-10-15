# Sicherheitsvertrag des Assistenten

## Erlaubte Werkzeuge

`getPortfolio`, `getHoldings`, `getInstrument`, `getFinancials`, `getForecast`, `getRisk`, `getNews`, `getPredictionHistory`, `getRecommendation`, `getDataQuality`.

Pydantic verbietet zusätzliche Argumente. Der Nutzer kann keine Nutzer-ID, SQL-Abfrage, Shell, URL, Datei oder Promotierungsaktion übergeben. Portfolio-, Chat-, Tool-Aufruf-, Dokument-, Regel-, Notification-, Brief- und Optimizerobjekte werden serverseitig auf Besitz geprüft. Instrumente und freigegebene kanonische Finanzdaten sind globale Stammdaten; private Ergebnisse sind nutzergebunden.

## Faktenvertrag

| Typ | Bedeutung |
| --- | --- |
| VERIFIED_FACT | Gespeicherte belegte Beobachtung; bei Dokumenten ausdrücklich nur der Text |
| DERIVED_METRIC | Deterministische Berechnung aus benannten Daten |
| MODEL_FORECAST | Tatsächlich archivierte validierte Produktionsprognose mit Unsicherheit |
| SCENARIO_ASSUMPTION | Explizite Hypothese, kein beobachteter Fakt |
| UNAVAILABLE | Fehlend, veraltet, nicht freigegeben oder nicht verifizierbar |

Fakten-IDs und feste Erklärungen bilden den vollständigen Antwortvertrag. Ein LLM kann eine P9-Sperre nicht überschreiben. Fehlende Eingaben werden in der Antwort erzwungen. Jede neue Handlungsempfehlung benötigt eine neue quantitative P9-Auswertung. Historische Prognosen einschließlich schlechter Ergebnisse und Abstentionen bleiben erhalten; aktuelle Tools erheben alte Ergebnisse nicht automatisch zu neuen Empfehlungen.

## Grenzen und Audit

Private Sessioncookies, Origin-/CSRF-Prüfung und bestehende Authentifizierung gelten auch für SSE. Explizite Rate-Limits, globale Advisory Locks auf einer eigenen Verbindung, Werkzeugbudget acht Sekunden, Toolausgabe 60 KB, Kontext-/Antwort-/PDF-/Dokumentgrenzen. Locks überleben Service-Commits und werden im Finally freigegeben. Browserabbruch ist unterstützt. Originaldaten gelangen nicht in Shell-Argumente. Parser läuft als festes lokales Modul.

Erkannte Passwort-/Token-/API-Key-/Bearer-/JWT-Werte werden vor Chatpersistierung und Modellkontext redigiert. Keine Prompt- oder Toolpayloads in Betriebslogs; SQLAlchemy verbirgt Parameter bei Fehlern. Dies ersetzt keine sichere Eingabe durch Nutzer: beliebig verschleierte Geheimnisse können nicht zuverlässig erkannt werden. Dokumentoriginale werden absichtlich bytegetreu archiviert und dürfen keine Zugangsdaten enthalten.

`ASSISTANT_TEST_MODE=true` ist ausschließlich mit `APP_ENV=test` zulässig. Fixture-Chats sind auf Testnutzernamen, dokumentbezogene Testembeddings auf `TEST_`-Quellen beschränkt. Der Stub ist als TEST_ONLY markiert und produziert keine Finanzdaten oder Kaufentscheidungen. CI benötigt keine realen Modelle oder externen Finanzaufrufe.

Abnahmefälle: fremde IDs, SQL/URL/Write-Argumente, unbekannte Fakten-/Quellen-IDs, injizierte Dokumentbefehle, Rechteentzug, späterer Datenimport, LLM-/Embedding-/Raw-Ausfall, Cancellation und Deduplizierung. Produktive Quellfreigaben und bestehende P4–P9-Gates bleiben unabhängig.
