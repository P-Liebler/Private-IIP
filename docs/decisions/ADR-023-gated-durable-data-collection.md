# ADR-023: Rechtegeprüfte dauerhafte Datenversorgung

Datum: 2026-10-16. Status: angenommen für PR1.

## Entscheidung

Die vorhandenen P3/P5/P6-Writer bleiben kanonisch. Provider liefern exakte Originalbytes; `providers/http.py` erzwingt vor DNS und jedem Retry das Source-Gate und gemeinsame Valkey-Limits. HTTPS-Hosts sind fest oder durch einen expliziten IR/RSS-Vertrag gebunden. Der Netzwerkbackend löst DNS auf, prüft sämtliche Antworten auf öffentliche IPs und verbindet die ausgewählte numerische Adresse; TLS verwendet weiterhin den ursprünglichen Host. Keine Proxy-Umgebungsvariablen oder Redirects. Maximal 16 MiB, feste Timeouts und drei Versuche, Retry-After mit numerischen/HTTP-Datumswerten, längere Sperren als strukturierter Fehler. HTTP-/Provider-Logs enthalten keine URLs mit persönlichen Schlüsseln.

Rohdaten werden vor Typ-/Schema-/Kanonikprüfung gespeichert, einschließlich fehlerhafter begrenzter HTTP-Antworten. Übergrösse oder abgebrochene Übertragung werden als unvollständiger Fehler protokolliert, niemals als vollständiges Original gehasht. Nur erlaubte Metadaten und Cache-Validatoren archivieren. 204/304 erzeugen keine Finanzwerte. Parser und angeforderte Bereiche bleiben nachweisbar.

PostgreSQL besitzt Collector-Jobs und Fortschritt. Celery/Scheduler wecken die gemeinsame Service-Schicht. Begrenzte Fenster, höchstens 30 Instrumente/fünf Jahre/vier offene Jobs, globale Exklusivlocks und per-Schritt-Checkpoints begrenzen Ressourcen. Nach einem Crash kann ein RUNNING-Auftrag nach Freigabe der Prozesssperre wiederaufgenommen werden. Raw-/Canonical-Commits kommen vor dem Checkpoint; Wiederholung ist idempotent. Fehler werden nicht endlos neu gestartet. Cancel wirkt an der nächsten Abschnittsgrenze; schon gespeicherte Daten bleiben erhalten.

Rechteentscheidung und Aktivierung sind getrennt; Review-Datensätze sind unveränderlich. Der API-/UI-Operator kommt aus der bestehenden Daten-Operator-Allowlist. Reguläre Nutzer erhalten keine neuen Schreibrechte. Allgemeine Zeitpläne sind standardmässig aus. Kein Provider erhält durch Implementierung, Tests oder Dokumentation eine Freigabe.

## Folgen

Keine neue Pflichtbibliothek und kein neuer kostenpflichtiger Dienst. Core-/Assistant-Locks und P7-Artefaktprüfung bleiben bestehen. `provider_sync_states` speichert ETag/Last-Modified erst nach erfolgreicher Verarbeitung. Die unterstützten SNB-Verträge sind monatlich; sie ersetzen keine täglichen Bewertungskurse. Alpha Vantage ist optional und kompakt, FRED/ALFRED bleibt ohne eigenen freigegebenen Collector optional. Grenzen und Quellenrechte: [Matrix](../data/SOURCE_RIGHTS_MATRIX.md).
