# PR10 – Konkreter Quellenentscheid und Live-Nachweisbogen

**DRAFT / NOT_APPROVED**, vorbereitet am **29.10.2026**. Dies ist eine Vorlage
für den vorhandenen Source-Registry-/Collectorvertrag, keine neue Pipeline und
kein bereits erteilter Operatorentscheid. Die tatsächlichen Rechtebelege,
Namen, Entscheidungen, Originale und Portfolioreceipts werden privat erfasst.
Keine Schlüssel, Login-/TOTP-Daten oder Depotdateien in Git/CI ablegen.

Primärprüfung und technische Grenzen:
[PR10C-Live-Datenbericht](../PR10C_LIVE_DATA_REPORT.md).

## 1. Vor dem ersten Netzwerkrequest privat ausfüllen

| Feld | Tatsächlicher Reviewwert |
| --- | --- |
| Quelle / Registry-ID | `ECB` oder `OPENFIGI`; vorhandene Source-ID lesen |
| Verantwortliche Person / Rolle | Autorisierter tatsächlicher Operator |
| Entscheid / Zeitpunkt | `UNKNOWN` bis zum tatsächlichen Entscheid; UTC-Zeit entsteht bei Erfassung |
| Primärbeleg / Fundstelle | URL, tatsächliches Prüfdatum, archivierter nicht sensitiver Rechtebeleg samt Hash |
| Berechtigter Nutzer / Zweck | Konkrete private Bewertungs- bzw. Mappingnutzung |
| Automatisierter Abruf | Exakter Endpoint, zulässige Serien/Identifier und erlaubtes Intervall |
| Speicherung | Exakte Antwortbytes vor Parsing, unveränderliche Raw-Aufbewahrung, Speicherung über Vertragsende geklärt |
| Ableitung | Interne Analyse erlaubt; ML getrennt entscheiden und hier nicht automatisch zulassen |
| Attribution / Änderungen | Quellenangabe und Kennzeichnung der eigenen Kreuzkursberechnung festgelegt |
| Grenzen | Zulässige Quote, lokale Tages-/Parallelgrenzen, kein Lasttest am Provider |
| Nächstes Review | Tatsächliches zukünftiges Datum mit UTC-Zeit; kein unbegrenzter Freibrief |
| Betriebsfreigabe | Privates Ziel, Securityreview, TLS/Egress und Original-/Backupschutz geprüft |
| Aktivierung | Separater tatsächlicher Schritt nach Review; wiederkehrende Sammlung zunächst aus |

Ein neuer Review deaktiviert die Quelle im bestehenden Vertrag. Erst eine
getrennte Aktivierung ist wirksam. Widerruf/Ablauf stoppt weitere Versuche;
ein alter Auftrag darf keinen später geänderten Review erben.

## 2. ECB: bestehende API-Felder vorbereiten

Der folgende Body zeigt die vorhandenen Felder von
`POST /api/v1/data-operations/sources/ECB/review`. Er ist absichtlich
`UNKNOWN`, ohne Freigabedatum und ohne vollständige Datumswerte; er darf nicht
als positive Freigabe übernommen werden. Der Operator ersetzt jeden Platzhalter
und entscheidet nach Prüfung selbst über `APPROVED`.

```json
{
  "status": "UNKNOWN",
  "terms_url": "https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html",
  "scope": "DRAFT: private Referenzbewertung; beide EXR-Inputs, exaktes Raw-Archiv, dauerhafte Aufbewahrung und interne Ableitung separat belegt. fx_inputs=EXR.D.CHF.EUR.SP00.A,EXR.D.USD.EUR.SP00.A fx_coverage=VON-DATUM|BIS-DATUM",
  "allowed_uses": ["fx_rates", "raw_archive", "derived_analysis"],
  "decision_note": "DRAFT: echte Fundstellen, Rechtebeleg, Attribution und tatsächlichen Operatorentscheid vor Freigabe eintragen.",
  "next_review_at": null,
  "rate_limit_per_minute": 1
}
```

Bei `UNKNOWN` werden im bestehenden Registryzustand keine Nutzungen freigegeben.
`fx_coverage` muss **das gesamte** tatsächlich angefragte Fenster enthalten;
ein Holdings-Refresh fragt überlappend die letzten 32 Tage bis gestern an.
Die 2.000-Zeichen-Grenze des vorhandenen Source-Scopes bleibt bestehen.
Die API nimmt die Identität des angemeldeten Datenoperators auf. Ein alternativer
CLI-Review innerhalb des autorisierten API-Containers muss dieselben echten
Felder einschließlich `--reviewer` enthalten. Keine CLI-Ausführung mit
Platzhaltern, keinem Ersatzreviewer oder automatisch gewähltem Ablaufdatum.

Nach tatsächlicher Zustimmung:

1. Review in **Einstellungen → Datenquellen** erfassen und die append-only
   Review-ID/den Zeitstempel lesen.
2. Quelle getrennt aktivieren; Aktivierungsbeleg sichern.
3. Erst danach in **Datenbetrieb** Preview und einen einzelnen Job starten.

Der vorhandene Requestbody für Preview (`POST
/api/v1/data-operations/preview`) und anschließend Job (`POST
/api/v1/data-operations/jobs`) ist:

```json
{
  "source_slug": "ECB",
  "kind": "ECB_FX",
  "start": "VON-DATUM",
  "end": "BIS-DATUM",
  "series": "EUR_CHF"
}
```

Für die erste Abnahme ein kurzes abgeschlossenes Veröffentlichungsintervall
innerhalb des freigegebenen Fensters einsetzen. Vorschau, Rechte und tatsächliche
Restquote kontrollieren. Die technische Serienauswahl ändert nicht die beiden
tatsächlich angefragten EUR-Inputs. Keine Collector-Umgehung durch einen
separaten Downloadclient und keine neue Schedulerimplementierung.

## 3. Privates Ereignisprotokoll: nicht durch leere Tabellen freigegeben

Je Ereignis einen neuen privaten Beleg anlegen. Diese Tabelle enthält keine
erzeugten IDs oder erfundenen Beobachtungszeiten.

| Feld | Erstabruf | Identische Wiederholung | Späterer Veröffentlichungstag |
| --- | --- | --- | --- |
| Tatsächlicher Review-/Aktivierungsbeleg | offen | offen | offen; noch gültig? |
| Requestfenster und konkrete Serien | offen | exakt gleich | tatsächliches neues Intervall |
| Job-ID / tatsächlicher Beginn / Ende UTC | offen | offen | offen |
| Ergebnis / Fehler / Retry / Quote | offen | offen | offen |
| Raw-ID / HTTP-Status / SHA-256 / Byteprüfung | offen | offen, ggf. 304/No-New-Data | offen |
| Tatsächlicher Referenztag beider Legs | offen | unverändert oder neue Revision | neuer veröffentlichter Tag |
| Canonical-/Leg-IDs / Quellen-IDs | offen | keine Duplikate | offen |
| `known_at` / `retrieved_at` | offen | alte Beobachtung nicht rückdatiert/erneuert | echte neue Kenntniszeit |
| Quarantäne / Qualität / Konflikte | offen | offen | offen |
| USD/CHF Decimal-Ableitung / gleicher Leg-Tag | offen | offen | offen |
| Portfolio-ID / Stichtag / UI-Freshness | privat offen | privat offen | privat offen |
| Sync-/Checkpoint- und Idempotenzbeleg | offen | ausdrücklich vergleichen | tatsächlich fortgesetzt |
| Prüfer / fachlicher Entscheid | offen | offen | offen |

`SUCCESS`, ein leerer Request oder eine 304-Antwort ersetzt keinen der fehlenden
fachlichen Belege. Erst zwei echte, zeitlich getrennte Veröffentlichungsereignisse
plus abgenommener geplanter Betrieb können `AUTOMATIC_REFRESH_VERIFIED`
begründen. Rechtewiderruf, 429, Timeout und Schemafehler ausschließlich mit
Offline-Fixtures testen.

## 4. OpenFIGI: konkretes Mapping statt Kursversprechen

Vorher privat freigeben: `mapping`, archivierte Originalantwort, zugehörige
Metadaten und interner Analysezweck; Eingabekennungen und deren Rechte,
Endpoint `https://api.openfigi.com/v3/mapping`, Quote, Zeitraum und nächste
Prüfung. Ein neuer Review benötigt dieselben Pflichtfelder wie ECB, einen
passenden OpenFIGI-Terms-Beleg und einen tatsächlichen Operator. API-Key nur im
geschützten Secret, niemals im Scope/Protokoll. Keine Kurs- oder ML-Freigabe
aus diesem Review ableiten.

Der bestehende `OPENFIGI`-Datenbetriebsjob braucht genau eine tatsächliche
`instrument_ids`-UUID. ISIN/FIGI, MIC und Währung kommen aus den zuvor geprüften
Instrumentdaten. Falls diese Angaben fehlen oder widersprüchlich sind, zuerst
Identität klären. Keine beispielhafte ISIN ist ein Nutzerbestand.

Im privaten Nachweis festhalten:

1. Tatsächliche interne ID, Eingabekennung und mitgesendete Filter.
2. Requestzeit, Raw-ID, Originalhash und verifizierte Antwort.
3. Alle echten Kandidaten beziehungsweise No-Match; fehlende Felder sichtbar.
4. Unabhängiger Listing-/MIC-/Währungs-/Zeitbeleg, falls die Antwort ihn nicht
   liefert; keine stillschweigende Ableitung.
5. Ausdrückliche Auswahl der konkreten FIGI aus diesem gespeicherten Original;
   auch ein Einzelkandidat wird nicht automatisch akzeptiert.
6. Audit-/Identifiernachweis und Wirkung in der Instrumentenseite.

Mehrfachlistings bleiben getrennt prüfpflichtig. Eine FIGI-Bestätigung belegt
weder automatische Kurse noch Dividenden-/Split-Abdeckung.

## 5. Je tatsächlichem Kurslisting privat ergänzen

| Feld | Erforderlicher Inhalt |
| --- | --- |
| Identität | Interne ID, ISIN, MIC, Handelswährung, Instrumenttyp, Gültigkeitsintervall |
| Datenvertrag | Provider, Symbol/Endpoint oder rechtmäßiger Originalexport, erlaubter Nutzungsort/Plan |
| Coverage | Tatsächliches Datumsspektrum und Veröffentlichungsintervall, unadjustierte Kurse |
| Rechte | Abruf, exaktes Raw-Archiv, Langzeitaufbewahrung, interne Analyse und ML getrennt |
| Actions | Dividenden, Splits und instrument-/intervallspezifischer Coveragebeleg |
| Qualität | Echte Raw-/Canonical-IDs, Freshness, mögliche Konflikte und Review |
| Entscheider | Tatsächlicher Operator, Datum, Primärbeleg, nächste Prüfung |

Keine vorhandenen spezifischen Portfolioinstrumente werden angenommen. Bei
fehlenden Rechten bleibt automatischer Abruf gesperrt; ein rechtmäßiger
manueller Import nutzt dieselben Original-/Preview-/Kanonik-/Ledgerverträge.
