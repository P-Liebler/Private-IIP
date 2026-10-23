# Separate echte Benutzerabnahme

Stand: 22.10.2026. **REAL_ORIGINALS_NOT_PROVIDED / REAL_PRIVATE_DATA_USE_NOT_APPROVED.** Dieser Ablauf ist vorbereitet, nicht ausgeführt. Synthetische Portfolio- und Restore-Goldens zählen nicht als echte Abnahme.

## Vorbedingungen

Der Benutzer löst den Pilot ausdrücklich aus, nachdem Runtime-/Storage-Security, privates HTTPS/Clienttrust und unabhängiges Backup ausreichend abgenommen sind. Eigene private Daten getrennt von E2E-/CI-Fixtures in einer eigenen bestehenden Deploymentumgebung mit eigenen DBs/Volumes/Secrets halten. Kein neuer Beta-Schalter umgeht Produktionsgates.

## Durchführen

1. Ein echtes Portfolio, ein echtes Konto und 1–5 tatsächliche Instrumente wählen. Rechtmäßige Broker-/Kurs-/FX-Originale lokal bereitstellen; keine Zugangsdaten übermitteln.
2. Herkunft, Nutzungsrechte, Stichtage und Kennungen prüfen. Eigene Exporte über die dokumentierten UI-Vorschauen übernehmen; unbekannte Bestände/Einstandswerte ausdrücklich kennzeichnen.
3. Gebühren, Steuern, Dividenden und Splits mit dem Auszug prüfen. Tägliche FX und passende Preiszeitpunkte belegen; offene Coverage bleibt offen.
4. Stückzahlen und Cash exakt gegen den Auszug vergleichen, CHF-Wert samt Preis-/FX-Herkunft prüfen. Abweichungen dokumentieren; keine automatische Ledgeranpassung.
5. Ergebnis festhalten: REAL_PORTFOLIO_VERIFIED, REAL_PORTFOLIO_PARTIAL, SOURCE_APPROVAL_REQUIRED oder PORTFOLIO_RECONCILIATION_FAILED – mit konkretem Umfang und nächsten Schritten.

## Privates Restore-Szenario

Nach Freigabe Schreibpfade kontrolliert anhalten, vollständiges verschlüsseltes Backup auf unabhängigem Ziel erstellen, Hashes prüfen und eine isolierte Umgebung ohne öffentliche Ports/externe Collector aufbauen. Nur lokale private Prüfergebnisse vergleichen: Transaktionsversionen, Mengen, Cash, Raw-/Dokument-/Modellhashes, Bewertungs-/FX-Belege und notwendige Geheimnisse/CA-Recovery getrennt. Archivierte Modelle ausschließlich mit ihrem exakten, gegebenenfalls isolierten Legacyvertrag verifizieren. Ein späterer Preiskurs darf keinen gepinnten Restorebeleg ersetzen.

Nur eine privacy-sichere Zusammenfassung mit Datum, bestanden/offen und nicht identifizierenden Prüfumfängen veröffentlichen. Keine echten Originale, DB-Dumps, Screenshots oder Kontobeträge in GitHub Actions. Wiederherstellungscopy anschließend nach eigenem genehmigtem Retentionsverfahren behandeln; Originalbackup behalten. Diesen Plan erst nach tatsächlich ausgeführtem Restore als bestanden kennzeichnen.
