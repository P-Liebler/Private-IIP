# Private Dokumente und RAG

Prüfstand: 2026-10-15. PostgreSQL/pgvector speichert Metadaten, Chunks und versionierte Vektoren; MinIO speichert die unveränderten PDF-Originale.

## Rechte vor Verarbeitung

Die neuen Quellen `MANUAL_DOCUMENTS` und `MANUAL_EVENTS` beginnen UNKNOWN/deaktiviert. Es gibt keine automatische Freigabe. Ein Datenoperator muss ausdrücklich über `DATA_OPERATOR_USERNAMES` benannt werden. Quellenrechte gelten je Verwendung: `RAG_METADATA`, `RAG_STORAGE`, `RAG_INDEX`, `CALENDAR_EVENTS`. Freigabe allein aktiviert keine Quelle.

Für PDF-Speicherung wird eine private, unveränderliche Prüfung von Dokument-SHA-256, Quelle, Speichern/Indexieren, dauerhafter Aufbewahrung, Attribution und Nachweis benötigt. Ohne belegte Inhaltsrechte ist nur die gesondert freigegebene Metadatenablage möglich. Temporär erlaubte Inhalte mit notwendiger Ablauf-Löschung werden derzeit nicht angenommen; dies würde einen gesonderten Löschvertrag für Original, Ableitungen und Backups benötigen.

## Pipeline

1. Metadaten an authentifizierten Upload-Endpunkt; kurzlebiges einmaliges Upload-Ticket im Valkey, an Nutzer gebunden.
2. Höchstens 5 MB exakte Bytes; SHA und Rechte prüfen.
3. Original unveränderlich speichern, Provenienz committen, Original erneut mit Hash laden.
4. Festes Parser-Unterprogramm: pypdf 6.20.1, 50 Seiten, 384 MiB Adressraum / 10 CPU-Sekunden, 15 Sekunden Prozessbudget, 100.000 Textzeichen. Verschlüsselte, bildbasierte oder übergroße PDFs liefern einen expliziten Extraktionsstatus. Keine OCR.
5. Text-Chunks 600 Zeichen, 80 Überlappung, höchstens 200. Seiten- und Chunknummer, Text-SHA und Pipelineversion bleiben erhalten.
6. Lokale Embeddings in Batches bis acht, Gesamtbudget bei Erstimport 60 Sekunden. Fehler lassen Original und extrahierten Text verfügbar. Reindex ergänzt fehlende Versionen und überschreibt alte Vektoren nicht.

Tabellenextraktion begründet keine kanonischen Finanzwerte. Dokumentinhalt bleibt nicht vertrauenswürdiges Quellenmaterial und kann keine Tools wählen oder Befehle auslösen.

## Retrieval und Quellen

Filter: Besitzer, Instrument, Dokumenttyp, Quelle, Publikationsintervall, tatsächlicher Wissensstand. Dokument, Chunk und Embedding müssen bereits vor dem Cutoff existiert haben; Publikation allein reicht nicht. Aktuelle Indexierungsrechte werden erneut geprüft. Kein Modellwechsel-Fallback auf unpassende Vektoren. Abfrage auf höchstens 1000 private Dokumente / acht Treffer begrenzt, HNSW-Kosinusindex.

Vor Zitatausgabe Original- und Chunk-Hash prüfen. Zitate enthalten echte interne Dokument-/Chunk-ID, Titel, Quelle, Publikation, erste Beobachtung, Seite, Hash, Attribution und geschützten Original-Downloadlink. Fehlende Originale oder Versionen erzeugen keine erfundene Quelle. Originaldownloads sind als Attachment markiert und erneut besitz-/rechtegeprüft.

Backup enthält Originale und exakte Vektoren. Ohne Modellgewichte ist nach Restore Quellenanzeige möglich; semantische Suche benötigt dasselbe Embeddingmodell oder einen ausdrücklich neuen Index. Der Restore-Checkpoint prüft Vektorinhalte unabhängig von Ollama.

Primärdokumentation, geprüft 2026-10-15: [pgvector Python/SQLAlchemy](https://github.com/pgvector/pgvector-python), [pypdf Textextraktion und Grenzen](https://pypdf.readthedocs.io/en/stable/user/extract-text.html), [Ollama Embed](https://docs.ollama.com/api/embed).
