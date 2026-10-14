# Market Calendars

P6, 2026-10-13. Offline `exchange-calendars==4.13.2`, inklusive transitive Versionslocks. Unterstützt NYSE/XNYS, NASDAQ/XNAS (Bibliotheksalias XNYS), SIX/XSWX. NASDAQ teilt hier den dokumentierten US-Aktienkalender; das ist keine eigene unabhängig gepflegte NASDAQ-Ausnahmeliste. Alle Öffnungs-/Schlusszeitpunkte werden UTC ausgegeben.

Die Bibliothek liefert Sessions, Wochenenden, Feiertage, frühe Schlüsse, historische bekannte Sonderausfälle und lokale DST-Regeln. Kein selbst erfundener Feiertagskalender. Unterstützter Bereich 1990–2035; unbekannte Börse oder Bereich außerhalb des Kalenders ist unavailable. Unerwartete künftige Schließungen können nicht behauptet werden. Eine neue Bibliotheks-/Regelversion erzeugt neue Dataset-Identitäten.

`MarketCalendarService`: is_session, next_session/previous_session (streng nach/vor Datum), sessions_between (inklusive), session_open, session_close, horizon. 30/90 bedeutet ausschließlich Sessions des Instruments. Referenztests: US Independence Day, Thanksgiving Early Close, US DST im März, Hurricane-Sandy-Schließung 2012, Schweizer Sessions und 30-/90-Session-Horizonte.

Primärdokumentation geprüft 2026-10-13: [Repository](https://github.com/gerrymanoim/exchange_calendars), [Calendar aliases](https://github.com/gerrymanoim/exchange_calendars/blob/master/exchange_calendars/calendar_utils.py), [Distribution](https://pypi.org/project/exchange-calendars/4.13.2/). Kein Finanzprovider und keine neue Quellenfreigabe.
