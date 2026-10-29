# PR9E – Technische Endabnahme und Releasekandidat

Stand **29.10.2026**: **LOCAL_SYNTHETIC_VERIFIED / SECURITY_BLOCKED / NOT_RELEASED**.

## Tatsächliche finale Nachweise

| Prüfung | Ergebnis |
| --- | --- |
| Core-Backend | **306/306**, exaktes Produktionsimage `5a925e0e…`, UID10001/read-only; separate Testwerkzeuge überschreiben keine der 66 Core-/Supportdistributionen |
| Normaler Produktionsbuild für CI | Eigener Digest `e0fb31b2…`, **306/306**, eigener nativer Probe, Scan/SBOM und vollständiger separater Restore |
| Host | **155/155**, Ausgangsbaseline 82 erhalten |
| Browser | **31/31**, bestehende 30 Fälle plus parserbasierte Style-CSP-/Radixprüfung; abgeschlossener Standalone-Build, Normalmodus/Rollen anschließend zurückgesetzt |
| Ruff / Format / Mypy | Bestanden; **309** formatierte Dateien, **203** Mypy-Quelldateien |
| Frontend | Lint, Typecheck, Standalone-Build und tatsächliches Core-Produktionsimage bestanden |
| Compose / Config | Finaler Scope und tatsächliche gestoppte Containerimages/-Configlabels stimmen mit aktueller aufgelöster Stagingkonfiguration überein |
| Fresh Migration / Drift | Beide Backendimages: `0021_ui_requests`, alle **78 explizit geforderten Tabellen** geprüft; kein neues Upgrade/Schema-Drift. Dies ist eine Teilmenge, keine Gesamtzählung sämtlicher Tabellen. Keine Migration geändert |
| Security / SBOM | Frische vollständige 13-Service-/9-Imageaufnahme; **13/13** Original-SBOMs formal gültig; **SECURITY_BLOCKED**, kein grünes Releasegate |
| Dependencies / Source | Frische Core-/Support-, MLflow- und NPM-Audits; finale Source-Secretsprüfung ohne bekannte Findings; keine Approvalaussage |
| Backup | Bestehender Motor, ruhender finaler Core, **1385** gebundene Dateihashes, synthetische Originale und bestehende Migrationsbelege |
| Isolierter Restore | **Bestanden**, dieselben finalen API-/PG-/Store-/S3-Client-/Legacy-Pins; Cleanup bestätigt |
| Finanz-/Archivverträge | Historisch **CHF 10’180**, heute explizit **STALE_PRICE**, keine Null-/vollständige Ersatzbewertung |
| Ausfall / Session / Wiederholung | Bestehende Backend-/Browserfälle für Provider-/Netz-/Sessionfehler, Korrekturen, Voids, Idempotenz, Objekt-/Quellenintegrität bestanden |

[Maschinenlesbare Regression mit Originalprotokollhashes](security/pr9-20261028/regression-final.json), [Core-Restore](security/pr9-20261028/restore-core.json), [separater Standardbuild-Restore](security/pr9-20261028/restore-standard-production.json).

## Fehlversuche bleiben erhalten

Die erste Browserbaseline bestand 29/30. Private-Beta-Prüfungen warteten zunächst zu früh auf die UI; sie synchronisieren jetzt auf die tatsächliche exakte Bewertungsantwort. Der zusätzliche CSP-Test trennte zunächst HTML-Probe und normale Anmeldung nicht sauber und verwendete einen Textlocator, der Styletexte ausschließt. Korrigiert wurden die Testabläufe, keine Finanzassertion oder CSP-Schutzregel. Spätere Läufe unter konkurrierender Build-/Scan-/Restorelast zeigten weitere begrenzte Lade-/Sessiontimeouts. Der finale vollständige Lauf wurde nach Abschluss der schweren Prüfungen ausgeführt; alle Originalfehlprotokolle bleiben lokal erhalten. Keine Produktions-SLA oder menschliche UX-Abnahme wird daraus abgeleitet.

Im ersten Core-Orchestrierungsversuch wurde der erfolgreiche One-shot-CA-Export mit `--wait` als Daemon behandelt; anschließend war eine abgebrochene neue DB-Initialisierung unvollständig. Originalvolumes waren nicht betroffen. Die fehlerhaften eigenen Stagingvolumes wurden erhalten und gestoppt. Der finale neue eigene Core verwendet einen separaten CA-Exitcode-Schritt und authentifizierte TCP-SQL-Readiness; keine Reparatur oder verdeckte Wiederverwendung einer Teilinitialisierung.

## Bestehende unveränderliche Historie

Der ursprüngliche PR8-Backupstand wurde in neue Volumes übernommen und **vor** Workerstart mit allen alten Archivhashes abgeglichen. Danach wurden nur explizit erlaubter monotoner Schedulerfortschritt und je eine neue eigene synthetische Preis-/FX-Beobachtung zugelassen. [Zeilenbezogene Delta-/Hashbelege](security/pr9-20261028/core-archive-preservation.json).

Dataset-/Raw-/Modell-/Prognose-/Outcome-, Risiko-/Szenario-/What-if-, Profil-/Strategie-/Review-, Assistenten-/Dokument-/Embedding- und PR1-/PR2-Evidenzverträge sind restauriert. Dokumentrückzüge und UI-Idempotenzreceipts bleiben eigene append-only Checks. Historische Modell-/P6-Manifeste, numerische Locks, alte RCs und frühere Checkpoints wurden nicht geändert. Der dynamische Legacy-Verifier bestätigt seinen bestehenden begrenzten Byte-/Installationsvertrag; vollständige historische ML-Inferenz wird damit nicht neu validiert.

Goldenportfolio: **CHF 10’180 ausschließlich am 26.10.2026 15:18:05.987683 UTC**. Der identische alte Bestand darf am heutigen Stichtag keine vollständige oder Nullbewertung liefern und muss `STALE_PRICE` zeigen. Keine künstliche Kursauffrischung.

## Neuer exakter Kandidat

[PR9_CORE_V1_RC1](../ops/releases/pr9-core-v1-rc1-manifest.json) bindet tatsächlichen HEAD plus Git-sichtbare Arbeitsbytes, alle 13 Servicepins, Original-SBOMs, Locks, Konfiguration, Security-/Regressions-/Restorebelege und Alembic-Head. Nur seine eigene Datei ist aus dem Source-Hashsatz ausgeschlossen. Nach Erzeugung werden keine Quellbytes verändert; Validator und Restore-Scope-Abgleich müssen bestehen. Der frühere RC3 bleibt unverändert.

Der Kandidat ist **NOT_RELEASED_OPERATOR_AND_SECURITY_GATES_REQUIRED**. Das Manifest erzeugt keine Security-, Zielhost-, Recovery-, Quellen-, Forecast- oder Strategieentscheidung. Der nächste spätere Push braucht einen neuen tatsächlichen Remote-CI-Lauf. Kein Push/Release/Cutover wurde ausgeführt.

[Security-Restentscheidungen](PR9A_SECURITY_CLOSURE_REPORT.md), [Installation und fehlende Infrastruktur](PR9B_INSTALLATION_READINESS_REPORT.md), [Quellen](PR9C_REAL_DATA_ENABLEMENT_REPORT.md), [reale Benutzerabnahme](PR9D_USER_PILOT_REPORT.md), [Gesamtstatus](PR9_ACCEPTANCE_REPORT.md).

## Separates OpenShift-Ziel

[Red Hat OpenShift GitOps](OPENSHIFT_GITOPS_ACCEPTANCE_REPORT.md) ist lokal
vorbereitet und im Source-Hashsatz sichtbar. Der 13-Service-Compose-Scope und
seine Restoreevidenz gelten weiterhin ausschließlich für diesen Composevertrag.
Keine OpenShift-SCC-, CSI-, Service-CA-, GitOps-Sync- oder Clusterrestoreabnahme
wird in diesem RC behauptet. Backend-/Browser- und Restoreläufe stammen vom
28.10.2026; finale Host-/Konfigurationsprüfungen vom 29.10.2026.
