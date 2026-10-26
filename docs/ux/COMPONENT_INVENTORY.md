# PR6 – Komponentenbestand

Die folgenden Bausteine sind implementiert. Der konkrete lokale Browserumfang und verbleibende manuelle Prüfungen stehen im [Gesamtbericht](../PR6_ACCEPTANCE_REPORT.md); nicht jede Zustandskombination jedes Bausteins ist einzeln browserseitig abgenommen.

| Datei unter frontend/web/components | Bausteine / Vertrag |
| --- | --- |
| ui/primitives.tsx | PageHeader, FinancialMetric, SummaryCard, StatusIndicator, DataFreshness, EmptyState, ErrorState, LoadingSkeleton, ContextualHelp, ConfirmationDialog, DetailDrawer, Stepper, Tabs, AccessibleSelect, CurrencyInput, DateInput, FileDropzone, SearchCombobox, ActionList, Button |
| ui/data-table.tsx | Generische filterbare/sortierbare Tabelle mit mobilen Karten und fehlenden Werten am Ende |
| ui/chart-container.tsx | Themeabhängiger TradingView-Chart, explizite Lücken, Punkte ohne Kalendernachweis, gleiche Daten als Tabelle |
| ui/theme-provider.tsx | Hell/Dunkel/System; nur Präferenzcookie |
| ui/toast.tsx | Begrenzte, schließbare Meldungen; keine finanzielle Erfolgsbehauptung |
| capabilities.tsx | Authentifizierte Sichtbarkeit je Betreiberrolle, Ausfall sperrt Betreiberanzeige |
| portfolio-setup-wizard.tsx | Portfolio/Konto/optionale Cashbuchung/CSV/Marktdaten/Bewertungsprüfung mit bestehenden APIs |
| transaction-csv-import.tsx | Raw-first-Vorschau, explizites Zahlen-/Datumsformat, Instrumentauflösung, erneute Vorschau nach Änderungen |
| market-data-import.tsx | Aus bestehender Importseite extrahiert; gleicher Preview-/Commit-Vertrag, auch im Assistenten |
| holdings-table.tsx | Wiederverwendete Positionstabelle/mobil beschriftete Karten, Kennung, Bewertung und Provenienzdrawer |
| position-highlights.tsx | Qualifizierte vorläufige Wertunterschiede; keine Tagesrangliste oder Empfehlung |
| risk-snapshot-charts.tsx | Versionierte Anzeige gespeicherter P8-Rendite-/Benchmark-/Drawdown-Reihen; fehlende Reihen gesperrt |
| forecast-interval.tsx | Anzeige ausschließlich validierter Intervallgrenzen; gleicher zugänglicher Text |
| instrument-events.tsx | Kanonische Actions und Nachrichten mit Belegen; keine Vollständigkeitsbehauptung |
| document-removal-button.tsx | Bestätigter Rückzug mit ausdrücklichem Hinweis auf erhaltene Originale |
| lib/booking-request.ts | Opaquer Wiederholungsschlüssel im URL; keine Finanzentwürfe oder Sessiontokens |

Radix stellt Dialog-/Drawer-Fokusverwaltung, Tabs und Tooltips bereit. cmdk stellt die suchbare Auswahl bereit. Standardformulare verwenden native Elemente. Ausstehend: menschliche Prüfung der Beschriftung/Fokusführung und vollständige Zuordnung aller alten Seiten zu den neuen Komponenten.
