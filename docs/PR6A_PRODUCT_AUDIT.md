# PR6A – Produktaudit

Stand: 23.10.2026. **IN PROGRESS.** Basis und gefetchtes origin/main: `f05cb70cc7db40d6185892e88aed6c6e4bcd871c`. Kein Push, Release, produktiver Cutover oder Quellenentscheid.

## CI und Runtime

GitHub-Run `39912579223`: Job `120278716684` verify SUCCESS; Job `120278716898` Security FAILURE im Dependency-Audit, nachfolgende Imagegates übersprungen. Originales Artefakt `12483388145` heruntergeladen; Archiv-SHA256 `8634b61b6e6cb03ff88b05ddc3d6c1020d1794276e9760aa5777646257574ec7` stimmt mit GitHub überein. Originalzip/JSON verbleiben unverändert im ignorierten lokalen Nachweisverzeichnis.

Das originale `pr4-core-dependencies.json` identifiziert **opentelemetry-api 1.45.0 / CVE-2026-114603 / GHSA-xcq7-p3pf-p88h**, Fix 1.45.1. Beide aktiven CI-Lockdateien entsprechen den Git-Blobs des Ausgangscommits. Ein roher Windows-Dateihash des Core-Locks unterscheidet sich ausschließlich durch CRLF/LF. Kein Legacy-Lock wurde im Dependency-Audit geprüft. Der Befund ist im aktualisierten Advisorybestand vorhanden; die alte lokale Nullmeldung ist keine aktuelle Freigabe.

[Herstelleradvisory](https://github.com/open-telemetry/opentelemetry-python/security/advisories/GHSA-xcq7-p3pf-p88h), geprüft 23.10.: übermäßig aufwendige Verarbeitung eingehender tracestate-Header, korrigiert in 1.45.1. Gezielter Core-/Dev-Patch ohne numerische Änderungen, neuer Runtimevertrag `PR6_CORE_OTEL_1451_V1`; Startguard verweigert alten installierten Stand. PR5-Locks bytegetreu separat archiviert. Alte Modelle/Prognosen bleiben unverändert; strikter Dependency-Gate und getrennter networkloser Legacyprozess bleiben erhalten. Vier fokussierte Runtime-/Legacytests bestanden; aktueller Core+Assistant-Audit ohne bekannte Befunde.

Die aufgezeichnete vollständige Release-Securityprüfung enthält weiterhin offene Store-/Image-Criticals. Der Dependency-Fix allein kann diese CI-Sperre nicht legitim grün machen. Keine Abschaltung oder Ignore-Regel. Finale Image-/Restore- und Remotezustände werden separat ergänzt.

## Baseline und Inventar

Vor dem UI-Umbau lokal erneut bestanden: **281 Backendtests**, eine bestehende Starlette/httpx-Deprecation-Warnung; **35 Hosttests**, Frontend-Lint/Typecheck/Standalone-Build und **22 Browserfälle ohne Skips**. Alle Tests ausschließlich lokal/synthetisch, keine Finanzprovider-Netzwerkaufrufe. Der neue Gesamtstand benötigt eine eigene abschließende Regression.

Inventar der vorhandenen Routen, Endpunkte, Zustände, Berechtigungen und E2E-Abdeckung wird aus den tatsächlichen Quelldateien aufgebaut. Statische Existenz ist kein Funktionsnachweis. Bekannte konkrete Mängel:

- Mehr als 20 gleichrangige Navigationsziele; Betreiberlinks ohne Sichtbarkeitsgrenze.
- Feste dunkle Farbangaben, keine Themepräferenz oder gemeinsame Design-Tokens.
- Startablauf verlinkt Verwaltungsseiten, statt durch wenige Felder zu führen.
- Der neue PR5-Übersichtsblock prüft Allokation auf COMPLETE, während der bestehende Vertragsstatus AVAILABLE lautet.
- CSV verlangt bisher UTF-8/Komma/ISO/Dezimalpunkt; Formatklärung fehlt.
- Charts sind einfache SVGs; Lade-/Fehler-/Leerezustände und Tastaturverhalten variieren zwischen Seiten.

## Weitere Abhängigkeiten

Aktualisierte lokale Evidenz: 297 Backendtests, 35 Hosttests, Ruff/Format/Mypy, Frontend-Lint/Typecheck/Standalone-Build und frische Migration 0021/78 Tabellen bestanden. Das statische Inventar enthält 31 Routen/215 API-Deklarationen; die kuratierte [Funktionsmatrix](ux/FUNCTIONAL_MATRIX.md) nennt Benutzerziele und Grenzen. Der aktuelle [Gesamtbericht](PR6_ACCEPTANCE_REPORT.md) führt finale Browser-/Restore-/Securitynachweise, ohne Baselinebefunde umzuschreiben.

Keine reale externe Quelle ist durch den PR6-Auftrag automatisch freigegeben. Ohne konkrete Rechte-/Operatorentscheidung bleiben Liveabruf und Schedulerabnahme BLOCKED. Der Nutzer wünscht eine allgemeine Prüfung verschiedener ISINs statt einer konkreten Instrumentliste; Zuordnung zu Börse/MIC und Handelswährung bleibt erforderlich. Fehlender Zielhost, Storagefreigabe, reale Portfolio-/Forecast-/Strategievalidierung und externe Anfängertestpersonen bleiben eigenständige Nachweise.

Weitere aktuelle Dependency-Prüfung: Next.js 16.3.8 ist von neu veröffentlichten Advisories betroffen, darunter [GHSA-2464-fhr4-w9xw](https://github.com/advisories/GHSA-2464-fhr4-w9xw). Gezielt auf Next.js und eslint-config-next 16.4.2 aktualisiert. npm meldet danach weiterhin fünf High-Einträge der Entwicklungswerkzeugkette über das ungepatchte braces; keine pauschale Ignore-Regel oder erzwungenes Downgrade. Die danach ausgef?hrten Audit-/Image-Nachweise vom 23.10. sind im Gesamtbericht datiert; sie sind keine neue Securityfreigabe vom 26.10. Die UI-Pakete sind exakt gepinnt.
