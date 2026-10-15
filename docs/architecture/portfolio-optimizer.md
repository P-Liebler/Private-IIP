# Portfolio Optimizer: Simulation

`long-only-shrinkage-slsqp-v1` arbeitet mit einem privaten, höchstens 24 Stunden alten P8-Snapshot, der zum aktuellen Ledger und den aktuellen gespeicherten Kurs-/FX-Versionen passen muss. Bestätigtes Investmentprofil erforderlich. Simulation verändert weder Ledger noch Produktionsprognosen oder Recommendations.

## Eingaben und Modell

Zwei bis 20 bereits gehaltene Instrumente, vollständige Bewertung, aktuelle akzeptierte Quotes, verifizierte Länder-/Sektormetadaten und Liquidität, mindestens 252 exakt ausgerichtete Renditesessions einschließlich relevanter Cash-FX-Renditen. Keine erfundene Nullkorrelation und kein Imputieren fehlender Werte. Negative Cashbestände/Leverage werden ausdrücklich nicht unterstützt.

Ledoit-Wolf-Kovarianz, Annualisierung 252, Symmetrie, endliche Werte und PSD prüfen. Eine versionierte Eigenwertuntergrenze von größtem Eigenwert × 1e-8 wird mit tatsächlich hinzugefügter Regularisierung archiviert; degenerierte Nullkovarianz wird abgewiesen. Matrix, Reihenfolge, Stichprobe, Shrinkage und Konditionszahl bleiben sichtbar.

Ziele: Minimum Variance, positive normalisierte Risk Budgets, explizite Target Allocation oder minimale Konzentration. Expected Return benötigt für alle Instrumente aktuelle validierte Produktionsprognosen desselben Horizonts; ohne sie `EXPECTED_RETURN_OPTIMIZATION_UNAVAILABLE`. Es wird erwartete Überschussrendite aus P7 verwendet, keine vom LLM erfundene Rendite.

Investierte Gesamtnominale bleibt konstant, Fremdwährungscash bleibt fix. Dies verhindert eine triviale All-Cash-Lösung und implizite FX-Trades. Long-only-Gewichte, Positions-, Sektor-, Länder-, Währungs-, Cash-, Volatilitäts-, Neukauf- und Turnovergrenzen werden vor und nach Kosten geprüft. Zu kleine Positionen werden entfernt und das Problem erneut gelöst. Unerfüllbare Grenzen oder Solverfehler liefern keine vorgeschlagenen Gewichte.

## Kosten, Risiko und Robustheit

Verkäufe vor Käufen, echte Decimal-Kostenrechnung durch die reine P8-What-if-Funktion. Kommission pro Order, einseitiger Spread und Slippage gemäß P8/P9. Keine Handelsausführung. P8 prüft tatsächliche verfügbare Cashkonten und FX; fehlende Cashmöglichkeit macht den Vorschlag nicht verfügbar.

Vergleiche mit NO_CHANGE, aktuellem Portfolio und Equal Weight; Equal Weight durchläuft ebenfalls P8 und Grenzprüfung. Sieben P8-Szenarien bleiben explizite Hypothesen. Unbelegte Benchmarkzuordnung erzeugt fehlende Szenarioeingaben. Stress: PSD-Mischung 75 % Kovarianz / 25 % gemeinsamer Faktor und Volatilität × 1,25; erneute Optimierung und Gewichtsänderung dokumentieren. Bei erwarteten Renditen werden Intervallunter-/obergrenzen separat optimiert. Infeasibilität, Grenzbruch oder mehr als zehn Prozentpunkte Turnover-Sensitivität bedeuten LOW_ROBUSTNESS. Erfolgreiche begrenzte Stresschecks sind kein empirischer Anlagestrategienachweis.

Jeder Lauf, auch eine Abstention, speichert Profil-/Risiko-/Prognose-/Bewertungsreferenzen, Konfiguration, Regel- und Codemanifest sowie Eingabehash. Produktionsfreigaben von P7/P9 bleiben separat offen.
