# PR6F – Funktionsprüfung und fachliche Grenzen

Stand 23.10.2026: **PARTIAL**. Das statische [Routen-/API-Inventar](ux/ROUTE_API_INVENTORY.json) ist eine Prüfhilfe, kein Funktionsnachweis aller sichtbaren Aktionen.

## Bisher behobene konkrete Fehler

- Allokationsanzeige vergleicht den tatsächlichen Status `AVAILABLE`.
- Nachrichtenfilter setzen den Seitenoffset zurück, damit ältere Filterseiten keine falsche Leermeldung erzeugen.
- Watchlists verwenden Instrumentensuche statt einer nötigen UUID-Eingabe. Mutationen haben einen gemeinsamen Pending-/Fehlerzustand. Fehlgeschlagene Archivierung verwirft die ausgewählte Liste nicht.
- Private Querycaches sind an die authentifizierte Identität gebunden; Buchungen/Marktdatenimporte invalidieren relevante Ansichten. Betreiberrechte sind keine Annahme aus einer anderen Rolle.
- Analysestartseite führt zu tatsächlichen Portfolio-Risiko-/Szenario-/What-if-Bereichen. Abgesicherte Tabparameter erhalten Deep-Links.
- Ergebnisansichten zeigen strukturierte Daten und Zustände; vollständiges Original-JSON bleibt aufklappbar.
- Ältere Datasetarchive mit nur teilweise gespeicherter Qualität verursachen keinen `Object.entries(undefined)`-Abbruch mehr. Nicht archivierte Kennzahlen/Ausschlussgründe werden ausdrücklich so benannt; alte Datasetinhalte/Hashes bleiben unverändert.

## Mutationen und lokaler Assistent

`0021_ui_requests` speichert Portfolio-/Kontoressource und technischen Wiederholungsbeleg atomar. Ledgerbuchungen erhalten ihren bestehenden Auditpfad und einen stabilen UI-Anfrageschlüssel. Ein Konflikt ergibt 409, eine Wiederholung einer stornierten Originalbuchung keine neue Buchung. CSV-Planhashes behalten ihren alten Vertrag ohne Formatparameter und binden explizite Formate im neuen Parservertrag.

Echte lokale Ollama-Auswahl und Embeddings sind mit Versions-/Digestbindung geprüft. Orchestrierung mit drei bestehenden Read-only-Tools, gespeicherter Antwort und erhaltener Forecastsperre bestand bei 120 s Timeout in 101.562 s; der vorherige 60-s-Lauf erreichte das Limit und bleibt als Einschränkung dokumentiert. Die ignorierte lokale `.env` ist auf den bereits unterstützten Wert 120 s eingestellt; andere lokale Einstellungen blieben erhalten, die allgemeine Standard-/Produktionskonfiguration wurde nicht heraufgesetzt.

Retrieval eines bereits freigegebenen synthetischen Originaldokuments mit echter embeddinggemma-Version, identischen Originalbytes und geprüftem Zitat-Hash bestand. Vorhandene Embeddings wurden wiederverwendet; `new_embeddings=0` ist keine neue Indexierung. Beim gestoppten Ollama speichert die Orchestrierung die explizite `LLM_UNAVAILABLE`-Ersatzantwort mit drei Toolbelegen und unveränderter Forecastsperre. Ollama wurde danach wieder gestartet. Diese Nachweise sind lokale Funktionstests, keine Finanzvalidierung oder reale Fremddokumentfreigabe.

## Dokumente

Migration `0020_document_removals` ergänzt ausschließlich eine append-only Entfernungsentscheidung. Eigentümer können ein Dokument idempotent aus aktiver Bibliothek, Retrieval und historischer Suchwiederholung zurückziehen. Fremde Dokumente bleiben 404, Original-/Reindexzugriff auf entfernte Dokumente ist gesperrt. Originale, Chunks, Embeddings und alte Belege bleiben unverändert; der Bestätigungsdialog benennt diese Aufbewahrung.

Ein isolierter Integrationstest bestätigt Rechteprüfung am selbst erstellten synthetischen PDF, Retrieval vor Entfernung, fremden Zugriff, wiederholte Entfernung, Ausschluss bei altem Stichtag, Originalbytes, erhaltene Chunks/Embeddings und DB-Abweisung einer Änderung oder Löschung des Entfernungsentscheids. Der alte Intelligence-Hash bleibt identisch; ein separater Entfernungshash ergänzt neue Restore-Nachweise. Lokale Schemaaktualisierung und `alembic check` bestanden, vorab lokaler Datenbankdump erstellt. Keine produktive Migration.

## Weiterarbeit

297 Backendtests, 35 Hosttests, 26 unterschiedliche Browserfälle und isolierter Restore mit 502 Raw-Objekten/503 Dateihashes sind bestanden; Ausführungen/Datierungen stehen im [Gesamtbericht](PR6_ACCEPTANCE_REPORT.md). Der normale lokale Modus mit zurückgesetzten Testrollen wurde am 26.10. geprüft. Lokale synthetische Tests ersetzen weder echte Depotabnahme noch Quellenrechte, LLM-Dauerbetrieb, Modell-/Strategiefreigaben oder Zielhostabnahme. Die kuratierte [Funktionsmatrix](ux/FUNCTIONAL_MATRIX.md) ergänzt das statische Inventar mit Nachweisen und Grenzen; nicht jede mögliche Fehlerantwort ist auf jeder einzelnen Seite browserseitig injiziert worden.
