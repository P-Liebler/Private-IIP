# Lokaler Assistent (P10)

Prüfstand: 2026-10-15. P9-Abnahme geht P10 voraus. Der Assistent erklärt gespeicherte quantitative Ergebnisse; er autorisiert keine Empfehlung und besitzt keinen Ledger-Schreibzugriff.

## Laufzeit

Optionales Compose-Profil `llm`: Ollama 0.40.4 mit Image-Digest, privates Netz, kein Host-Port, kein Cloudbetrieb, maximal ein geladenes Modell und eine Anfrage, 2 CPUs / 3 GiB RAM. Modellvolumen `ollama_data`. Die Kernplattform benötigt Ollama nicht für Readiness, Portfolio, Research, Risiko, Recommendations oder strukturierte Briefs.

```powershell
docker compose --profile llm up -d ollama
docker compose exec -T ollama ollama pull qwen3:0.6b
docker compose exec -T ollama ollama pull embeddinggemma:300m
```

Downloads sind explizite Operatoraktionen. CI lädt keine Gewichte. Chatmodell rund 523 MB; Embeddingmodell rund 622 MB; zusätzlicher RAM und Betriebskosten sind unabhängig von verpflichtenden API-Gebühren.

Verifizierte lokale Versionen: `qwen3:0.6b@7df6b6e09427a769808717c0a93cadc4ae99ed4eb8bf5ca557c90846becea435`, `embeddinggemma:300m@85462619ee721b466c5927d109d4cb765861907d5417b9109caebc4e614679f1`. Embeddings haben 768 Dimensionen. Laufzeitversion und vollständiger Modell-Digest stehen in jedem gespeicherten Modellnachweis. Tags sind kein dauerhaft unveränderlicher Name; nach Modellwechsel werden neue Embedding-Versionen angehängt.

`LLMProvider` und `EmbeddingProvider` trennen Orchestrierung und konkrete lokale Laufzeit. Nur feste API-Pfade und lokale Allowlist-Adressen; keine Nutzer-URLs, Weiterleitungen oder Proxy-Umgebung. Modellnamen mit Cloud-Hinweisen werden abgewiesen. Kontext 4096 / Antwort 384 Tokens, Requesttimeout 60 Sekunden, Antwortbytes maximal 2 MB. Anpassungen sind begrenzt.

## Datenfluss

Authentifizierung → Besitzprüfung → Rate-/Ressourcengrenze → bis vier typisierte Read-only-Tools → optionales privates Retrieval → JSON-Schema für Auswahl belegter Fakten → serverseitige Validierung → feste Erklärungen und exakte Fakten → unveränderliche Nachricht → SSE.

Das Modell liefert weder freie Finanzzahlen noch frei erfundene Quellen. Es wählt Fakten-IDs und erlaubte Erklärungsschlüssel. Vollständige Textvalidierung erfolgt vor dem ersten Textfragment. Dadurch ist der Chat bewusst enger als ein frei formulierender Finanzchat. Bei Laufzeitfehlern bleiben strukturierte Fakten mit Ausfallhinweis verfügbar. Abbruch beendet die Anfrage; ein Abbruchvermerk wird soweit möglich gespeichert.

Private Unterhaltungen können gelöscht werden; Löschung kaskadiert Nachrichten und Tool-Aufrufe. Der stündliche Retentionjob löscht Unterhaltungen nach ihrer Erstellungszeit, standardmäßig nach 30 Tagen. Löschung betrifft die aktive Datenbank; bestehende Backups folgen ihrer eigenen Aufbewahrung.

Primärdokumentation, geprüft 2026-10-15: [Chat API](https://docs.ollama.com/api/chat), [Embed API](https://docs.ollama.com/api/embed), [strukturierte Ausgaben](https://docs.ollama.com/capabilities/structured-outputs), [Docker](https://docs.ollama.com/docker), [Qwen3](https://ollama.com/library/qwen3:0.6b), [EmbeddingGemma](https://ollama.com/library/embeddinggemma).


Numerische Modell-Pins bleiben im unver?nderten Core-Lockfile. Dokument-/Vektor-Pakete werden aus `requirements-assistant.lock` mit `--no-deps` nachinstalliert und separat im Codemanifest erfasst. Alle Backendimages verwenden beide Schichten und `pip check`; die strikte Pr?fung alter Modelle bleibt bestehen. Siehe [ADR-022](../decisions/ADR-022-preserve-model-dependency-pins.md).
