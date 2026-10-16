# Provider-Inventar

Stand 2026-10-16. Status der realen Registry ist getrennt von synthetischen TEST_-Quellen zu lesen.

| Quelle | IMPLEMENTED | OFFLINE_TESTED | LIVE_TESTED (Produktpfad) | OPERATOR_APPROVED | ENABLED | SCHEDULED |
| --- | --- | --- | --- | --- | --- | --- |
| SEC_EDGAR | Ja, Submissions/Company Facts/Primary Filing | Ja | Nein | Nein | Nein | Nein |
| ECB | Ja, EXR tägliche EUR/CHF+USD | Ja | Nein | Nein | Nein | Nein |
| SNB | Ja, geprüfte monatliche Policy-/Referenz-FX-Verträge | Ja | Nein | Nein | Nein | Nein |
| OPENFIGI | Ja, Filter/unlisted, explizite Kandidatenannahme | Ja | Nein | Nein | Nein | Nein |
| COMPANY_IR | Ja, explizites CSV + manuelle PDF-Prüfung | Ja | Nein | Nein | Nein | Nein |
| ALPHAVANTAGE | Optionaler kompakter Raw-OHLCV-Adapter | Ja | Nein | Nein | Nein | Nein |
| NEWS_RSS | Ja, RSS 2.0 unter beiden Nutzungsgates | Ja | Nein | Nein | Nein | Nein |
| MANUAL_CSV | Ja, Vorschau/Commit/Quarantäne | Ja | Nicht anwendbar | Bestehender Upload-Scope | Ja | Kein automatischer externer Abruf |
| FRED/ALFRED | Optionaler Schlüssel konfigurierbar; kein Netzwerkcollector | Nein für neuen Collector | Nein | Keine Freigabe | Nein | Nein |
| Yahoo / Stooq / SIX | Kein aktiver Kurscollector | Gate-Prüfungen | Nein | Nein | Nein | Nein |

Die SNB-Schema-Verifikation nutzte das offizielle R-Dokumentationsskript und zwei kleine öffentliche Vertragsreferenzen (`snboffzisa` Januar 2024, `devkum` Januar 2024). Sie wurden nicht in die Plattform importiert, nicht als Produktions-Smoke abgenommen und begründen keine Quellenaktivierung. Dokumentierte Struktur: CubeId/PublishingDate, Leerzeile, semikolongetrennte Header Date/D0[/D1]/Value. Tests verwenden ausdrücklich synthetische Werte dieses Schemas.

Sämtliche produktiven externen Collector-Aufträge benötigen weiterhin Registry-Gate, erlaubte Nutzung, aktuelle Review, globalen Limiter und gegebenenfalls persönliche Konfiguration. Keine Quelle wurde durch die Dokumentationsprüfung freigegeben. Unterstützende Pakete wurden nicht ergänzt; numerische und Assistant-Lockfiles bleiben unverändert.
