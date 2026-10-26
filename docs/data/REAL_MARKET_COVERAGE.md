# PR6 – Reale Marktabdeckung

23.10.2026: **NOT_VERIFIED**. Allgemeine Prüfung verschiedener ISINs ist beauftragt; kein konkreter Brokerexport oder reales Depot wurde bereitgestellt. Keine aktivierte automatische Kursquelle ist nachgewiesen.

| Markt / Instrumentart | Identität | Kursversorgung | Dividenden/Splits | Historische lokale Verfügbarkeit |
| --- | --- | --- | --- | --- |
| Schweizer Aktien | ISIN/MIC/Währung manuell erfassbar; OpenFIGI nur unter Gate | Manuelle zulässige CSV funktional, automatische Echtdatenversorgung offen | Manuell und versioniert; Vollständigkeit muss je Instrument/Intervall geprüft werden | Ab tatsächlicher erster Beobachtung; kein rückdatiertes Archiv |
| US-Aktien | ISIN/Ticker/FIGI und MIC; CIK für US-Filer separat | Alpha-Adapter technisch vorhanden, noch keine reale Freigabe/Abnahme | Keine pauschale Vollständigkeit | SEC-Veröffentlichung und lokale Beobachtung unterscheiden |
| Internationale Aktien | Mehrere Listings nicht zusammenwerfen | Markt-/Quellenabdeckung ungeprüft | Quellen-/Instrumentvertrag erforderlich | Rekonstruktion ausdrücklich kennzeichnen |
| ETFs | ISIN ist keine alleinige Börsen-/Währungsentscheidung | Kostenlose globale/CH-Abdeckung nicht belegt | Ausschüttungen/Splits nur mit Herkunft und kontrollierter Anwendung | Kein historisches Mitgliedschafts-/PIT-Versprechen |
| Delistete Instrumente | Kennungshistorie und optionale unlisted-Kandidaten | Keine sichere historische Vollversorgung behauptet | Delisting verlangt Review | Damalige Listung und heutiger Mappingtreffer sind verschieden |

Portfolio-/Transaktionswährungen sind derzeit fachlich auf CHF, EUR und USD begrenzt. Allgemeine Instrumenterfassung bedeutet deshalb keine Bewertung beliebiger Handelswährungen. Andere Währungen erfordern eine absichtliche Erweiterung der validierten Ledger-/FX-Verträge. Fehlende Währungsunterstützung bleibt ein Eingabefehler, kein Nullwert.

Die Live-Prüfschritte stehen in der [Live-Nachweismatrix](LIVE_PROVIDER_TEST_MATRIX.md). Monatliche SNB-Referenzen ersetzen keine tägliche Bewertungs-FX. „0 CHF verpflichtende API-Kosten“ schließt Hardware, Strom, Speicher und Betrieb nicht ein.
