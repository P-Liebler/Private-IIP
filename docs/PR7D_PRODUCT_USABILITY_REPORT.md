# PR7D – Produkt- und Bedienungsprüfung in Arbeit

Neuester Stand 27.10.:29/29 Browserfälle bestanden; native kompakte Auswahl,
aktueller HTTPS-Browser und klare Grenzen stehen in den beiden letzten Abschnitten.

26.10.2026. **UX_FUNCTIONAL_STATUS: LOCAL_REGRESSION_VERIFIED / PARTIAL_WORKFLOWS_OPEN**.

Das bestehende PR6-Design wurde erhalten. Frischer Frontend-Lint, Typecheck
und Standalone-Produktionsbuild mit Zod4.6.7 bestehen. Der erste vollständige
Browserlauf mit einem neu erzeugten synthetischen Restore-/Research-/P6-/P10-
Account ergab 25/26 bestandene Fälle, keine Skips; Testmodus danach geprüft
zurückgesetzt. Chartfall am Selektor der Portfolioauswahl gescheitert und
anhand des tatsächlichen zugänglichen Namens korrigiert. Die gleichentägige
unveränderte FX-Zeile wird im Fixture-Skript korrekt als Dublette akzeptiert;
Golden CHF10’180 bleibt zwingend. **Der folgende vollständige Lauf v3 bestand
26/26 in3,3 Minuten ohne Skips**, einschließlich Chart/Theme/Tastatur. Belege:
`backups/pr7-fresh-browser-v3.txt` und `...-status.json`. Der normale lokale
Modus mit ausgeschaltetem Testprovider, entfernten Testrollen und deaktivierter
Collection/Forward wurde danach geprüft.

Die Chart-Fixture ist ein eigenes synthetisches CHF-Cash-Portfolio mit echten
Ledger-API-Aufrufen. Ihre rekonstruierte Historie ersetzt keine historische
lokale Verfügbarkeit. Setupzeit wird aus der Loginmessung ausgeschlossen.
Goldenportfolio und finanzielle Bewertungs-/Coveragegates bleiben erhalten.

Login bis sichtbare Positionen: **2362ms** in diesem lokalen synthetischen
Standalone-Lauf (`local-dashboard-timing.json` im Chartfall). Aufbau der
zusätzlichen Chart-Fixture explizit ausgeschlossen. Keine kontrollierte
Kalt-/Warm-Paarmessung und kein Produktions-SLA; die Messung allein beweist
keine allgemeine Performanceverbesserung gegenüber PR6.

Noch offen: systematischer Abgleich sämtlicher PARTIAL-Aktionen und
Fehler-/Rechte-/Retryzustände, tatsächliche kalte/warme Performanceanalyse
mit Ressourcen-/API-Aufschlüsselung und konkret gemessene Optimierungen,
Assistentenfortschritt/Abbruch/Timeout-Abnahme auf dem realen lokalen Modell.
Vorhandene synthetische Ersatzantworttests sind kein neuer Nachweis einer
schnellen realen Modellantwort.

## Neue Fortsetzungsabnahme

Der nächste vollständige Lauf `backups/pr7-browser-v7.txt` bestand **27/27 in
5,0 Minuten ohne Skips**. `...-status.json` bestätigt den anschließenden
Normalmodus mit Testprovider/Rollen aus und Collection/Forward aus. Neue
gezielte Fälle prüfen Quellenladefehler/Retry ohne veraltete Freigabeanzeige,
sofortige Assistentenrückmeldung, sichtbare Laufzeit, Abbruch, Verlaufabruf und
einen ohne Abschlussbeleg endenden Antwortstrom. Der Entwurf bleibt bei
Abbruch/Transportfehler erhalten. Es wurden keine Modelltexte oder
Finanzwerte für diese Transporttests erfunden. Der bestehende DB-Test zur
serverseitigen Abbrucharchivierung gehört zum bestandenen301-Fall-Backendlauf.

Die zwei vorherigen Startversuche scheiterten unter Hostlast an
Start-/Health-Fristen; ihre Belege bleiben erhalten. Im erfolgreichen Lauf
wurde bis zu600s auf unveränderte gesunde Dienstzustände gewartet. Ollama war
für die kontrollierte Testprovider-Regressionsprüfung vorübergehend gestoppt.
Das ist keine neue native LLM-Latenzabnahme und kein Nachweis einer bestimmten
Ursache aller historischen Ladezeitschwankungen.

## Konkrete Abfragekorrektur und neue Messung

Header und Dashboard fragten `/notifications` mit unterschiedlichen Querykeys
zweimal ab. Beide verwenden jetzt dieselbe vollständige Antwort im bereits
pro angemeldetem Benutzer getrennten, beim Logout verworfenen QueryClient.
Der gezielte Browserfall verlangt genau einen initialen Dashboardabruf.
Im gemessenen Ablauf mit zusätzlichem vollständigem Portfolioseitenaufruf
sank die Gesamtzahl dieser GETs von3 auf2; die neue Dokumentnavigation benötigt
weiterhin ihren eigenen Abruf. Keine private Cachepersistenz hinzugefügt.

Der vollständige Lauf nach dieser Änderung bestand **27/27 in3,3 Minuten ohne
Skips** (`backups/pr7-browser-v9.txt`); Normalmodus anschließend verifiziert.
Der vorherige Lauf v8 hatte25/27 bestanden: ECONNRESET bei Instrumentanlage
und ein15s-Timeout bei einer bestehenden Abfrage während paralleler Scans.
Er wird nicht als grün behandelt. Der neue Lauf erfolgte ohne parallelen Scan.

| Messung | Login bis Positionen | Risikofunktion bis Antwort/Bedienbarkeit |
| --- | --- | --- |
| Warm1 nach Korrektur | 2188ms | 2006ms |
| Warm2 nach Korrektur | 1962ms | 715ms |
| Warm3 nach Korrektur | 1732ms | 836ms |
| Erster Aufruf nach API-/Web-Neustart | 2858ms | 923ms |

Neustart bis technische Bereitschaft:19’747ms. Browserkontext jeweils neu;
OS-/DB-Caches wurden nicht geleert. Risikodaten sind jeweils **PARTIAL**, keine
Abnahme vollständig versorgter Risikostatistiken. Belege:
`backups/pr7-performance-notifications/summary.json` samt Anfragezeiten.

Die vorherige Messreihe mit gleichzeitigem Securityscan ergab warme
Loginzeiten8095/3302/5576ms und Risk3048/1765/2766ms; erster Aufruf nach Neustart
4797/2221ms, technische Bereitschaft59’093ms. Quelle:
`backups/pr7-performance-synthetic/summary.json`. Andere Hostlast und Cachelage
verhindern eine kausale Zuordnung der Zeitdifferenz allein zur Codeänderung.
Direkt nachgewiesen ist die entfallene doppelte Dashboardabfrage. Die Shell,
Positionen und optionale Analysen bleiben getrennt fortschreitend sichtbar.

[Unabhängiger Anfängertest](ux/PR7_BEGINNER_TEST.md) vorbereitet:
**PENDING_USER_TEST**. Keine Testperson oder erfundene Erfolgs-/Zeitmessung.

## Zwischenstand am 27.10. vor dem abschließenden gemeinsamen Lauf

Der neue Webkandidat PR7rc6 besteht Lint, Typecheck und Standalone-Build.
Er bietet Drag-and-drop für eine unveränderte CSV-Datei, eine ausdrücklich
überprüfbare Erkennung der Standardspalten für Kurse/FX/Actions und verwirft
eine frühere Vorschau bei neuer Auswahl. Auswahlwechsel während Preview/Commit
sind gesperrt; ein abgeschlossenes Ergebnis kann nicht nochmals über denselben
Button übernommen werden. Erfolgreiche Übernahmen invalidieren aktive Abfragen.
Die bestehende Importengine bleibt verantwortlich für Mapping, Originalbytes,
Konflikte und Dubletten. Mehrere Instrumente mit unterschiedlichen FIGIs/MICs
werden im erweiterten echten Preview-/Commit-Browserfall geprüft; der neue
Gesamtlauf stand zu diesem Zeitpunkt noch aus. Der nachfolgende Abschlussabschnitt
enthält den neuen29/29-Pass; der alte27/27-v9-Pass wurde nicht darauf übertragen.

Die neue Assistentenanzeige unterscheidet laufende Modellverarbeitung von
strukturierter Ersatzantwort. Echter isolierter HTTPS-Lauf mit Ollama0.40.11:
erstes Ereignis2234ms, Abschluss samt archivierter Ersatzantwort126’575ms,
Status **LLM_UNAVAILABLE**, keine erfolgreiche native Antwort. Vorwärmen dauerte
separat56’305ms und verhinderte die anschließende120s-Überschreitung nicht.
Der frühere kalte Lauf unter paralleler Buildlast benötigte allein rund92s
zum Laden. Diese unterschiedlichen Lastfälle werden nicht als gleicher
Benchmark verglichen. Fehlgeschlagene Antworten bleiben unveränderlich im Archiv.

Darauf folgt der neue **PR7_COMPACT_LABEL_SELECTION_V1**: höchstens24 Belege,
6000 Kontextzeichen, Frage bis2000 Zeichen, Labels bis240 Zeichen; das Modell
sieht nur vorhandene Original-IDs, Labels und Fact Types. Werte, Originaltexte
und Herkunft werden vollständig serverseitig archiviert und gerendert.
Der native Selektor darf höchstens zwei IDs und zwei feste Erklärungsschlüssel
zurückgeben. Pflichtangaben zu fehlenden Grundlagen ergänzt weiterhin die
deterministische Orchestrierung vor der Ausgabe. Nicht sichtbare/erfundene IDs
und Budgetüberschreitungen werden abgewiesen. Neue Antworten pinnen den Vertrag;
alte Antworten und Modellmanifeste werden nicht umgeschrieben.21 gezielte
Auswahl-/P10-Tests bestehen; vollständige Backend- und erneute native Abnahme
laufen noch. Das feste120s-Limit wird nicht verlängert.

## Abschließender lokaler Lauf am 27.10.

**29/29 in4,0 Minuten ohne Skips** (`backups/pr7-browser-v10.txt`),
Normalmodus nachweislich wiederhergestellt. Die neuen CSV- und Assistenten-
Änderungen sind damit gemeinsam geprüft. Zusätzlich News-/Qualitäts-Lesefehler
per503 injiziert, Retry mit Enter ausgelöst und Datumfilter erhalten; keine
Finanzantworten erfunden. Nach Qualitätsladefehlern erscheinen keine alten
grünen Qualitätskarten. Aktuelle neue Builds: Backend PR7rc6, Web PR7rc7.

Native kompakte Auswahl besteht: vorgewärmt erstes Ereignis2064ms, gespeicherte
AVAILABLE-Antwort28’783ms; separates explizites Vorladen25’010ms. Mit gestopptem
Modell LLM_UNAVAILABLE samt gespeicherter strukturierter Antwort4249ms.
Frühere überschrittene120s-Läufe bleiben im Archiv; das Limit wird nicht
verlängert. Diese unterschiedlichen Kontext-/Lastfälle sind keine kontrollierte
allgemeine Beschleunigungsquote oder kalte Produktionszusage.

Der finale HTTPS-Browser meldet sich tatsächlich über dieselbe Origin am
Gateway an, rendert das frische synthetische Portfolio und prüft dessen aktuelle
COMPLETE-Bewertung10180. Keine Seitenfehler. Die eigene Test-CA wurde im
Browserkontext ausdrücklich als QA-Ausnahme zugelassen; separat bestand der
strikte Python-CA-Vertrag. OS-Client-CA und echter Zielhost bleiben offen.
Der ursprüngliche alte Goldenbestand ist heute korrekt STALE_PRICE/PARTIAL;
nur am belegten26.10.-Cutoff beträgt sein vollständiger Wert10180.

Die31-Routen-Smokes und29 Fachfälle sind keine Vollabnahme jeder Kombination
von Transport-, Rechte-, Eingabe- und Recoveryfehlern. Unabhängiger Menschentest
und reale Quelldaten fehlen. Die PARTIAL-Kennzeichnung wird dadurch nicht
pauschal auf WORKING angehoben.

Die [individuelle Nachprüfung aller bisherigen PARTIAL-Routen](ux/PR7_FUNCTIONAL_RECHECK.md)
ordnet primäre Backendwege, Zustandsverträge, vorhandene Fachfälle und verbleibende
Abnahmegrenzen zu. Der separate echte Anfängertest bleibt PENDING_USER_TEST.
