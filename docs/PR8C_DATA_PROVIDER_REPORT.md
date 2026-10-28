# PR8C – Datenversorgung für Private Core V1

Stand: 27.10.2026. **BLOCKED_BY_SOURCE_APPROVAL**. Dokumentationsprüfung ist keine Quellenaktivierung. Es wurden keine Finanzprovider-Endpoints aufgerufen und keine externen Quellen freigegeben. Auch die erneute Prüfung von Hilfs-/Rechteseiten liefert keine importierten Finanzdaten.

## Geprüfter Umfang

| Priorität | Quelle / vorhandener Datenpfad | Primärprüfung 27.10.2026 | Noch erforderliche Operatoraktion |
| --- | --- | --- | --- |
| Tägliche FX | ECB, bestehender `ECB_FX`-Collector für EUR/CHF und USD/CHF | [Referenzkursbeschreibung](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html): Veröffentlichung gewöhnlich gegen 16 Uhr CET an Arbeitstagen, TARGET-Schließtage ausgenommen; Informationskurse, keine tatsächlichen Transaktionskurse. [Copyright](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html): Quellenangabe, korrekte Wiedergabe, Kennzeichnung eigener Änderungen und Drittwerk-Ausnahmen beachten. | Genau diese Reihen, Abruf, Originalarchiv und CHF-Ableitung prüfen und versioniert genehmigen. Tatsächliche Broker-FX und Gebühren bleiben Ledgerdaten. Keine monatliche SNB-Reihe als Tagesersatz. |
| Identitäten | OpenFIGI, vorhandener Mapping-Review | [API-Dokumentation](https://www.openfigi.com/api/documentation): ohne Key 25 Mapping-Requests/min und 10 Jobs/Request; mit Key 250/min und 100 Jobs. Search-Limits separat, `Retry-After` bei 429. | Mapping-/Metadatennutzung und Speicherung freigeben. ISIN liefert Kandidaten; Listing, MIC, Handelswährung und Anteilsklasse manuell bestätigen. Keine Preisversorgung aus einem FIGI ableiten. |
| Aktien/ETF-Kurse | Vorhandener Alpha-Vantage-Adapter oder rechtmäßiger manueller Import | Vertrags-/Abdeckungsgrenzen aus der [PR7-Matrix](data/PR7_SOURCE_APPROVAL_MATRIX.md) bleiben offen. Es liegt keine genehmigte allgemeine CH-/EU-/ETF-Abdeckung vor. | Für jedes tatsächlich benötigte Listing Endpoint/Plan, automatisierten Abruf, unveränderte Langzeitablage, Korrekturen und Analyse erlauben lassen. Ohne Freigabe CSV verwenden. Unterschiedliche ISIN sind möglich; universelle automatische Kursabdeckung ist nicht belegt. |
| Splits/Dividenden | Vorhandener manueller Actions-Import und Coverage-Review | Split-/Dividendenbelege und deren Rechte sind instrument-/intervallspezifisch. | Original, Ex-/Zahl-/Wirksamkeitsdatum, Währung und Faktor prüfen; kanonische und manuelle Buchung nicht doppelt anwenden. Coverage nicht automatisch aus einem Einzelereignis freigeben. |
| Fundamentals | SEC, bestehender Collector | [SEC Developer Resources](https://www.sec.gov/about/developer-resources): höchstens 10 Requests/s pro Nutzer über alle Geräte, effizienter begrenzter Abruf und identifizierter Bot. | Konkrete CIK, User-Agent/Kontakt und Rechte an eingebetteten Drittwerken prüfen. CIK ist keine Börsenkennung. Keine Freigabe für Preise oder fremde IR-Dokumente daraus ableiten. |
| Yahoo | Gewünschte Quelle unter Freigabevorbehalt | Die Rechteseite lieferte am 27.10. über das Recherchewerkzeug HTTP 999; dadurch keine neue erfolgreiche Vollprüfung. Der frühere dokumentierte Sperrentscheid bleibt erhalten. | Ausdrückliche Erlaubnis für automatisiertes Sammeln und Originalarchiv nachweisen; bis dahin BLOCKED. |

## Ausführbare Operatorfolge

1. Unter **Einstellungen → Datenquellen** den bisherigen Rechteentscheid lesen. Für eine Quelle einen eigenen Beleg mit Datum, genauer Fundstelle, Nutzer, Endpoint/Serien/Listing, automatischem Abruf, dauerhafter Originalablage, Analyse, Attribution, Quote und Ablaufdatum vorbereiten. Beleg privat aufbewahren.
2. Ein autorisierter Quellenoperator erfasst den belegten Entscheid über den vorhandenen Review-Dialog. Der CLI-Vertrag ist alternativ `python -m app.sources.cli review SLUG --status APPROVED --terms-url URL --scope SCOPE --use USE --note BELEG --reviewer PERSON --next-review YYYY-MM-DD --rate-limit-per-minute LIMIT`. Platzhalter sind keine Freigabe; das genaue Datum und die Person müssen tatsächlich feststehen.
3. Erst nach dem Review getrennt aktivieren (`python -m app.sources.cli enable SLUG`). Operatorrolle und globales Scheduling sind weiterhin separate Gates. Core hat keinen Provider-Egress; vor automatischem Betrieb braucht auch der Netzwerkpfad eine ausdrückliche Prüfung.
4. In **Datenbetrieb** einen einzelnen begrenzten Abruf vorbereiten. Vor dem Start Identität, Kalender, Währung, Zeitfenster und Quote kontrollieren. Schema-/Mappingfehler nicht automatisch akzeptieren.
5. Job-ID, exakte Raw-Bytes und SHA-256, Abruf-/Beobachtungsdatum, Canonical-IDs, Qualitätsstatus und tatsächliche Frontendanzeige prüfen. Historisch geladene Daten nicht als früher lokal bekannt ausgeben.
6. Identischen Auftrag wiederholen und vorhandene Versionen/Checkpoints auf Duplikate prüfen. An einem späteren echten Veröffentlichungstag separat inkrementell aktualisieren. Erst dieser zweite Zeitpunkt belegt fortlaufende Versorgung.
7. 429/Retry-After, Schemafehler, Timeout und Rechtewiderruf ausschließlich mit den vorhandenen Offline-Tests simulieren. Bei Quelleausfall letzten Erfolg und Fehler getrennt betrachten; veraltete Werte bleiben veraltet.

## Aktualisierung der tatsächlichen Holdings

`ops/holdings_refresh.py` liest die aktuelle Ledgerbewertung über die bestehende authentifizierte API und erstellt für tatsächlich gehaltene, nicht nullwertige Stückzahlen je einen begrenzten bestehenden Preisjob. Es dedupliziert Instrumente über Konten und berücksichtigt auch Fremdwährungscash mit negativem Vorzeichen. CHF-Portfolios mit EUR/USD nutzen die vorhandenen ECB-FX-Aufträge; andere FX-Währungen/Basiswährungen werden explizit als nicht unterstützt gemeldet. Es wird keine Universalabdeckung behauptet.

Standard ist nur Vorschau. `--execute` stellt ausschließlich von der bestehenden API zugelassene Aufträge in die vorhandene persistente Queue. Quellenrechte, Mapping, Quoten, Ausführung, Retry und Checkpoints bleiben im bestehenden Backend. Die globale Vier-Job-Grenze bleibt wirksam. Jeder spätere Aufruf liest Holdings erneut. Kein automatischer Zeitplan wird installiert.

```powershell
# Zugangsdaten zuvor im geschützten Prozess-Environment setzen, niemals im Befehl.
python ops/holdings_refresh.py --origin https://PRIVATER-HOST --ca C:/privat/root.crt --portfolio-id PORTFOLIO-UUID --output backups/refresh-NEUER-ZEITPUNKT.json
```

Benötigt `IIP_OPERATOR_USERNAME` und `IIP_OPERATOR_PASSWORD`; Sitzungscookies bleiben im Arbeitsspeicher und Logout wird versucht. TOTP-geschützte interaktive Anmeldung darf dieses Hilfswerkzeug nicht umgehen. Ohne zugelassenen automatisierten Authentisierungsweg den vorhandenen Browserworkflow verwenden. Vorschau/QUEUED ist kein erfolgreicher Liveabruf. `AUTOMATIC_REFRESH_STATUS` bleibt ohne initialen und tatsächlich späteren Livebeleg gesperrt.

## Manuelle Versorgung

Die vorhandenen Browserfälle in `private-beta.spec.ts`, `portfolio.spec.ts`, `data-operations.spec.ts`, `product-ux.spec.ts` und `pr7-read-recovery.spec.ts` prüfen die echte lokale API mit ausdrücklich synthetischen Accounts: Transaktionen, mehrere Instrumente in einer Kursdatei, separate FX, Preview/Commit, Wiederholung/Korrektur, Aktionen, Kalender-/Coverage-Gates, Depotabgleich und Fehlerwiederholung. Der vollständige neue PR8-Lauf besteht mit **30/30 Browserfällen**, Testmodus und Rollen danach zurückgesetzt; [Core-Abnahmebericht](PR8E_CORE_ACCEPTANCE_REPORT.md). Auch der finale Backup-/Restorevertrag ist lokal nachgewiesen. Diese technischen Nachweise ersetzen keine echten Depotoriginale oder Rechtefreigabe; Quellenaktivierung und fortlaufende Liveversorgung bleiben gesperrt.
