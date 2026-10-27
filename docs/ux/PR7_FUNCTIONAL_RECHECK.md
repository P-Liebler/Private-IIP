# PR7 – Nachprüfung der bisherigen PARTIAL-Routen

Stand 27.10.2026. Ausgangspunkt ist die [kuratierte Funktionsmatrix](FUNCTIONAL_MATRIX.md).
Die31-Routen-Smokes und der vollständige29-Fall-Lauf sind Breiten- und
Fachworkflowbelege. Sie ersetzen keine Prüfung jeder Kombination aller
Transport-, Rechte-, Validierungs- und Recoveryfehler. Die Einträge werden
deshalb nicht allein durch einen Smoke von PARTIAL auf WORKING angehoben.

## Zustandsvertrag der Nachprüfung

- Laden und optionale Fachabfragen werden getrennt dargestellt; Shell und
  Hauptnavigation warten nicht auf ein lokales Modell oder eine fertige Kurve.
- Fehlende Daten bleiben fehlend. Unvollständige P8-Verläufe zeigen keine
  erfundene Benchmark oder Nullrendite; heutige alte Kurse sperren Gesamtwerte.
- Lesefehler dürfen keine erfolgreiche Mutation vortäuschen. Quellenfreigaben
  und Qualitätskarten werden nach einem Ladefehler ausgeblendet. Die neu
  reparierten News-/Qualitäts-Read-Retries sind per Tastatur tatsächlich geprüft.
- Mutationserfolg folgt einem erfolgreichen Backendbeleg. Preview/Bestätigung,
  stabile Anfrageschlüssel und Backend-Dublettenverträge bleiben maßgeblich.
  Nach Marktdatencommit werden aktive Leseansichten erneut abgefragt.
- Rollen-/Besitz-/Source-/Forecastgates bleiben Backendentscheidungen; sichtbare
  Fähigkeiten sind Hinweise. Fehlende Datenoperator-/ML-/Betriebsrechte sind
  keine Einladung zur Eigenfreigabe.
- Mobile390/1440-Breite und gemeinsame Tastatur-/Dialogverträge sind geprüft;
  dies ist keine vollständige Screenreader- oder unabhängige Anfängerabnahme.

## Individuelle Zuordnung

Die Spalte „Fachfälle“ nennt vorhandene Dateien unter `frontend/web/e2e/`.
Sie bezeichnet den dort tatsächlich geprüften Weg, nicht jeden Seitenzustand.

| PARTIAL-Route | Primärer Weg / Backendwirkung | Fachfälle | Weiterhin begrenzte Abnahme |
| --- | --- | --- | --- |
| `/` | Sessionabhängige Weiterleitung | product-ux | Vollständiger Session-/Recoveryfehlerraum separat. |
| `/dashboard` | Eigene CHF-Übersicht/Positionen; gemeinsame Benachrichtigungsabfrage | portfolio, product-ux | Teilwerte und Rekonstruktion bleiben gekennzeichnet. |
| `/portfolios/new` | Konto/Instrumente/CSV im bestehenden geführten Ledgerweg | product-ux, private-beta | Unabhängige Anfängerperson fehlt. |
| `/portfolios/[id]` | Ledger/Transaktionen, Bewertung, Abgleich, P8 | portfolio, private-beta, risk, intelligence | Reale Broker-/Preis-/FX-/Actionabnahme fehlt. |
| `/instruments` | Lokale Identitäten und bestätigte Zuordnung | research, private-beta | Keine universelle ISIN-/Handelsplatzabdeckung. |
| `/instrument/[id]` | Preise, Coverage, Research, archivierte Forecasts | research, forecasts | Source-/Action-/Forecastgates bleiben wirksam. |
| `/data-quality` | Tatsächliche Qualitäts-/Portfolioabfragen und Reparaturlinks | portfolio, private-beta, pr7-read-recovery | Neu:503, ausgeblendete Qualitätskarten, Enter-Retry; nicht jede Unterabfrage injiziert. |
| `/data-operations` | Preview/Start/Status/Abbruch/Wiederaufnahme begrenzter Aufträge | data-operations | Echte Finanzquellen gesperrt; kein Liveerfolg aus Fixtures. |
| `/data-operations/readiness` | Archiv-/Coverageprüfungen | data-operations, validation | Technische Readiness ist keine Finanzvalidierung. |
| `/watchlists` | Eigene Listen/Notizen, bestätigte Entfernung/Archivierung | research | Kein vollständig injizierter Transportfehlerraum jeder Mutation. |
| `/news` | Archivierte Metadaten, Quellen-/Datumfilter, Pagination | pr7-read-recovery, product-ux | Neu:503 und Enter-Retry mit erhaltenem Datum; kein Feed freigegeben. |
| `/research` | Versionierte Fakten und deterministische Regeln | research | Fehlende/stale/konfliktbehaftete Grundlagen sperren Scores. |
| `/analyses` | Navigation zu eigenen Portfolioanalysen | product-ux | Fachresultate verlangen ein geeignetes Portfolio. |
| `/documents` | Rechtegeprüfte Originale, Retrieval und bestätigter Rückzug | intelligence, product-ux | Aufbewahrung wird nicht als physische Löschung ausgegeben. |
| `/alerts` | Persistente Regeln, Meldungen und Deduplication | intelligence | Unavailable ist nicht false; kein echter Zielhostzeitplan. |
| `/daily-brief` | Archivierter regelbasierter Bericht | intelligence | Ohne LLM nutzbar; reale Eingaben nicht validiert. |
| `/settings` | Konto, Sicherheit und Theme | system-status, product-ux | Echte Schlüssel-/TOTP-Recovery und Client-CA separat. |
| `/settings/data-sources` | Versionierter Review, getrennte Aktivierung/Scope | data-operations | Neu: Ladefehler/Retry ohne alte Freigabekarten; keine Eigenfreigabe. |
| `/system/status` | Geschützte Betriebsabfragen | system-status | Lokaler Status ersetzt keine Zielhostabnahme. |

Weitere experimentelle Routen – Backtests, Modelle/Validierung, Empfehlungen,
Assistent, Optimizer und Time Machine – behalten ihre eigenen P6–P10-Gates.
Die neuen Assistentenfälle prüfen sofortige Rückmeldung, Laufzeit, Abbruch,
Verlaufabruf, vorzeitiges EOF und ehrliche Modellabwesenheit. Die native Auswahl
und ihr echter Ausfall wurden zusätzlich im getrennten Staging geprüft.

Offen bleiben die vollständig injizierte Fehlerraumabnahme über diese Fälle
hinaus, die unabhängige Testperson und reale Originale/Quellen. Diese Grenzen
sind Teil des aktuellen Status, keine stillschweigende Abnahme.
