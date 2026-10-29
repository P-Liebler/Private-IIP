# PR9 – Private Core V1: Releaseblocker und reale Einsatzvorbereitung

Stand **29.10.2026**: **LOCAL_SYNTHETIC_VERIFIED / SECURITY_BLOCKED / NOT_RELEASED**. Die lokal ausführbaren Arbeiten und Endprüfungen sind abgeschlossen. Keine Produktivinstallation, kein Push/Release, keine Quellenaktivierung und keine Modell-/Strategiepromotion.

## Getrennte Abschlusszustände

| Statusschlüssel | Tatsächlicher Zustand |
| --- | --- |
| `REMOTE_CI_STATUS` | `VERIFY_PASSED_SECURITY_FAILED; PR9_WORKTREE_NOT_REMOTE_VERIFIED` – letzter tatsächlicher Lauf 40642782341 |
| `SECURITY_STATUS` | `SECURITY_BLOCKED` – Legacy 1 Critical/47 High; Caddy ein High ohne v3-Fix; weitere Pflichtreviews offen |
| `LEGACY_VERIFIER_STATUS` | `STATIC_PRECHECK_VERIFIED_NOT_SUBSTITUTE; REQUIRED_RECOVERY_BLOCKED; EXCEPTION_NOT_APPROVED` |
| `CORE_DEPLOYMENT_STATUS` | `LOCAL_SYNTHETIC_VERIFIED; TARGET_HOST_NOT_AVAILABLE; NOT_INSTALLED` |
| `BACKUP_STORAGE_STATUS` | `LOCAL_CAPACITY_AND_PERMISSIONS_VERIFIED; FINAL_SCOPE_PREFLIGHT_VALID` |
| `INDEPENDENT_RECOVERY_STATUS` | `PENDING_INDEPENDENT_ENCRYPTED_TARGET_AND_OPERATOR_DRILL` |
| `REAL_DATA_SOURCE_STATUS` | `BLOCKED_BY_SOURCE_APPROVAL; LIVE_NOT_EXECUTED` |
| `AUTOMATIC_REFRESH_STATUS` | `DETERMINISTIC_GATED_PLANNER_VERIFIED; LIVE_CONTINUITY_NOT_VERIFIED; SCHEDULING_OFF` |
| `PORTFOLIO_FUNCTIONAL_STATUS` | `LOCAL_SYNTHETIC_VERIFIED; REAL_RECONCILIATION_PENDING` |
| `REAL_PORTFOLIO_PILOT_STATUS` | `REAL_PORTFOLIO_PILOT_PENDING` |
| `UX_USER_TEST_STATUS` | `PENDING_USER_TEST; AUTOMATED_31_OF_31_PASSED` |
| `PRIVATE_CORE_V1_RELEASE_STATUS` | `NOT_RELEASED; PR9_CORE_V1_RC1_NOT_APPROVED` |
| `FORECAST_VALIDATION_STATUS` | `NOT_VALIDATED_SHADOW_ONLY` |
| `RECOMMENDATION_VALIDATION_STATUS` | `NOT_VALIDATED_GATED` |

## Was konkret verbessert und geprüft wurde

- [OpenShift / Red Hat OpenShift GitOps](OPENSHIFT_GITOPS_ACCEPTANCE_REPORT.md):
  Core-Overlays und Argo-CD-Application/AppProject, Service-CA, eingeschränkte
  Controllerrechte und optionaler `oc`-Backuptransport lokal geprüft. Kein
  Zielcluster verfügbar; kein Sync, keine SCC-/CSI-/Clusterrestoreabnahme.
  Dieses zusätzliche Ziel hat eigene Freigaben und schließt keine PR9-Gates.

- [Security/CI](PR9A_SECURITY_CLOSURE_REPORT.md): tatsächliche Remotefehler ausgewertet, vollständiger Core-/Recovery-CI-Vertrag mit harten High-/Criticalgates und getrennten historischen Belegen. [Gemessene Runtime](PR9A_BACKEND_RUNTIME_REVIEW.md) reduziert die ursprünglichen 44 Backend-High-Zeilen auf **0**, ohne numerische Migration. Normaler CI-Produktionsbuild separat ebenfalls geprüft. Seaweed- und verfügbare Caddy-Patches eingebaut; kein Scanner abgeschaltet.
- [Legacy](security/PR9_LEGACY_VERIFIER_REVIEW.md): statische Byte-/Metadatenprüfung ohne Start alter Paketsoftware bestanden, exakter alter Recovery-Verifier bleibt sichtbar und geblockt. [Caddy](security/PR9_CADDY_REVIEW.md) und [Styleattribute](security/PR9_CSP_REVIEW.md) haben konkrete unfreigegebene Restrisikoreviews.
- [Installation/Backup](PR9B_INSTALLATION_READINESS_REPORT.md): geschützter C:-Stagingpfad, reale Größen-/Wachstumsgrenzen, endgültiger read-only Preflight mit **60’639’080’448 freien Bytes**, eigene Volumes, geführter Plan ohne Apply, physischer/BitLocker-/ACL-Zielguard und tatsächliche Operatornachweise vorbereitet. CA-One-shot- und PostgreSQL-Readinessfehler behoben. C: ist kein unabhängiges verschlüsseltes Recoveryziel.
- [Quellen](PR9C_REAL_DATA_ENABLEMENT_REPORT.md): Primärdokumentation am 28.10.2026 geprüft. Kein blinder Alpha-Fallback: tatsächliche Registryrechte, Listing/MIC/Währung/Assettyp, Zeitintervall, Quoten und bestehende Jobcheckpoints entscheiden deterministisch. Fehlende Freigabe erzeugt leere Jobliste und explizite Enthaltung. ECB/OpenFIGI vorbereitet; keine Quelle aktiviert oder live abgerufen. Allgemeine ISIN-Möglichkeit bedeutet keine pauschale Kursabdeckung.
- [Pilot](PR9D_USER_PILOT_REPORT.md): private Originalaufnahme und Stichtagsabgleich sowie bestehendes unabhängiges PR7-Aufgabenblatt ausführbar vorbereitet. Tatsächliche Originale, Zielhost und unabhängige Person fehlen weiterhin.
- [Technische Endabnahme](PR9E_RELEASE_CANDIDATE_REPORT.md): **306 Backendtests je geprüftem Backendimage, 155 Hosttests, 31/31 Browserfälle**, Ruff/Format/Mypy, Frontendchecks, Fresh Migration/Drift, 13 gültige SBOMs für neun Images und beide tatsächlichen isolierten Restores bestanden. Core-Restore prüft **1385 Dateihashes**, sämtliche alten Archivverträge, historisch CHF 10’180 und heute `STALE_PRICE`. Testmodus und Rollen zurückgesetzt; isolierte Projekte gestoppt/aufgeräumt.

## Die sechs entscheidenden Fragen

| Frage | Belastbare Antwort |
| --- | --- |
| Sind alle technisch behebbaren Core-Releaseblocker geschlossen? | Die identifizierten lokal behebbaren Runtime-, Build-, CI-Scope-, CSP-Element-, Speicher-, Refresh- und Startablauffehler sind behandelt und geprüft. **Keine vollständige Releasefreigabe:** verbleibende Befunde ohne unterstützten Fix und reale Reviews/Infrastruktur bleiben offen; PR9 ist remote nicht verifiziert. |
| Welche Securityentscheidungen brauchen Menschen? | Digestbezogener Legacy-Critical/High-Review, Caddy-v3-JWK-/DoS-Pfad, Styleattribute sowie native/Unknown-/Host-/Wartungsgrenzen. Keine genehmigte Ausnahme vorhanden. |
| Funktioniert mindestens eine genehmigte echte Quelle nachweislich? | **Nicht belegt.** ECB ist priorisiert; Rechte-/Serienreview, Aktivierung, separater Egress und tatsächlicher erster/späterer Abruf fehlen. Rechtmäßiger manueller Import bleibt vorbereitet. |
| Kann ein echtes Depot sicher aufgenommen und abgeglichen werden? | Technischer Ablauf ist vorhanden. Private Originale werden erst nach Security-/Hostfreigabe aufgenommen; tatsächlicher Brokerabgleich bleibt **pending**. |
| Ist die App ohne Einführung bedienbar? | **Nicht menschlich validiert.** Automatisierte Hauptfunktionen bestehen; unabhängige Person und tatsächliche Beobachtung fehlen. |
| Welche exakten Schritte fehlen bis Private Core V1? | Die folgenden realen Entscheidungen und Abnahmen; keine zusätzliche künstliche Testhistorie ersetzt sie. |

## Konkrete noch nötige Schritte

1. Berechtigter Securityreviewer beurteilt das [vollständige exakte Inventar](security/pr9-20261028/core-rc1/inventory.json), Legacy-/Caddy-/CSP-Reviews und übrige native Grenzen. Jede etwaige Ausnahme braucht echte Person, Nachweise, Zweck, Ablauf, Trigger und getrennte Genehmigungsreferenz; Critical bleibt bis dahin blockierend.
2. Den weiterhin fehlenden autorisierten Zielhost mit privatem Hostnamen und VPN/DNS bereitstellen. Den [Installations-/Hostablauf](operations/PRIVATE_CORE_INSTALLATION.md) auf tatsächlichen Windows-/Android-Clients, CA, Login/TOTP, Alarmempfang und Hostreboot ausführen. Lokales Staging schließt diese Gates nicht.
3. Physisch und administrativ unabhängiges verschlüsseltes Backupziel und getrennt verwahrte Schlüssel festlegen. Bestehenden Motor unter echtem Dienstkonto planen, Retention, freien Platz, Fehler-/Missed-Run-Alarme samt Empfang testen. Unabhängigen Restore und DB-/S3-/TOTP-/CA-/Schlüssel-Recovery tatsächlich abnehmen.
4. Quellenoperator prüft konkrete Serien/Listings sowie Automatik-/Rawarchiv-/Analyseerlaubnis. ECB initial und an einem tatsächlich späteren Veröffentlichungstag mit Originalbytes/Hashes/Korrektur-/Portfolioverknüpfung prüfen; alternativ zulässige private manuelle Originalexporte. Keine ungeprüfte Ausweichquelle.
5. Nach Security/Host eigenen echten Pilotaccount und private Brokeroriginale aufnehmen. Mengen, Cash, Gebühren/Steuern, Dividenden/Splits, Kurse, FX, Einstand und Gesamtportfolio am gleichen Stichtag vollständig klären. Keine erfundenen Ausgleichsbuchungen; Originale bleiben außerhalb GitHub/CI.
6. Unabhängige Person ohne Einführung nach [PR7-Protokoll](ux/PR7_BEGINNER_TEST.md) beobachten, tatsächliche Hürden beheben und nachprüfen. Danach separate Operatorentscheidung zum [unveränderlichen RC](../ops/releases/pr9-core-v1-rc1-manifest.json). Ein später autorisierter Push benötigt neuen tatsächlichen Remote-CI-Lauf.

Forecasts und Empfehlungen bleiben unabhängig davon **unvalidiert/gesperrt**. 0 CHF verpflichtende API-Kosten betrifft keine Hardware-/Betriebskosten. Der Kandidat wird durch Manifestgenerierung nicht genehmigt.
