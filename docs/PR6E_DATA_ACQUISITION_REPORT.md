# PR6E – Allgemeine Datenquellenprüfung mit offenen Freigaben

Prüfdatum: 23.10.2026. Nutzerentscheidung: allgemeine Unterstützung verschiedener ISINs prüfen; kein konkretes Depot vorgegeben. Kein neuer Quellenentscheid, kein Provider-Datenabruf und keine automatische Sammlung durch diese Dokumentationsprüfung.

## ISIN ist ein Ausgangspunkt, kein eindeutiger handelbarer Kurs

Eine ISIN identifiziert ein Wertpapier, aber nicht zwingend eine einzelne Börsennotierung oder Handelswährung. Identitätsauflösung muss Kandidaten samt MIC, Handelswährung, Instrumenttyp und Gültigkeit zeigen. Mehrdeutige Kandidaten verlangen Bestätigung. Fehlende Abdeckung eines Providers darf weder eine andere Notierung stillschweigend einsetzen noch einen Kaufpreis als Marktkurs verwenden.

## Primärdokumentation

| Quelle | Am Prüftag belegt / erreichbar | Eignung und offene Punkte |
| --- | --- | --- |
| [OpenFIGI](https://www.openfigi.com/api/documentation) | API-Dokumentation erreichbar; Zuordnung fremder Kennungen zu FIGI, optional unlisted/delisted equities | Internationales Mapping, keine Kurs-, FX- oder Corporate-Action-Versorgung. Kandidatenannahme und konkrete Nutzungsfreigabe bleiben separat. |
| [SEC](https://www.sec.gov/about/developer-resources) | REST-APIs für Submissions und XBRL dokumentiert | US-Filer/Fundamentals; keine weltweite ISIN-Kursquelle. Kontakt/User-Agent und gemeinsame Abrufgrenzen sind erforderlich. |
| [ECB Copyright](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html) | Rechte-/Haftungshinweise erreichbar; [API-Hilfe](https://data.ecb.europa.eu/help/api/data) erneut HTTP 503 | Geeignet für unterstützte EUR-Referenzkurse, keine Aktienkurse. Schnittstellenprüfung unvollständig; Quellenangabe und Drittparteirechte beachten. |
| [SNB Copyright](https://www.snb.ch/en/srv/disclaimer_copyright) | Nichtkommerzielle zweckverträgliche Speicherung unter Quellen-/Drittparteivorbehalt beschrieben; [API-Hilfe](https://data.snb.ch/en/help_api) nur JS-Hülle | Vorhandene monatliche Referenzadapter ersetzen keine tägliche Portfolio-FX. Keine generelle Aktien-/ETF-Abdeckung. |
| [Alpha Vantage API](https://www.alphavantage.co/documentation/) / [Terms](https://www.alphavantage.co/terms_of_service/) | Dokumentation und Bedingungen erreichbar; persönliche nichtkommerzielle Lizenz mit Einschränkungen | Vorhandener kompakter Tageskursadapter ist eine mögliche begrenzte Versorgung. Symbol/MIC/Währung, konkreter kostenloser Umfang und unveränderliche Aufbewahrung müssen vor Freigabe bestätigt werden. Keine universelle ISIN- oder CH-ETF-Abdeckung behauptet. |
| [FRED/ALFRED](https://fred.stlouisfed.org/docs/api/fred/overview.html) | Reihen-/Release-/Vintage-Abfragen dokumentiert | Makro, keine generelle Wertpapierkursquelle. Vorhandene optionale Schlüsselkonfiguration ist noch kein Collector. Fremdrechte gelten je Reihe. |
| [Yahoo Terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) | Aktueller Abruf HTTP 999; kein neuer Bedingungsnachweis gewonnen | Vorher dokumentierte Anforderung ausdrücklicher Automatikerlaubnis bleibt ungelöst. Priorität unter Freigabevorbehalt, deaktiviert. Kein Umgehungsversuch. |
| [Twelve Data Terms](https://twelvedata.com/terms) | Bedingungen erreichbar, Stand 01.01.2026; tarif- und fremdlizenzabhängige Datenrechte | Kein Adapter/Konto hinzugefügt. Aufbewahrung und Löschung nach Vertragsende müssen mit unveränderlichen Archiven vereinbar sein; kein kostenloser globaler Vollversorgungsnachweis. |
| Eigene zulässige CSV | Bestehender Vorschau-/Übernahmepfad lokal testbar | Praktischer Fallback für verschiedene manuell angelegte ISINs. Rechte am Original müssen vorliegen; kein Beweis für historische Verfügbarkeit oder vollständige Actions. |

## Weitere Arbeit

Die bestehenden PR1-Collector-Gates, DNS-Bindung, Raw-Ablage, Budgets und Jobs werden weiterverwendet. Ein neues Scraping-Framework ist durch unklare Rechte nicht gerechtfertigt. Allgemeiner Dokumentationszugriff beweist keinen erfolgreichen Produktpfad. [Live-Testmatrix und Registryzustand](data/LIVE_PROVIDER_TEST_MATRIX.md) trennen jede Nachweisstufe; [Abdeckungsgrenzen](data/REAL_MARKET_COVERAGE.md) bleiben explizit. Lokale Fehler-/Retry-/Source-Gate-Verträge sind Bestandteil der bestandenen Backendregression; ein echter wiederholter Abruf bleibt ohne Rechteentscheidung ungetestet. Status weiterhin **BLOCKED_BY_EXTERNAL_DEPENDENCY** für neue automatische Echtdatenversorgung.
