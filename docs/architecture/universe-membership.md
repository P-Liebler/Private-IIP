# Universe Membership

P6, 2026-10-13. Jedes Universe gehört einem Nutzer; US_LARGE_CAP, CH_LARGE_CAP, USER_WATCHLIST und CUSTOM_UNIVERSE sind definierte Typen, keine vorinstallierten echten Indexhistorien.

Membership-Versionen unterscheiden `valid_from`/`valid_to` (beide inklusive), `known_at` und `observed_at`. Status LISTED, DELISTED oder REMOVED. Korrekturen desselben Instruments und Eintrittsdatums ersetzen fachlich eine frühere Version, erhalten sie aber physisch. Ein neuer Eintritt hat ein neues `valid_from`. Überlappende gültige Intervalle sind mehrdeutig und werden ausgeschlossen. Heutiges `active` wird nicht als historische Auswahl benutzt.

CSV: `instrument_id,valid_from,valid_to,known_at,membership_status`. Interne UUIDs sind das explizite Mapping; kein automatisches Ticker-Mapping. Upload archiviert exakte Bytes; Vorschau prüft Schema, IDs, Reihenfolge und doppelte Intervalle. Commit ist atomar und idempotent pro Raw-/Intervallidentität. Entfernen/Korrigieren erfolgt durch neue CSV-Versionen. Source MANUAL_PIT startet UNKNOWN/deaktiviert; erforderlich ist gesonderte Freigabe `universe_membership`. Bestehende MANUAL_CSV-Rechte werden nicht erweitert.

Eine erst heute importierte 2015-Membership gilt im strengen Modus nicht als damals bekannt. Zusätzlich muss ein Universe-Review die Vollständigkeit einschließlich delisteter Titel für den jeweiligen Zeitraum belegen (`valid_from`, `valid_to`, `includes_delisted`). Ohne diese Evidenz entsteht SURVIVORSHIP_BIAS_RISK oder strenger Ausschluss. Ein lokales Watchlist-Universe impliziert keine vollständige historische Indexmitgliedschaft.

Operator-Reviews: `python -m scripts.review_pit_evidence <review.json>`. Der Review speichert Reviewer, Original-Raw, Methode und Zeit. Kein Browser-Button macht eine Behauptung automatisch zum verifizierten Nachweis.
