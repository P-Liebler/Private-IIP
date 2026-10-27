# PR7C – reale Datenversorgung, Zwischenstand

Fortsetzung27.10.:29/29 lokale Browserfälle bestehen; der abschließende Abschnitt
beschreibt die geprüften manuellen Änderungen. Reale Provider bleiben gesperrt.

26.10.2026: **LIVE_PROVIDER_STATUS: BLOCKED_BY_SOURCE_APPROVAL**.
**AUTOMATIC_REFRESH_STATUS: DISABLED**.

Die aktuelle lokale Registry wurde read-only geprüft. Kein externer Provider
ist freigegeben und aktiviert; die Recherche hat keine Operatorentscheidung
erzeugt. [Quellenmatrix](data/PR7_SOURCE_APPROVAL_MATRIX.md) enthält aktuelle
Primärbelege, Quotengrenzen, Markt-/Datentypgrenzen und konkrete offene
Rechtepunkte für ECB, SEC, OpenFIGI, SNB, Alpha Vantage und individuelle
IR-/RSS-Verträge. [Live-Nachweise](data/PR7_LIVE_PROVIDER_EVIDENCE.md) bleiben
getrennt von Dokumentations- und synthetischen Adapterprüfungen.

Allgemeine unterschiedliche ISINs sind weiterhin Zielumfang. Daraus folgt
keine bestätigte Abdeckung jeder Börse/Währung, keine kostenlose globale
Kurshistorie und keine geprüfte Corporate-Action-Vollständigkeit. Ein Listing
benötigt zusätzlich MIC/Handelswährung; Monats-SNB ist kein täglicher FX-Ersatz.

Der vorhandene manuelle Raw-first-/Preview-/Commit-Weg bleibt nutzbar und
wird in den laufenden Browserregressionen mit ausdrücklich synthetischen
Originalen geprüft. Echte Brokeroriginale liegen nicht vor. Es wurde weder
ein realer Pilot noch eine automatische Versorgung als erfolgreich erklärt.

Noch offen: vollständiger PR7-Collector-Vertragsabgleich einschließlich
Abbruch/Pagination/Backfill/Kalender/Delisting, abschließende manuelle Mehrinstrument-/Fehlerraumabnahme
und nach tatsächlicher Operatorfreigabe die kleinen echten Live-Abnahmen
einschließlich späterer separater Aktualisierung. Die Quellenmatrix allein
schließt PR7C nicht ab.

Die Quellenoberfläche ist ergänzt: Eignung/Marktgrenzen, API-Key, Limits,
Datum der Dokumentationsprüfung getrennt von tatsächlichem Operatorreview,
konkrete offene Rechtepunkte und tatsächlicher Import-/Abrufstatus. Bei
Ladefehlern werden zwischengespeicherte Freigabezeilen ausgeblendet; Aktualisieren
und Retry sind im vollständigen27-Fall-Browserlauf bestanden. Drei neue
Backendtests prüfen außerdem, dass ein laufender Providerretry keinen inzwischen
geänderten Review/Scope übernimmt, selbst wenn die Quelle erneut aktiviert ist.
Die erste Antwort bleibt archiviert; vor dem zweiten Netzwerkversuch wird
abgebrochen. Keine tatsächliche Quelle wurde dafür aufgerufen oder freigegeben.

## Technische Fortsetzung27.10.

Der gemeinsame29/29-Browserlauf bestätigt CSV-Dateiabgabe, überprüfbare
Standard-Headererkennung und zwei Instrumente mit unterschiedlichen FIGIs/MICs
und Handelswährungen in derselben echten Preview-/Commit-Datei. Anschließende
tägliche USD/CHF-FX stammt ausschließlich aus der als SYNTHETIC gekennzeichneten
Testdatei. Keine aktuelle Marktquote und kein realer Providererfolg wird daraus
abgeleitet. Alte Vorschau wird bei neuer Auswahl verworfen, aktive Übernahme
blockiert Auswahlwechsel; erfolgreiche Übernahme aktualisiert aktive Ansichten.
Quarantäne, Konfliktentscheid und Dubletten bleiben Verträge der bisherigen Engine.
Source-UI-Retry und unveränderlicher Review pro Providerattempt sind geprüft.
Reale Originale und individuelle Quellenfreigaben fehlen weiterhin.
