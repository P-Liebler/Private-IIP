# PR10E – Bedienbarkeit und sichtbare Funktionen

Stand **29.10.2026**: **PENDING_USER_TEST**. Es steht keine unabhängige
Testperson zur Verfügung. Es wurden keine Erfolgsquote, Dauer, Fehlklicks oder
menschlichen Beobachtungen erfunden. Die bestehende PR6-/PR9-Oberfläche und das
Designsystem bleiben erhalten.

## Tatsächliche technische Prüfung

Die bestehende PR9-Baseline enthält 31 Browserfälle. Der erneute lokale
Standalone-Lauf besteht mit **31/31 Fällen**; Testmodus und temporäre Rollen
sind danach zurückgesetzt. Die endgültigen Ergebnisse sind im
[PR10-Regressionsbeleg](security/pr10-20261029/regression-final.json) gebunden.
Der [tatsächliche Remote-Lauf](security/pr10-20261029/remote-ci.json) auf
`dd601be4bf916550932c9d9067bad1cf7c10c2c6` besteht bereits mit 31/31 Fällen.
Das ersetzt keine unabhängige Person oder Android-/VPN-Zielabnahme.

Die vorhandenen automatisierten Fälle prüfen unter anderem Anmeldung,
Portfolio/Konto, Importvorschau und explizite Zuordnung, wiederholten Import,
Bewertung/FX, Depotabgleich, unbekannten Einstand, Korrektur/Voids, Herkunft,
Quellen-/Modellgates, Einstellungen, mobile Navigation und CSP. Die numerischen
Assertions bleiben erhalten. Eine erfolgreiche Importantwort allein ist keine
erfolgreiche Gesamtbewertung; der bestehende Test prüft die tatsächliche
Bewertungsantwort und ihren dargestellten Wert.

Die neue ECB-Korrektur und Caddy-/Recovery-Härtung betreffen nachgewiesene
Backend-/Betriebsfehler. Sie werden nicht als beobachtete UX-Probleme bezeichnet.
Eine weitere Design-Neuentwicklung wurde nicht begonnen.

## Vorhandene Kennzeichnung gesperrter Funktionen

`components/ui/primitives.tsx` unterscheidet unter anderem fehlende/veraltete
Daten, Quellenfreigabe, experimentellen SHADOW-Betrieb und fehlende
Voraussetzungen. Datenbetrieb, Validierung und Systemstatus zeigen getrennte
Forecast-/Recommendation-/Produktionsgates. API-Gates bleiben maßgeblich;
UI-Capabilities erteilen keine Rechte. Eine sichtbare experimentelle Funktion
ist keine validierte Anlageempfehlung oder genehmigte Finanzquelle.

Der LLM-Ausfall muss den vorhandenen strukturierten `LLM_UNAVAILABLE`-Zustand
liefern; Portfolio, Ledger und Datenqualität dürfen keine erfundenen
Erklärungen oder Ersatzwerte erhalten. Fehlender Benchmark ist keine Nullkurve.
Die vorhandenen Backend-/Browser-/Coreproben prüfen diese Zustände getrennt.

## Ausführbarer unabhängiger Test

Das [bestehende PR7-Protokoll](ux/PR7_BEGINNER_TEST.md) wird weiterverwendet.
Solange Security/Zielbetrieb fehlen, darf die echte Testperson ausschließlich
eine isolierte synthetische Umgebung verwenden. Ohne technische Einführung:

1. Anmelden.
2. Portfolio erstellen.
3. Konto hinzufügen.
4. Datei importieren und Vorschau bestätigen.
5. Position finden.
6. Gesamtwert und seine Grundlage erklären.
7. Eine Datenlücke erkennen.
8. Eine belegte Korrektur durchführen.
9. Datenquelle und Datenalter prüfen.
10. Einstellungen finden; anschließend abmelden.

Build/Digest, Gerät, Browser, Bildschirmgröße, pseudonymisierte Person und
tatsächliche Hilfen dokumentieren. Je Aufgabe Dauer, Fehlklicks, Unsicherheit,
Fehlermeldung und Abbruch erfassen. Erst daraus konkrete reproduzierbare
Mängel ableiten, gezielt korrigieren und erneut mit der Person prüfen. Private
Zugangsdaten, Depotoriginale und personenbezogene Protokolle bleiben aus Git/CI.

**Menschliche Bedienbarkeit bleibt unvalidiert.** Automatisierte Prüfungen und
eine echte Beobachtung mit synthetischen Daten sind jeweils eigene Belege;
keiner von beiden ersetzt den echten Portfolioabgleich aus PR10D.
