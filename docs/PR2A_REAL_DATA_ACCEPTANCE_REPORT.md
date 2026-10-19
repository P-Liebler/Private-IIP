# PR2A – Controlled Real Data Onboarding & Historical Evidence

Stand: 19.10.2026; erste getrennte Zwischenabnahme am 16.10.2026 vor PR2B. **PR2A TECHNICAL FUNCTIONAL · PR2A BLOCKED_BY_SOURCE_APPROVAL.** Die technische Onboarding-/Prüfschicht ist abgenommen; eine reale Datenabnahme wurde nicht erreicht. Abschließende Regression, Browser und Recovery sind bestanden und im [PR2-Gesamtbericht](PR2_ACCEPTANCE_REPORT.md) dokumentiert. Die Zwischenbefunde bleiben als historische Nachweise erhalten.

## Ausgangspunkt und Baseline

`main`, `cfa8c51230d42f6a1d3cc0b766a8c2449dd04ec4`, sauber. Read-only `git ls-remote` bestätigte denselben Remote-main. PR1-Run [38889975378](https://github.com/P-Liebler/Private-IIP/actions/runs/38889975378) wurde zunächst laufend und anschließend tatsächlich **completed/success** abgefragt; Backend, Frontend und Browserphase erfolgreich. Kein P10-Lauf wurde als PR1-Nachweis verwendet. Neue lokale Baseline: **232 Tests bestanden**, 86,96 Sekunden, eine bestehende Starlette-Warnung.

P6-Replay des Altarchivs `a4c9d4ff-07de-44d0-a89b-53e843648994`: `VERIFIED_PINNED_REPLAY`, weiterhin `dd5cd6ef97b9248eb148725797470069b9b33635df15f8506d61bf99761ea538`. Das alte P7-Artefakt wurde mit den unveränderten strikten Dependency-Gates geladen: `9706d2dc2631d0cfde24ddaad3ccd4f41b686351cd5b82ecd5e0a96fc18f5c94`, Modell weiterhin SHADOW. Das bestehende synthetische P6-Archiv hat Basiswährung USD; es wurde nicht zu einem CHF-Pilotarchiv umgeschrieben.

## Tatsächliche Quellen und Rechte

Die aktuelle Registry bestätigt SEC_EDGAR, ECB, SNB, OPENFIGI, ALPHAVANTAGE und COMPANY_IR als UNKNOWN/deaktiviert; Yahoo BLOCKED/deaktiviert, Stooq UNKNOWN/deaktiviert. MANUAL_CSV behält ausschließlich den vorhandenen genehmigten Upload-Scope. MANUAL_PIT, MANUAL_RESEARCH, MANUAL_DOCUMENTS und MANUAL_EVENTS bleiben UNKNOWN/deaktiviert. TEST_-Quellen sind technische Fixtures, keine externen Rechte.

[PR1-Rechtematrix](data/SOURCE_RIGHTS_MATRIX.md), Primärprüfung 15./16.10.2026, bleibt maßgeblich; keine neue pauschale Erlaubnis oder Aktivierung. Neue Operator-Checklisten erfassen Identität, offizielle Bedingungen, Datentypen, automatisierten Zugriff, lokale/historische Speicherung, abgeleitete Analysen, Attribution, Quoten, nächste Review, benötigte Konfiguration und exakten Scope. Notizen ändern kein Source-Gate. Persönliche Zugangsdaten gehören ausschließlich in geschützte Konfiguration.

## Reale Imports und Live-Smokes

**Keine produktive externe Anfrage ausgeführt. LIVE_SMOKE_BLOCKED_SOURCE_NOT_APPROVED.** Es wurden auch keine rechtmäßig bereitgestellten neuen Originaldateien für einen echten 3–5-Instrumente-/1-Benchmark-Piloten geliefert. Vorhandene Testdateien werden nicht als reale Originale umdeklariert. Kein Alpha-Premium-/Full-Endpunkt, kein Yahoo-/Stooq-Bypass.

Der Pilotweg verwendet vorhandene Registry-IDs, CHF, einen separaten Benchmark, eine explizite Quellenmenge und die bestehenden PR1-Jobs. Er prüft alle Quellen und technischen Voraussetzungen vor Start, erstellt eine Vorschau der maximalen Requests und erhält Fortschritt/Cancel/Resume/Raw-/Canonical-Versionen. Ein Teilauftrag über dem globalen PR1-Queue-Limit bleibt sichtbar und kann nach Fertigstellung vorhandener Jobs fortgesetzt werden. Joblinks bleiben erhalten. Ein im Audit gefundener fehlender Datennachweis wird nicht durch einen erfolgreichen Collector-Status aufgehoben.

## Gemessene technische Archivprobe

Readiness-Record `219e9547-cbeb-4e21-874d-09818a708c98`, Rohbericht lokal `backups/pr2a-audit.json`. **Ausdrücklich synthetisch**, Zeitraum 2024-01-02 bis 2024-01-05, ein Universe-Instrument plus Benchmark. Über beide Reihen zusammen acht beobachtete Sitzungen/Open-Werte. Acht geprüfte gleichwährungsbezogene FX-Sitzungen sind abgeleitete Identitätsumrechnungen, kein Nachweis acht externer FX-Fixings. Vier Dataset-Zeilen, null geeignete strenge Trainingsbeobachtungen, vier fehlende/unverifizierte Labels; Momentum20 und Volatilität20 fehlen je viermal. Ohne registrierte Fenster bleiben Train/Validation/Calibration/OOS-Zahlen **nicht ausgewertet**, nicht scheinpräzise aufgeteilt.

Blocker: Quellenfreigabe, nicht belegte reale Herkunft, nicht vollständig abgedeckte Quellenpolicy, historische PIT-Lücken, Delisting-Coverage, fehlende Fundamentals, unzureichende Historie und fehlende Experimentfenster. Die Probe belegt die technische Erklärung der Hindernisse; sie belegt kein reales Coverage-Prozent und keine finanzielle Modellgüte.

## Herkunft, PIT und Corporate Actions

Originalbelege referenzieren exakte Raw-IDs/SHA-256 und einen identifizierten Operator. REAL_MANUAL/REAL_PROVIDER sind prüfpflichtige Herkunftsklassifikationen; öffentliche historische Verfügbarkeit entsteht weiterhin ausschließlich aus P6-Evidenz. TEST_-Quellen und gekennzeichnete synthetische Originale dürfen nicht als REAL attestiert werden. Abweichende Raw-Hashes, fehlerhafte/leere Antworten oder fremde private Uploads werden abgewiesen. Auch ein USER_ARCHIVE-Flag allein genügt nicht.

Price/Open/Volumen, FX, Fundamentals, Actions nach Typ, historische Membership, Delistings und PIT bleiben getrennte Gates. Split-/Dividendenlisten beweisen keine Vollständigkeit; unbekannte Merger/Spinoffs bleiben Lücken. Historische Membership kommt aus dem gewählten P6-Universe/Dataset, nicht aus heutigen Watchlists. Ohne reale Belege ist weder eine umfassende Action-Historie noch Survivorship-Freiheit nachgewiesen. Keine rückwirkenden lokalen Beobachtungs- oder Modellzeitpunkte.

## Technische Zwischenprüfung und Freigabegrenze

19 neue Unit-Fälle und drei lokale Integrationsflows bestanden zum Zwischenstand, zusätzlich elf bestehende P6/P7-Kernfälle. Geprüft werden getrennte Blocker, OOS-/Embargo-Verträge, Source-Gates, Ownership, private Jobdeduplizierung, unveränderliche Prüfbelege und synthetische Forward-Abstentionen. Tests greifen auf lokale Services/Fixtures zu, nie auf Finanzprovider. Weitere Abschlussprüfungen folgen im Gesamtbericht.

Die technische PR2A-Zwischenabnahme erlaubt die angeforderte weitere PR2B-Infrastrukturarbeit. **Reale Quellenrechte, echte Pilotaufnahme, veröffentlichungsgerechte Historie und Modell-/Strategieannahme bleiben offen.** Eine spätere echte Operatorentscheidung benötigt einen neuen Audit/Pilotbericht; diese Abnahme wird nicht nachträglich als erfolgreich umgedeutet.

## Technische Abschlussabnahme vom 19.10.2026

**PR2A TECHNICAL FUNCTIONAL · PR2A BLOCKED_BY_SOURCE_APPROVAL.** Gesamtregression 257 Backendtests und 20 Browserfälle bestanden; Source-/Ownership-/Raw-/OOS-Sperren sowie frische Migration 0019_validation/76 Tabellen geprüft. Die tatsächlichen Quellenzustände wurden am 19.10.2026 erneut aus der Registry gelesen: die genannten externen Quellen bleiben UNKNOWN/deaktiviert; MANUAL_CSV behält seinen bisherigen Upload-Scope. Keine reale Quelle wurde freigegeben, keine produktive Provideranfrage oder echte Pilotaufnahme durchgeführt.

Eine ausdrücklich synthetische lokale Restoreprobe erzeugte einen begrenzten Pilotvorschau-Beleg `c66622d6-87db-4915-9e57-d4f2b7d9b46e` und eine blockierte Abnahme. Drei vorhandene Testinstrumente plus Testbenchmark sind keine realen Pilotwerte. Die Vorschau scheitert vor Netzwerkzugriff an der ungeprüften ECB-Quelle; es wurden dafür keine Collector-Jobs gestartet. Neue datierte Golden-Testbeobachtungen und ein synthetischer Share-Basis-Beleg dienen ausschließlich den lokalen Browser-/Restoretests. Historische Versionen und deren tatsächliche Kenntniszeit bleiben erhalten.

Isolierter Restore 19.10.2026 05:31:39–05:32:55 UTC bestanden: 290 Raw-Objekte, tatsächlicher Quellen-/Collector-Checkpoint und zehn PR2-Belege, alter P6-Hash und P7-Artefakt unverändert, Golden-Portfolio exakt CHF 10'180. Einzelheiten und Grenzen im [Gesamtbericht](PR2_ACCEPTANCE_REPORT.md). Das schließt die technische PR2A-Abnahme; reale Rechte, Originale und Coverage bleiben ausdrücklich offen.
