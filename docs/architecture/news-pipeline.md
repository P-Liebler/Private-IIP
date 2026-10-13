# News (P5)

Implementierte Inputs: explizit freigegebene RSS-2.0-Metadaten und validierter manueller JSON-Import. NEWS_RSS und MANUAL_RESEARCH starten UNKNOWN/deaktiviert. Ein Feed braucht `news`, `news_feed_archive` und einen genauen Host im Source-Scope. Das zusätzliche Archive-Recht deckt die unveränderte Feed-Response ab. Ein allgemeines News-Recht erlaubt keinen beliebigen vollständigen Artikeltext. Artikel werden nicht nachgeladen, Paywalls nicht umgangen. Kurze manuelle Excerpts werden nur mit `news_excerpts` gespeichert.

Pipeline: Rechtegate → Hostprüfung → verteilter Rate-Limiter → Request → Originalbytes/Hash/HTTP-Metadaten → RSS-Parser → Deduplizierung → Zuordnung → News-DB. Der Parser verweigert DTD/Entities. Keine universelle HTML-Interpretation; RSS-Namespaces/Atom benötigen einen eigenen geprüften Vertrag. GDELT ist kein zusätzlicher aktivierter oder behaupteter Provider.

Duplikate: normalisierte URL (Trackingparameter/Fragment entfernt), Hash der normalisierten zulässigen Headline-Metadaten, ähnliche normalisierte Titel (≥0,92, ausreichende Titellänge). Quellenbeobachtungen bleiben erhalten, mit `duplicate_of_id`; sie werden nicht als unabhängige neue Meldung ausgegeben. Kleine Suchfenster für Ähnlichkeit begrenzen Aufwand; globale URL-/Hash-Treffer bleiben möglich.

Zuordnung verwendet ausdrücklich gelieferte Identifier gegen die lokale Instrumenthistorie. Eindeutige aktuelle Identifier können CONFIRMED sein, mehrdeutige Ticker und reine Namensmatches bleiben CANDIDATE. Zufällige Tickerwörter im Artikel werden nicht automatisch übernommen. Verknüpfungen speichern Relevance, Confidence und Mapping-Status. Historische Instrument-API liest nur CONFIRMED.

`published_at`, `discovered_at`, `retrieved_at` bleiben getrennt. Historische Sicht verlangt Veröffentlichung und eigene Entdeckung ≤ `as_of`. Eine alte Meldung, heute erstmals importiert, wird nicht rückwirkend als damaliger eigener Archivstand ausgegeben. Sentiment-Abstraktion ist lokal und optional: ohne installiertes Modell oder unterstützte Sprache null/unavailable, keine erfundenen Wahrscheinlichkeiten. Volltext, Embeddings und ML-News-Features sind keine P5-Pflichtdienste.
