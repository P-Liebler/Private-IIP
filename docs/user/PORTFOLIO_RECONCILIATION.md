# Mit dem Depotauszug vergleichen

Im Portfolio **Depotabgleich** öffnen. Konto, Stichtag und eine nachvollziehbare Belegreferenz eingeben. Über **Vorhandene Instrumente vorbereiten** werden ausschließlich Instrumente vorgeschlagen; Stückzahlen und Beträge müssen vom Auszug selbst eingegeben werden. Weitere Instrumente lassen sich suchen und zuordnen.

Cash je Währung eingeben. Leer bedeutet **nicht angegeben**, nicht null. Nur bei ausdrücklich bestätigtem **vollständigem Kontoauszug** werden nicht aufgeführte Positionen/Währungen als null erklärt. Optional einen belegten Gesamtwert in Portfolio-Basiswährung und Positionsmarktwerte in nativer Währung angeben.

**Abgleich berechnen** vergleicht denselben Ledger und dieselbe P4-Bewertung. Es werden keine Buchungen erzeugt, geändert oder passend gerechnet. Eingaben sind manuelle Auszugsangaben; die temporäre Anzeige ist kein archivierter, verifizierter Brokeroriginal-Nachweis.

| Ergebnis | Nächster Schritt |
|---|---|
| MATCHED_ENTERED_FIELDS | Eingegebene Felder stimmen überein; Umfang beachten. Kein automatisches REAL_PORTFOLIO_VERIFIED |
| DIFFERENCES_FOUND | Stückzahl, Gebühren, Dividenden, Instrument/Börse, FX-Referenz, Stichtag und Corporate Actions prüfen |
| PARTIAL | Für angegebene Vergleichswerte fehlen vollständige/gültige Bewertungsdaten; Datenqualität bearbeiten |

Unter **Transaktionen** nötige Korrekturen ausdrücklich vornehmen; alte Versionen bleiben erhalten. Ein unterschiedlicher Marktwert kann aus anderem Bewertungszeitpunkt oder FX-Referenzkurs entstehen. Ein Schlusskurs ist kein handelbarer Livepreis. Den Ledger niemals allein deshalb ändern, damit ein ungeklärter Auszugswert passt.

Echte Auszüge, Berichte und Wiederherstellungsnachweise nur auf getrennten privaten, freigegebenen Speichern behalten. Keine Brokerdateien, Kontonummern, Beträge oder Screenshots in Git/CI-Artefakte hochladen.
