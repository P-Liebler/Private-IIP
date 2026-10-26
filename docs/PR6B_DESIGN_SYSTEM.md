# PR6B – Designsystem und lokale Prüfnachweise

Abgleich 26.10.2026, technische Browsernachweise vom 23.10. Implementiert und im beschriebenen lokalen Umfang geprüft; keine vollständige Barrierefreiheitszertifizierung.

## Grundlage

`frontend/web/styles/design-system.css` definiert semantische Oberflächen, Text-, Akzent-, Positiv-, Negativ- und Warnfarben; ein 8-Pixel-Abstandssystem, Typografie, Radien, Schatten, Fokus, Bewegung und Breakpoints. Bestehende Utility-Farben verweisen auf diese Tokens, damit alte Deep-Links dieselbe Darstellung erhalten. Hell, Dunkel und System werden durch CSS-Farbschemata unterstützt. Nur die Darstellungspräferenz steht in einem Cookie; keine Finanzdaten oder Sitzungstokens werden im Browserstorage gespeichert.

Sechs Hauptbereiche ersetzen die lange Hauptnavigation. Auf Mobilgeräten öffnet ein Radix-Dialog die Navigation; Tastaturfokus, Escape und Rückkehr zum Auslöser übernimmt das Primitive. Betreiberziele werden anhand einer authentifizierten, nicht gecachten Capability-Antwort angezeigt. Das ist eine Sichtbarkeitsregel; bestehende Backendberechtigungen bleiben maßgeblich.

## Bausteine

- Gemeinsame Seitentitel, Kennzahlen, Status mit Text und Icon, Datenstand, Lade-, Fehler- und Leerzustände.
- Dialoge, Detaildrawer, Tabs und Hilfetexte verwenden Radix; die Instrumentauswahl verwendet cmdk. Einfache Auswahlfelder bleiben native HTML-Elemente.
- Tabellen bieten Filter und Sortierung auf Desktop sowie beschriftete Karten auf Mobilgeräten. Fehlende Sortierwerte bleiben zuletzt und werden nicht zu null Euro umgedeutet.
- Charts verwenden TradingView Lightweight Charts 5.2.1 mit Namensnennung und Lizenzhinweis. Farben werden nach Themewechsel aus den berechneten CSS-Farben gelesen. Eine zugängliche Tabelle zeigt dieselben Werte.
- Explizite Bewertungslücken erzeugen getrennte Liniensegmente. Unbekannte Handelskalender erlauben keine Behauptung vollständiger Sitzungsabdeckung.
- Dateiauswahl erhält das Originalobjekt unverändert; Formatinterpretation geschieht im bestehenden Raw-first-Import.

## Automatisierte Abnahme und verbleibende Grenzen

Bestanden: sechs primäre Bereiche, sechs Zielbreiten 360–1920 px, Light/Dark/System samt Persistenz, Theme-/Zeitraumwechsel eines tatsächlichen Canvas-Charts, horizontale Layoutgrenzen, Tastaturdialog mit Escape und Fokusrückkehr. Berechnete Text-/Status-Tokens erreichen mindestens 4.5:1 zur Oberfläche, starke Kontrollränder mindestens 3:1. 30 geschützte Start-/Unterziele wurden auf 390/1440 px ohne Seitenfehler geprüft. Das ist kein Nachweis aller denkbaren Inhaltskombinationen oder vollständiger Screenreader-/WCAG-Abnahme. Externe Anfängerprüfung bleibt PENDING_USER_TEST. [Gesamtbericht](PR6_ACCEPTANCE_REPORT.md).
