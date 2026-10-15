# Strukturierter Daily Brief

Der Bericht benötigt kein LLM. Gespeicherte Fakten aus P4/P5/P7/P8/P9 sowie freigegebene archivierte News, Makrobeobachtungen und Termine werden mit Quellen und Datenlücken zusammengeführt. Keine neu erfundenen Marktbewegungen, Empfehlungen oder Earnings-Termine.

Portfolio-Performance erscheint nur bei vollständiger validierter P8-Renditekette, passendem Bewertungsstand und belegten Session-Schlusszeiten im tatsächlichen Berichtsfenster. Ohne Nachweis bleibt die Performance `null`/UNAVAILABLE. Ohne Vorbericht gibt es keine behauptete Veränderung. Eine Änderung wird nur zwischen zwei vorhandenen verfügbaren Fakten desselben sachlichen Geltungsbereichs ausgewiesen; Rohbelege bleiben im Bericht.

Konfiguration je Nutzer: an/aus, lokale Uhrzeit, IANA-Zeitzone. Speicherung UTC. Einzigartiger Schlüssel Nutzer/lokales Berichtsdatum und Datenbanksperre machen manuelle Erstellung, Scheduler und Wiederanlauf idempotent. Fehlende Frühlingsstunde wird vorwärts normalisiert, doppelte Herbststunde verwendet den ersten Fold. Der Scheduler erstellt höchstens den jüngsten fälligen Bericht, keine unbegrenzte Nachlieferung. Tatsächliches Erstellungsende und nomineller Termin werden getrennt gespeichert; verspätet beobachtete Daten werden nicht als pünktlich bekannte Daten ausgegeben. Rückblick maximal 48 Stunden, höchstens zehn Portfolios / zehn Positionen pro Portfolio.

Bericht und Contenthash bleiben unveränderlich; eine private Notification verweist darauf. Optionales „lokal erklären“ verwendet dieselben Fakten-IDs und denselben Antwortvertrag wie der Chat. Modellfehler ändern den strukturierten Bericht nicht. Automatik ist standardmäßig ausgeschaltet.
