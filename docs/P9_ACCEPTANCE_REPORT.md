# P9 — technische Abnahme

Stand: 2026-10-15. **P9 FUNCTIONAL — RECOMMENDATIONS GATED. V3 NOT VALIDATED.** Diese Abnahme erfolgt vor Beginn von P10.

## Ausgangspunkt und Umfang

`main`, `1294080ba0042706d4df99f37f39646aea736673`, sauberer Arbeitsbaum. Baseline erneut: 155 Backend-Tests. GitHub Actions `38561223407` für den Ausgangscommit wurde vom Nutzer als erfolgreich bestätigt. Neue Änderungen wurden nicht gepusht; **REMOTE CI NOT VERIFIED FOR THIS CHANGE**. Kein Release, keine Quellenaktivierung und keine Modell-/Strategie-Promotion.

P9 umfasst private versionierte Investmentprofile, Kandidaten aus bestehenden Instrumenten/eigenen Beständen/Watchlists/Universes, harte Eligibility vor Scores, feste transparente Bewertungsregeln, P4/P5/P7/P8-Kontext, reine P8-Hypothesen, unveränderliche Bewertungen einschließlich Abstentions, historischen P6-Strategie-Replay und eine separate Operator-Abnahme. API und `/recommendations` respektieren Eigentum und Cookie-Sessions.

## Daten- und Freigabevertrag

Ohne bestätigtes Profil, vollständige NAV, aktuelle Kurse/FX/Actions, ausreichende Historie, Fundamentals/Valuation, gültigen Risiko-/Szenariokontext, Liquidität und Portfolio-Limits wird kein Score freigegeben. Fehlende Informationen ergeben `INSUFFICIENT_DATA`, bekannte harte Ausschlüsse `INELIGIBLE`. Kategorien und technische Berechtigung sind getrennt.

P7 prüft Prognosen für die Bewertung frisch. Nur aktuelle PRODUCTION-Versionen mit realer Strict-PIT-Promotionsevidenz, akzeptierter Kalibrierung, Artefakten und begrenzter Unsicherheit sind zulässig. Modell-Promotion ersetzt keine Strategieabnahme. Die vorhandenen synthetischen SHADOW-Modelle erlauben ausschließlich `NO_VALIDATED_PRODUCTION_FORECAST`. Es bestehen keine normalen freigegebenen Anlageempfehlungen.

Die feste Ausgangsregel ist **nicht als optimal nachgewiesen**. Gewichte: Excess Return .25, Konfidenz .15, Quality .20, Value .15, optional Momentum .05; Abzüge Risiko .08, Konzentration .05, Korrelation .04, Kosten .03. Pflichtkomponenten werden nicht imputiert. Fehlendes Momentum führt nicht zur Umgewichtung. Ranking: absteigender belegter Score, stabile Instrument-ID als Tie-breaker, fehlende Scores zuletzt. Ein rein synthetisches Pure-Engine-Golden liefert exakt 58.00; das ist kein finanzieller Erfolgsnachweis.

Präferenzen speichern konkrete Einheiten, harte/weiche/informative Felder und Bestätigung. Defaults sind unbestätigt. Jede Bewertung pinnt Profil-/Regelversion, P4-/Research-/Forecast-/Risiko-IDs, Eingaben, Code-/Dependency-Manifest, Batch/Kandidatenmenge und Ergebnis-Hash. UPDATE ist in fünf neuen Tabellen gesperrt; Korrekturen erzeugen neue Records. Regelcode und Registry-Hash müssen übereinstimmen. Historische Records bleiben lesbar und reproduzierbar.

## Portfolio und historische Ausführung

Hypothesen verwenden den P8-What-if-Service mit echten Cash-/Positions-/FX-Prüfungen und Kosten. Modi: Fixbetrag, NAV-Anteil, Zielgewicht; Kauf- und Verkaufshypothesen. Keine Transaktion wird erzeugt. P8 und P9 teilen die Liquiditätsprüfung. Unbekannte Klassifikationen oder Korrelationen werden nicht zu neutralen Werten.

Der Strategie-Replay verwendet damals archivierte Forecasts, Risiko, Research, Präferenzen und Modellfreigaben. Nur die separate Strategie-Freigabe darf innerhalb einer ausdrücklich offline ausgewerteten SHADOW-Strategie simuliert werden. Alle finanziellen Gates bleiben bindend. Die archivierte Kategorie muss zum gespeicherten Handlungspreview passen. HOLD/WATCH erzeugen keinen Kauf. Heutiges Ranking und später erzeugte Forecasts sind unzulässig.

P6 führt nächste Sitzung, FX, Actions, Positionen, Cash und realistische Kosten aus. Anfangsbestand und NAV müssen zum Dataset passen. Abweichende historische Cash-/Positionszustände, bekannte offene beziehungsweise am ersten Tag mehrdeutige Action-Entitlements und verspätete Signale werden abgewiesen. Ausländisches Cash und mehrere unvereinbare Signale am gleichen Tag bleiben explizit ausgesetzt. Baselines: NO_CHANGE, Benchmark-only, Equal Weight, Momentum und Quality/Value. Ohne echte Evidenz: `RECOMMENDATION_BACKTEST_UNAVAILABLE`.

Produktive Regeln erfordern Operator-Review, reale Daten, Kosten und vollständige Ausführung, mindestens 600 OOS-Sitzungen, alle fünf Baselines und drei stabile OOS-Fenster. P6-Anfragen erlauben dafür nun begrenzt fünf Kalenderjahre; das separate Session-Limit bleibt standardmäßig 400, bewusst konfigurierbar bis 1000. Ein größerer Datumsbereich erzeugt keine historische Datenverfügbarkeit.

## Verifikation

| Prüfung | Ergebnis |
| --- | --- |
| Vollständige Backend-Regression nach Ranking-/Datumsbereichserweiterung | **173 passed** |
| Abschließende P6/P9-Tests einschließlich zusätzlichem Anfangs-NAV-/Actions-Golden | **12 passed**; ein zusätzlicher Fall, Testbestand damit 174 |
| Browser-Regressionsfälle | **11 bestanden**: zehn bisherige Fälle und der neue P9-Fall |
| P9-Browser-Korrektur | Auswahl desselben Portfolios leert den Risiko-Snapshot nicht mehr; eigener P8-Setup macht den Fall unabhängig von Testreihenfolge/CI-Zustand |
| Ruff / Format / Mypy | PASS; 153 App-Dateien |
| Frontend lint / typecheck / production build | PASS |
| Compose build/start und Readiness | PASS; `/api/v1/health/ready` HTTP 200 |
| Upgrade, Schema-Drift und frische Migration | PASS; `0015_recommendations`, 55 erforderliche Tabellen |
| MLflow vollständig gestoppt | Portfolio 10180, Research/Risiko und begründete Recommendations verfügbar; Ledger unverändert; Metriken vorhanden |
| Isolierter Restore | **PASSED**, 09:31:30–09:32:28 UTC am 2026-10-15 |
| Git-Diffprüfung | PASS; alte Migrationen unverändert |

Backend-Fälle prüfen Shadow-Modelle trotz behaupteter Validierung, fehlende Produktionsprognosen, Hard Gates, Delisting/Ausschlüsse, fehlende Valuation, Liquidität, Konzentration, optionale Komponenten, Gebühren, stabile Sortierung, Profilkonflikte, Immutability, Ownership, Replay, historische Ausführungszeiten, Anfangs-NAV/Actions und unveränderten Ledger. Tests verwenden ausschließlich lokale Services oder explizite synthetische Fixtures.

Backup: `backups/p9-acceptance/sets/20261015T092457Z-67600`. Eigene temporäre PostgreSQL-/MinIO-Instanz, anschließend begrenztes Cleanup ihrer Volumes. Erhalten: Raw-Bytes/Hashes, P6-Dataset, Modellartefakt und MLflow-Metadaten, acht Forecast-Abstentions ohne erfundene Outcomes, sechs Risiko-/fünf Szenario-/fünf What-if-Snapshots und zwei Profilversionen/zwei Recommendations. P9-Historienhash `4f6fa0231b95daf8516ca209a3d23f65d8ab5cc4a448ba28e318e70a4a201fe0`; Modellartefakt `9706d2dc2631d0cfde24ddaad3ccd4f41b686351cd5b82ecd5e0a96fc18f5c94`. Privater Login und exakt **CHF 10'180** wurden im Restore geprüft. Spätere synthetische Browserläufe dürfen zusätzliche Records erzeugen; der Satz dokumentiert seinen Sicherungszeitpunkt.

## Grenzen und P10-Freigabe

Reale validierte Forecasts und eine historische Strategieabnahme fehlen. Fehlende historische Archive, inkompatible Anfangszustände oder Datenlücken erlauben keinen erfolgreichen Strategie-Backtest. Die feste Rubrik und synthetische Goldens beweisen keinen Investmentnutzen. Bestehende P4-Zielinstallations-, VPN-/CA-, unabhängige Backup-/Schedule- und Schlüssel-Recovery-Gates bleiben offen. **V3 NOT VALIDATED**, kein Produktionsrelease.

Die technische P9-Abnahme ist abgeschlossen. P10 ist durch den Gesamtauftrag bereits autorisiert und kann jetzt beginnen. Der Assistent darf diese Gates ausschließlich erklären.
