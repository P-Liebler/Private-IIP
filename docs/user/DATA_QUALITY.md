# Datenqualität und nächste Schritte

Jede Position zeigt Kursdatum/-alter, Schlusskurswährung, Quelle, lokale Erfassung sowie FX-Referenz, Alter und Herkunft. Die Berechnungszeit des Portfolios ist kein neuer Börsenkurs. Bekannte Teilwerte sind keine vollständige Summe.

| Zustand / Problem | Aktion |
|---|---|
| CURRENT im bestehenden Bewertungsvertrag | Innerhalb der P4-Altersgrenze; trotzdem Tages-Schlusskurs, kein Livepreis |
| DELAYED | Verfügbarer Schlusskurs mit sichtbarem Datum; keine Echtzeitbehauptung |
| STALE / STALE_PRICE | Zu alten Kurs durch rechtmäßiges aktuelles Original ergänzen |
| MISSING / MISSING_PRICE | Kurs für das richtige Instrument importieren |
| INVALID / MISSING_EVENT_PRICE | Validierung, Konflikt oder Kurseinheit nach Split/Dividende prüfen |
| MISSING_FX / MISSING_EVENT_FX | Geeignete aktuelle bzw. damalige tägliche FX-Referenz importieren |
| SOURCE_BLOCKED | Abrufrecht/Scope prüfen; nur ein Operator darf nach belegtem Entscheid aktivieren. Zulässiger manueller Import bleibt möglich |
| HISTORICAL_ONLY | Explizit historische Bewertung, keine Behauptung eines aktuellen Kurses |
| UNVERIFIED_CORPORATE_ACTION | Action und Intervallabdeckung prüfen; manuelle und kanonische Effekte nicht doppelt buchen |
| UNKNOWN_COST_BASIS | Einstand bleibt unbekannt; nur mit belegter Herkunft korrigieren |
| NEGATIVE_CASH | Finanzierung, fehlende Buchungen oder Gebühren anhand des Auszugs prüfen |

Unter **Datenqualität** führen Aktionen direkt zu Import, Instrumentzuordnung, Buchungen und Quellenprüfung. Ein leerer Fehlerkatalog beweist keine vollständige Corporate-Action-Historie. Renditen bleiben entsprechend vorläufig oder gesperrt. P7-SHADOW und gesperrte P9-Empfehlungen werden dadurch nicht freigegeben.
