# PR7 – tatsächliche Providerbelege

26.10.2026: **LIVE_TEST_BLOCKED_BY_SOURCE_APPROVAL** für ECB, SEC_EDGAR,
OPENFIGI, SNB, ALPHAVANTAGE, COMPANY_IR und NEWS_RSS. Yahoo bleibt BLOCKED.
Die read-only geprüfte lokale Registry enthält für diese externen Quellen
keine Aktivierung und keinen last_success. Keine externen Finanzdatenabrufe,
keine neue Freigabe, kein realer Collector-/Canonical-/UI-Erfolg behauptet.

Die [Primärdokumentationsprüfung](PR7_SOURCE_APPROVAL_MATRIX.md) ist kein
Liveabruf. Synthetische Tests der Adapter bleiben separat bezeichnet.
MANUAL_CSV hat ein bestehendes manual_upload-Gate; die aktuellen Tests
verwenden synthetische Originale und sind kein echter Brokerabgleich.

Nach tatsächlicher Operatorentscheidung ist je Quelle separat zu ergänzen:

| Nachweis | Aktueller Zustand |
| --- | --- |
| Versionierter Rechteentscheid und konkreter Scope | fehlt |
| Genau ein kleiner erlaubter Abruf, Status/Schema | nicht ausgeführt |
| Originalbytes, Hash und Provenienz vor Parsing | kein neuer Echtbeleg |
| Listing-/Serienidentität, MIC und Währung | nicht real geprüft |
| Canonical-Version, Qualitätsgates und tatsächliche UI | nicht real geprüft |
| Identischer Wiederholungsauftrag und Idempotenz | nicht real geprüft |
| Spätere separate Aktualisierung und Checkpoint | nicht real geprüft |
| Wiederkehrender Betrieb mit ausdrücklichem Opt-in | deaktiviert |

Bei 429/Timeout/Schemaänderung erfolgt die Fehlersimulation ausschließlich
offline. Ein Gate wird vor jedem tatsächlichen Retry erneut geprüft.
Keine absichtliche Überlastung realer Provider zur Abnahme.
