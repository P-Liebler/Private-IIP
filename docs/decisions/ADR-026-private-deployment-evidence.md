# ADR-026 – Getrennte technische und betriebliche Abnahme

19.10.2026 · angenommen für lokale PR3-Vorbereitung.

Preflight und Deploymentwrapper verwenden den bestehenden Compose-/Settings-/Backup-/Alembic-Vertrag. Es entstehen weder eine zweite Produktarchitektur noch neue Finanz- oder Schemafreigaben. Staging und Produktion verwenden eigene Projekte/Volumes/Secrets; beide erhalten sichere Settings. Operatorzugriff auf Statusinformationen ist eine eigene explizite Allowlist ohne Daten-/ML-Rechte.

Konfigurationsprüfung, lokale Tests, lokale Stagingtests, wirklicher Zielhost und Operatorannahme sind getrennte Evidenzstufen. Ein erreichbarer Ordner beweist keine unabhängige Sicherung, ein TLS-Handshake keinen Windows-/Android-Trust, eine Alert-Regel keine Zustellung. Die Statusseite darf diese Bedingungen nicht per Checkbox schließen. Belege werden mit UTC-Zeit, Version und reproduzierbaren Prüfschritten im Operatorprotokoll geführt.

Backup/Restore/Retention teilen einen Betriebssystem-Lock am ausgewählten Root; Integritätsfehler werden vor Restoreausführung protokolliert. Modell-/Rohdaten-/History-Hashes bleiben unverändert streng. TOTP-/CA-Secrets gehören ausschließlich in getrennte verschlüsselte Sicherungen. Ein synthetischer Key-Drill ist keine Freigabe echter Secret-Recovery.

Neue Security-Scans haben trotz funktionierender lokaler Tests High-/Critical-Imagebefunde geliefert. Sie bleiben offen; Caddy wurde auf einen überprüften neueren Digest gebracht, ohne sämtliche Befunde als behoben auszugeben. Numerische Runtime-Pins und alte Artefakte werden nicht heimlich migriert. Ohne sichere Images und reale Host-/Client-/Backup-/Alarmnachweise bleibt PRIVATE_CORE_DEPLOYMENT_NOT_VERIFIED. Reale Daten, Forecasts und Empfehlungen besitzen unabhängig davon ihre bestehenden Gates.
