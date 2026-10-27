# PR7 – Quellenprüfung und Freigabeumfang

Prüfdatum 26.10.2026. **Dokumentationsprüfung, keine Operatorfreigabe.**
Die lokale Registry wurde read-only unter `backups/pr7-source-registry.json`
erfasst. Alle unten genannten externen Quellen bleiben deaktiviert; Yahoo
BLOCKED, die übrigen UNKNOWN. MANUAL_CSV ist ausschließlich für manual_upload
freigegeben. TEST-Quellen sind keine echten Providerbelege.

| Quelle | Geeigneter Umfang / Grenzen | Aktuelle Primärbelege und technische Regeln | Noch erforderlicher Entscheid |
| --- | --- | --- | --- |
| ECB | EUR-FX-Referenzreihen, keine Wertpapierkurse/Actions | [Copyright](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html): Nutzung direkt bezogener Information mit Quellenangabe, korrekter Wiedergabe und Kennzeichnung eigener Änderungen; Autorenwerke ausgenommen. API-Hilfeseite war über das Recherchewerkzeug nicht erreichbar. | Konkrete EXR-Reihen, Tageskalender, Speicherung und Ableitung im versionierten Scope festhalten; keine Echtabnahme aus dem Copyrighttext ableiten. |
| SEC_EDGAR | US-Filer/XBRL/Filingoriginale, keine Kurse, CIK ≠ ISIN/Listing | [Developer Resources](https://www.sec.gov/about/developer-resources): programmatischer JSON-/Archivzugriff, effiziente begrenzte Abrufe, höchstens 10 Requests/s pro Nutzer über alle Geräte; identifizierbarer Bot. | Kontakt/User-Agent, konkrete CIK und Rechte am konkreten Drittinhalt samt Aufbewahrung dokumentieren. Keine universelle Rechtefreigabe für alle Anlagen eines Filings. |
| OPENFIGI | Internationale Identifier/Listingkandidaten; keine Preise oder historische Listingvollständigkeit | [API](https://www.openfigi.com/api/documentation): Mapping ohne Key 25/min und 10 Jobs; mit Key 250/min und 100 Jobs. Search 5/20 pro Minute. Retry-After beachten. [FAQ](https://www.openfigi.com/about/faq): freie Speicherung/Weiterverwendung der FIGI-Symbologie; Identifier/Metadaten unter offenem Lizenzmodell. | Konkreten Mapping-/Metadatenscope, Attribution/Lizenz und gegebenenfalls Rechte fremder Eingabekennungen dokumentieren; Mehrfachtreffer nur manuell bestätigen. Key optional. |
| SNB | Makro-/Referenzreihen; vorhandener Adapter monatlich, kein täglicher Portfolio-FX-Ersatz | [Copyright](https://www.snb.ch/en/srv/disclaimer_copyright): nichtkommerzielle Speicherung/zweckgemäße Weiterverwendung, Fremdrechte beachten. [API-Hilfe](https://data.snb.ch/en/help_api): CSV/JSON, Updates über lastUpdate oder ETag/If-None-Match/304, kein regelmäßiges Vollabruf-Polling. [Haftungshinweis](https://www.snb.ch/en/srv/disclaimer_liability): Informationszweck und besondere Grenzen für Finanztransaktionsreferenzen. | Konkreter Cube/Dimensionen/Frequenz, Fremdquelle, Attribution und erlaubter Analysezweck; keine unbelegte tägliche Marktabdeckung. Keine garantierte numerische Quote aus der Hilfe ableiten. |
| ALPHAVANTAGE | Begrenzte tägliche Kurse für konkret bestätigte Symbole; globale CH-/EU-/ETF-Abdeckung nicht abgenommen | [Bedingungen](https://www.alphavantage.co/terms_of_service/) erlauben persönliche nichtkommerzielle Nutzung unter EULA; [Support](https://www.alphavantage.co/support/) nennt 25 kostenlose Requests/Tag und lizenzabhängige Echtzeit-/Delayed-Daten. Key erforderlich; angepasste Daten berücksichtigen Splits/Dividenden und sind nicht ohne Weiteres rohe Ausführungskurse. | Persönliche Berechtigung, Endpoint/Plan, MIC/Währung, dauerhafte unveränderliche Originalablage und Aufbewahrung nach Vertragsende ausdrücklich prüfen. Keine unbegrenzte kostenlose Historie oder vollständige Corporate Actions versprechen. |
| COMPANY_IR | Einzeln bestimmte Emittentenberichte/Dokumente | Ohne konkreten Host/Dokumentvertrag keine repräsentative Rechteprüfung möglich. Öffentliche Erreichbarkeit ist kein Archivierungs-/Indexierungsrecht. | Je Host: Automatik, Dokumentoriginal, Langzeitarchiv, Analyse/RAG, Attribution und Rate-Limit belegen. Kein universeller Crawler. |
| NEWS_RSS | Metadaten/Links einzelner Feeds, kein pauschales Volltextarchiv | Ohne konkreten Feed keine gemeinsame Lizenz oder Quote. RSS ist ein Format, keine Nutzungsfreigabe. | Je Feed: Automatik, Metadaten/Artikeltexte, Originalaufbewahrung, Retention, Ableitungen und Attribution getrennt entscheiden. |

## Weitere kostenlose Kurskandidaten

[Twelve Data Basic](https://twelvedata.com/pricing) nennt 8 API-Credits/min,
800/Tag und US-Aktien/ETFs, FX sowie begrenzte globale Trials. Breite globale
EOD-Aktien-/ETF-Abdeckung steht im kostenpflichtigen Grow-Umfang. Die
[Bedingungen](https://twelvedata.com/terms) unterscheiden Display/Non-Display,
Subscription und Drittbörsenrechte. Deshalb kein belegter kostenloser
CH-/EU-Komplettversorger; konkretes privates UI-/Archivrecht bleibt zu prüfen.
Kein Adapter aktiviert und kein Key beantragt.

Stooq-Bedingungen zeigten eine Browser-Verifikation; kein Umgehungsversuch,
keine positiven Automatisierungs-/Archivannahmen. SIX-Lizenzseite war über das
Recherchewerkzeug nicht abrufbar. Yahoo bleibt unter dem bereits dokumentierten
ausdrücklichen Erlaubnisvorbehalt. Keiner dieser Zustände berechtigt einen
Collectorabruf.

Für Schweizer/US-/europäische Aktien und ETFs bleibt zulässiger manueller
Import der verfügbare lokale Weg. Allgemeine ISIN-Erfassung belegt keine
Kursabdeckung: MIC, Währung, Datumsintervall, Delisting und Actioncoverage sind
je Instrument zu prüfen. CHF/EUR/USD sind der vorhandene Ledgerumfang.
Historische Downloadbarkeit wird niemals als damalige lokale Verfügbarkeit
oder vollständiges PIT-Archiv ausgegeben.

## Einheitliche Entscheidung

Vor jeder Aktivierung im vorhandenen append-only Reviewvertrag festhalten:
Primärbeleg mit Datum/Fundstelle, privater Zweck, automatisierter Abruf,
exakte Originalspeicherung, Langzeitarchiv/Retention, abgeleitete Analyse,
Attribution, Endpoint/Markt/Währung/Instrument, Quote und nächste Prüfung.
Review und anschließende Aktivierung bleiben getrennt. Neue Erkenntnisse
ändern keine alte Beobachtungs- oder Rechteversion rückwirkend.
