# PR7E – privater Portfolio-Pilot vorbereitet

27.10.2026. **PENDING_REAL_ORIGINALS_AND_SECURITY / TARGET_HOST_NOT_AVAILABLE**.

Technisch bestehen synthetische Migration/Recovery, tägliche Preis-/FX-
Importverträge, aktuelles frisches Goldenportfolio im HTTPS-Browser und der
vollständige isolierte Zielrestore mit 1381 Dateihashes. Das ersetzt keinen
realen Brokerabgleich, keine universelle ISIN-Versorgung und keine Hostfreigabe.

Der ursprüngliche Goldenbestand wird am belegten Cutoff26.10. mit CHF10’180
wiederhergestellt. Heute bleibt sein alter Kurs sichtbar veraltet, Gesamtwert
fehlt. Diese richtige Sperre ist zusätzlich im Restore verifiziert. Archivierte
Modelle, schlechte Prognosen, Transaktionskorrekturen, Dokumentrückzüge und
technische Wiederholungsbelege bleiben erhalten. Details im [Storagebericht](PR7B_STORAGE_READINESS_REPORT.md).

## Noch erforderliche echte Abnahme

1. Unveränderliches Image-/Configmanifest und verbleibende Securitybefunde
   einschließlich nativer Grenzen/CSP explizit prüfen. Kein ungeprüfter Critical.
2. Autorisierten Zielhost/VPN, Client-CA-Vertrauen, eigene Pilotcredentials,
   unabhängiges geschütztes Backup und Schlüsselwiederherstellung bereitstellen.
3. Eigenen echten Benutzer ohne synthetische QA-Portfolios verwenden. Zulässige
   Brokeroriginale erst nach diesen Gates lokal entgegennehmen; nicht in Git/CI.
4. Kontoauszug, Trades, Gebühren/Steuern, Positionen, Cash, Splits/Dividenden,
   Schlusskurse und tägliche FX am selben Stichtag abgleichen. Differenzen
   verursachungsgerecht dokumentieren; fehlende Werte bleiben fehlend.
5. Quellenoperator entscheidet einzelne Nutzungen mit bestehender Evidenz-
   Versionierung. Kleine echte Abrufe/Idempotenz und spätere Aktualisierung
   separat abnehmen. Automatische Collection bleibt bis dahin aus.
6. Unabhängigen [Anfängertest](ux/PR7_BEGINNER_TEST.md) durchführen und danach
   den tatsächlichen Zielhost-Backup-/Restore-/Recoveryablauf abnehmen.

Die bestehende Entscheidung „Zielhost fehlt; lokal vorbereiten“ bleibt gültig.
Reale Originale und Testperson liegen nicht vor. **Kein echter Pilot, keine
Produktion, kein Push/Release und keine Modell-/Strategiepromotion.**
