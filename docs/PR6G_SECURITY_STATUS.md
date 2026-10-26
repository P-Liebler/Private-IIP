# PR6G – Sicherheitsstatus

Prüfstand: 23.10.2026. **SECURITY_BLOCKED**. Lokale Verbesserungen sind keine Freigabe für private Produktivdaten oder Deployment.

Abgleich 26.10.: Die folgenden Dependency-/Image-/DB-Befunde sind historische Nachweise vom 23.10.; keine frische Vulnerability-Abnahme am 26.10. behauptet. Die Trivy-DB liegt außerhalb des 48-Stunden-Fensters einer neuen Releaseprüfung. Vor einem Release sind aktuelle Scans und alle bestehenden Reviews erneut erforderlich.

Ein separater Quelltext-Secret-Scan am 26.10. meldet **NO_KNOWN_SECRET_FINDINGS / 0 Befunde**. Der [sichere Befundindex samt exakten Snapshot-Dateihashes](security/PR6_SOURCE_SECRETS_20261026.json) enthält keine Scanner-Matches. Lokale ignorierte Secrets/Backups sind nicht exportiert. Dies ist ein Secret-Snapshot, kein neuer Dependency-/Image-Scan und keine Garantie vollständiger Geheimniserkennung.

## Dependency-Reparatur

Das verifizierte Originalartefakt des Remote-Laufs `39912579223` nennt `opentelemetry-api==1.45.0`, CVE-2026-114603 / GHSA-xcq7-p3pf-p88h. Aktive Core-/Dev-Locks und der Runtimeguard verwenden gezielt 1.45.1. Die exakten vorherigen Lockbytes sind unter `backend/legacy_contracts/pr5/` erhalten. Numerische Modellpins und archivierte Manifeste wurden nicht geändert. Der neue Backend-Kandidat baut auf dem exakt gepinnten PR5-Image auf und installiert den Patch mit `--no-deps`; `pip check` bleibt verpflichtend.

Der aktuelle Core-/Assistant-Dependency-Audit meldet null bekannte Befunde. Next und eslint-config-next wurden aufgrund eines neuen Advisories von 16.3.8 auf 16.4.2 aktualisiert. `npm audit --omit=dev` meldet null bekannte Befunde; der vollständige npm-Audit meldet fünf High-Befunde im Entwicklungsbaum einschließlich `braces` ohne verfügbaren Patch. Kein Audit wurde abgeschaltet, kein Ignore ergänzt und kein `--force` verwendet.

Nachweise: `backups/pr6-core-dependencies.json`, `backups/pr6-ui-audit-production-final.json`, `backups/pr6-ui-audit-all-final.json`. Lokale Originale unter `backups/` sind absichtlich nicht im Git. Der spätere Remote-CI-Pass ist **NOT_VERIFIED**; es gab keinen Push dieses Arbeitsstands.

## Image- und Betriebsgrenzen

Ein geändertes Image benötigt einen neuen exakten Scan. Die PR6-Scans verwenden verifizierten Trivy 0.76.0 mit Datenbank vom 23.10.2026 und behalten Originalberichte sowie originale CycloneDX-Bytes. Fehlgeschlagene Versuche aufgrund nicht vorhandener Tags bleiben als `SCAN_INCOMPLETE` erhalten. Gültige spätere Versuche reparieren keine Originaldatei.

Das vorhandene MinIO hat weiterhin nicht freigegebene Critical-/High-Befunde. Backend-/optionale native Pakete und verbleibende Highs benötigen ein konkretes Review. Der lokale Seaweed-/PG17-Kandidat ist weder ein automatischer Storage-Fallback noch eine genehmigte Major-Migration. Unveränderte übrige PR4-Images erhalten durch einen partiellen PR6-Scan kein neues Gesamtsiegel. Die bestehenden Releasegates werden nicht umgangen.

## Erhaltene Grenzen

- Sessiontokens bleiben in HttpOnly-Cookies und gehashten Datenbankfeldern; Theme-Cookies enthalten nur Darstellung.
- UI-Capabilities sind Sichtbarkeitshinweise. Besitzrechte und getrennte Daten-/ML-/Betriebsrollen werden serverseitig geprüft.
- Quelle: approved + enabled + in-scope vor jedem Request. Kein Live-Collector wurde für diese UX-Arbeit freigegeben.
- Dokumententfernung ist ein unveränderlicher Rückzug, keine zugesicherte physische Löschung.
- Finanzielle Mutationen nutzen Bestätigung, atomare Wiederholungsbelege und bestehende Ledgerverträge.
- Produktivmanifest, Securityreview, Zielhost/VPN, CA, unabhängiges Backupziel, Zeitplan und Schlüsselwiederherstellung bleiben offen. Der Nutzer hat ausschließlich lokale Vorbereitung autorisiert.

## Vor einem Release

Aktuelle exakte Teilinventare und formal gültige originale SBOMs: [PR6 final](security/pr6-20261023-final/inventory.json), [Schema-/Hashprüfung](security/pr6-20261023-final/sbom-validation.json). Der frühere Stand `pr6-20261023` bleibt als eigener Versuch erhalten. Beide enthalten keine genehmigte Ausnahme; das finale Webimage rc6 ersetzt nur den neu gescannten Webkandidaten. Andere Komponenten wurden nicht als neue Builds ausgegeben.

Originale Image-/SBOM-Nachweise des tatsächlich auszuliefernden Builds validieren, sämtliche Blocker beheben oder nach geltender Policy konkret prüfen, Zielhost unabhängig abnehmen und nur das genehmigte unveränderliche Manifest starten. Ein lokaler synthetischer Browser- oder Restore-Pass ersetzt diese Entscheidungen nicht.
