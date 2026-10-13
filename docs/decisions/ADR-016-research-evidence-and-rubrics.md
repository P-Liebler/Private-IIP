# ADR-016: P5 evidence, restatements and deterministic research

Status: Accepted, 2026-10-13.

Fundamental- und Estimate-Versionen sind append-only und verweisen auf unveränderte Raw-Bytes. Öffentliche Verfügbarkeit und eigene erste Beobachtung bleiben getrennt. P5-Historie verlangt beide Zeitpunkte ≤ Stichtag; ein aktuelles Companyfacts-JSON rekonstruiert keine frühere lokale Archivversion. Restatements erhalten explizite Ersetzungsbezüge. Neue externe und manuelle Research-Quellen starten UNKNOWN/deaktiviert; bestehende Nutzungsrechte werden nicht erweitert.

Feste absolute Research-Rubriken mit vollständiger Pflicht-Coverage bilden die erste Score-Version. Keine heimlichen privaten Marktperzentile oder ML-Entscheidungen. Fehlende Pflichtdaten setzen Scores aus. Snapshot-Lesemodelle und indizierte numerische Kennzahlen erlauben DB-seitige Screenerfilter ohne Neubearbeitung von Raw-Daten pro Seitenaufruf. Firmenweite Aktienzahlen benötigen eine ausdrückliche Aktiengattungs-/Split-Prüfung vor Market Cap und Bewertung.

News-Duplikate erhalten Quellenbeobachtungen statt sie zu löschen. Optionales Sentiment fällt ohne lokales Modell auf unavailable zurück. Die P4-Zielinstallations-, Backup-, VPN- und Schlüssel-Recovery-Gates bleiben unabhängig offen. P6 wird nicht begonnen.
