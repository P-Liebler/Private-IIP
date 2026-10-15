# Intelligente Alerts und Notifications

Privat, versioniert, datengetrieben. Regeln, Auswertungen und Ereignisse sind unveränderliche Archive; Archivierung, letzter Prüfzeitpunkt und Gelesenstatus sind getrennte Betriebszustände.

| Alert | Eingabe / Grenze |
| --- | --- |
| PRICE_THRESHOLD | Akzeptierter datierter Kurs / Handelswährung; kein Livekurs |
| FORECAST_CHANGED | Nur aktuelle validierte Produktionsprognose; absolute Wahrscheinlichkeitsänderung |
| RISK_INCREASED | Frischer P8-Snapshot mit passendem Ledger-/Marktstand; Volatilitätsanteil |
| CONCENTRATION_INCREASED | Gleicher P8-Vertrag; größtes Positionsgewicht |
| EARNINGS_UPCOMING | Operatorgeprüfter versionierter Kalender mit Original-JSON; Tage bis Termin |
| NEGATIVE_NEWS | Nur validierte, zeitlich belegte Sentimentklassifikation; keine Keyword-Erfindung |
| FUNDAMENTAL_DETERIORATION | Verfügbarer aktueller P5-Quality-Score, Scorepunkte |
| MODEL_CONFIDENCE_CHANGED | Produktionsprognose mit empirischer Coverage; Änderung des Anteils |

Fehlende Daten liefern `ALERT_EVALUATION_UNAVAILABLE`, Zustand `null`, niemals implizit „alles gut“. Änderungsregeln brauchen zuerst einen gültigen Ausgangswert. Schwellenübertritte, Ursprungs-IDs und Konfiguration bilden den Fingerprint. Identische Eingaben erzeugen keine neue Auswertung oder Notification. Cooldown und Vorgängerzustände werden aus der Datenbank gelesen und überstehen Worker-Neustarts. Gültige „Termin storniert“-Evidenz kann einen Terminalert zurücksetzen, ohne einen Nullwert zu erfinden.

Kalenderimporte speichern Originalbytes vor Parsing; bekannte Publikation und erste lokale Beobachtung bleiben getrennt. Korrekturen verweisen auf die eigene Vorgängerversion. Eine unbekannte Terminquelle erzeugt keinen geschätzten Earnings-Termin. Derzeit existiert kein automatisch freigegebener Kalender- oder Sentimentprovider.

Celery Beat prüft jede Minute einen begrenzten Batch; Regeln frühestens nach fünf Minuten erneut, höchstens 50 pro Batch / 50 aktive Regeln je Nutzer. Gemeinsamer Advisory Lock verhindert parallele Dispatchläufe. Authentifizierte manuelle Auswertung ist separat begrenzt. In-App-Notifications besitzen eindeutigen privaten Deduplikationsschlüssel und idempotenten Gelesenstatus; keine E-Mail oder externe Nachricht wird versandt.
