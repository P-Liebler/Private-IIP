# PR7 – unabhängiger Anfängertest

**PENDING_USER_TEST**, vorbereitet am 26.10.2026. Es wurde keine unabhängige
Testperson beobachtet. Automatisierte Browserprüfungen zählen nicht als dieser
Test; keine Erfolgsquote oder Zeit ist bislang erhoben.

## Vorbereitung durch den Testleiter

Nur eine isolierte synthetische Umgebung verwenden, solange Security und
Zielhost nicht abgenommen sind. Eigener Testbenutzer, eigene Zugangsdaten,
keine echten Depotdaten, keine automatische Collection. Den exakt getesteten
Build/Digest, Gerät, Browser, Bildschirmgröße und Startzustand protokollieren.
Passwort und Originaldateien gehören nicht in das Protokoll oder GitHub.

Eine eindeutig als synthetisch bezeichnete Transaktions-CSV sowie dazugehörige
Kurs-/tägliche FX-Dateien nach den vorhandenen Importvorlagen bereitstellen.
Ein Instrument besitzt absichtlich eine falsche beziehungsweise fehlende
Kursbeobachtung; ein zweiter zulässiger manueller Datensatz erlaubt eine
nachvollziehbare Korrektur. Erwartete Positionen, Cash und CHF-Bewertung vorher
separat berechnen. Keine korrigierte Originaldatei anstelle der ersten ablegen:
beide bleiben mit Herkunft und Korrekturbezug erhalten.

Zunächst die Testperson selbst arbeiten lassen. Hilfe erst auf Nachfrage oder
nach Abbruch geben und jede Hilfe dokumentieren. Keine finanziellen Begriffe
vorab erklären; dadurch würde das Verständnisproblem verdeckt.

## Aufgabenblatt für die Testperson

1. Melden Sie sich mit dem bereitgestellten Testkonto an.
2. Legen Sie ein Portfolio mit CHF als Basiswährung an.
3. Fügen Sie das bereitgestellte Testkonto hinzu.
4. Importieren Sie die Transaktionsdatei. Prüfen Sie die Vorschau vor Bestätigung.
5. Finden Sie die daraus entstandene Position.
6. Erklären Sie in eigenen Worten den Portfoliowert und seine Datenbasis.
7. Finden Sie das Instrument mit dem fehlerhaften oder fehlenden Kurs.
8. Führen Sie mit der bereitgestellten Korrekturdatei die passende Aktion aus.
9. Zeigen Sie Quelle, Datenalter und Freigabestatus. Erklären Sie, ob automatische Aktualisierung verfügbar ist.
10. Melden Sie sich ab und prüfen Sie, dass das Portfolio nicht mehr zugänglich ist.

## Beobachtungsbogen

| Aufgabe | Ohne Hilfe erfolgreich? | Dauer | Fehlklicks | Unklare Begriffe | Abbruch/Hilfe | Vorschlag |
| --- | --- | --- | --- | --- | --- | --- |
| 1 Anmeldung | offen | — | — | — | — | — |
| 2 Portfolio | offen | — | — | — | — | — |
| 3 Konto | offen | — | — | — | — | — |
| 4 CSV/Vorschau/Commit | offen | — | — | — | — | — |
| 5 Position | offen | — | — | — | — | — |
| 6 Wert verstehen | offen | — | — | — | — | — |
| 7 Kursfehler | offen | — | — | — | — | — |
| 8 Korrektur | offen | — | — | — | — | — |
| 9 Quelle | offen | — | — | — | — | — |
| 10 Abmeldung | offen | — | — | — | — | — |

Danach erfassen: wichtigste drei Verständnisprobleme, unerwartete Ergebnisse,
Vertrauen in Teilwerte/fehlende Daten, Tastatur- und mobile Bedienbarkeit.
Die Testperson darf keine fehlenden Daten als Nullwert oder synthetische
Testwerte als reale Finanzdaten verstehen. Jede finanzielle Abweichung vor
einem erneuten Test fachlich untersuchen.

## Ergebnis und Nachbesserung

Testleiter, pseudonymisierte Person, Datum, Build und Hilfen ergänzen. Pro
Problem einen reproduzierbaren Schritt und eine konkrete Änderung festhalten;
reparierte Hauptaktionen gezielt nachprüfen. Der Anfängerbefund ersetzt keine
Security-, Quellen-, Brokerabgleich- oder Restoreabnahme.
