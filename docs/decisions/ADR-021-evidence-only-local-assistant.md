# ADR-021: Lokaler Assistent mit beleggebundener Ausgabe

Datum: 2026-10-15. Status: angenommen für P10.

## Entscheidung

Ollama ist ein optionaler privater Dienst. Chat und Embeddings haben unabhängige Providerverträge. Das Chatmodell liefert nur erlaubte Fakten-IDs und Erklärungsschlüssel. Serverseitig erzeugter Text enthält ausschließlich vorhandene Fakten und fest definierte Erklärungen. Quellenmaterial darf keine Tools oder privilegierten Aktionen auslösen.

RAG verlangt aktuelle Quellenrechte und eine dokumentbezogene unveränderliche Rechteprüfung. Bytegetreue Originale werden vor Parsing gespeichert. pgvector-Vektoren sind modellversioniert und ergänzend, niemals überschreibend. P10-Schema folgt mit Migration 0016 auf die getrennte P9-Abnahme und Migration 0015.

Alerts und Briefs funktionieren ohne LLM. Optimizer bleibt eine quantitative Simulation mit bestätigten harten Grenzen. Time Machine trennt tatsächliche Archive von Rekonstruktion und verweigert rückdatierte Prognosen.

## Folgen

Erklärungen sind enger und weniger frei formuliert als bei einem allgemeinen Chatbot. Dafür lassen sich Finanzwerte, Quellen, Modellversion und Freigabegrenzen überprüfbar zuordnen. Modell-, Embedding- oder MLflow-Ausfall darf Buchhaltung und strukturierte Ergebnisse nicht sperren. Erfolgreiche synthetische Prüfungen begründen keine reale Anlagevalidierung oder V3+-Produktionsfreigabe.
