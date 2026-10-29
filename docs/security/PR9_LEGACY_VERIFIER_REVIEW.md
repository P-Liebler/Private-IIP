# PR9 – Legacy-Verifier: statische Alternative und vorbereiteter Ausnahmeentscheid

Technischer Reviewstand: **28.10.2026**. **DRAFT_NOT_APPROVED / SECURITY_BLOCKED**. Dieses Dokument erteilt keine Ausnahme, keinen Produktionsstart und keine Modellfreigabe. Die erforderliche Recovery-Komponente bleibt im vollständigen Core-Scope enthalten.

## Exakte Komponente und bisheriger Befund

| Feld | Gebundener Nachweis |
| --- | --- |
| Komponente / Rolle | `legacy-verifier`, erforderlicher Recovery-Vertrag, kein normaler API-/Worker-Dienst |
| Image | `private-iip/backend@sha256:acb9d2027e8925f756ccd7d1a22e1fae989c0db3bf8bf486400e0bc963e21816` |
| Unveränderter PR8-Beleg | [Core-RC3-Inventar](pr8-20261027/core-rc3/inventory.json), SHA-256 `05f78966eab269dd4712694cb9a69cc3ad6cadf9f563bca1d3256bae69219522` |
| Original-SBOM | [legacy-verifier.cdx.json](pr8-20261027/core-rc3/legacy-verifier.cdx.json), SHA-256 `0dbc717f85f8fc74e6f5ac7b46aea68d3d6912600f43828860485cd0eb68963d` |
| Gebundener ursprünglicher Scan-Hash | `7b6914162ef5af6b0dfe0b7b19ffe52a8142284de5fef36ac68d86e8f5a765bf` |
| PR8-Paketbefunde | **1 Critical, 47 High**, zusätzlich 69 Medium, 63 Low und 4 Unknown; keine automatische Ausnahme |
| Datenbankstand dieses historischen Belegs | `2026-10-27T07:13:33.504287223Z`; der Beleg wurde am 27.10.2026 veröffentlicht. Ein aktueller Release braucht seinen eigenen frischen Scan. |

Die Zahlen beschreiben dieses exakte alte Image und diesen Beleg. Ein neuer Scan kann zusätzliche oder anders bewertete Befunde enthalten. Weder statische Metadatenprüfung noch ein neuer API-Build ändern die alten Bytes, installierten Pins oder ursprünglichen Befunde. Ein neuer certifi-Pin darf nicht als identische historische Runtime ausgegeben werden.

## Option A – Statische Prüfung unter aktueller Host-Runtime

[`ops/verify_archive_metadata.py`](../../ops/verify_archive_metadata.py) ergänzt den bisherigen Vertrag:

1. Der vorliegende Archivumschlag wird begrenzt gelesen; sein Base64-Artefakt muss zum enthaltenen erwarteten SHA-256 passen. Artefakt-, Konfigurations- und Training-Code-Metadaten müssen übereinstimmen.
2. Source-Image muss digestgebunden sein. Das tatsächlich lokal inspizierte Image muss dieselbe ID haben; Tagersatz oder stiller Image-Neubau sind unzulässig.
3. Die Auswahl der Metadatenpfade stammt aus dem **hashgeprüften Original-SBOM** dieses Images. Gelesen werden ausschließlich die beiden Lockdateien und begrenzte reguläre `.dist-info/METADATA`-Dateien. Links, fehlende, doppelte und widersprüchliche Distributionsdaten werden verworfen.
4. `docker create` erzeugt einen **niemals gestarteten** Container. `docker cp` liest die exakt zugelassenen Dateien; anschließend wird dieser Container entfernt. Das Image wird dabei weder gestartet noch als Python-/Shell-/Providerprozess ausgeführt. Die neue Prüfung importiert keine archivierten Packages und entpackt kein Archiv in das Hostdateisystem.
5. Der aktuelle Host-Parser vergleicht die historischen Lockbytes mit dem Archivvertrag und jede aufgeführte installierte Paketversion. Originale, Modellmanifeste und historische Ergebniszeilen werden nicht verändert.

Die neue Prüfung bestätigt nur den Vergleich mit dem **übergebenen, vertrauenswürdig beschafften Archivumschlag**. Ein frei konstruierter Umschlag mit neu berechnetem Hash beweist keine historische Herkunft. Der Operator muss daher die Umschlagherkunft, den bestehenden Modell-/Archivbezug und dessen unveränderten erwarteten Hash aus dem vorhandenen Archivnachweis sichern. Ein Hash allein authentisiert keinen Herausgeber.

Der [finale tatsächliche statische Lauf](pr9-20261028/static-archive-metadata-final.json) prüft den bereits vorhandenen Archivumschlag, **66 installierte Pins** und den ursprünglichen SBOMvertrag erfolgreich. Er bindet den finalen Verifierhash `57ad92ffa32391ac63ee567e5270e4a3ffda95f8ab1b12fc89c533ba2d932a08`, `--pull never`, sichere Komponenten-Dateinamen und die 64-MiB-Gesamtgrenze mit begrenzter Vierer-Verarbeitung. Der [frühere Zwischenlauf](pr9-20261028/static-archive-metadata.json) bleibt unverändert erhalten. In beiden Fällen wurde das alte Image **nicht gestartet**, kein archiviertes Paket importiert und keine historische Ausführungsreproduzierbarkeit behauptet.

| Aussage | Neue statische Prüfung | Bisheriger isolierter Verifier |
| --- | --- | --- |
| Artefaktbytes passen zum erwarteten Archivhash | Ja, innerhalb des gebundenen Eingabevertrags | Ja |
| Archivierte Trainings-/Konfigurationsmetadaten passen | Ja | Ja |
| Historische Lockbytes und installierte Distributionsversionen passen | Ja, aus SBOM-gebundenen Dateien gelesen | Ja, innerhalb des alten Python mit `importlib.metadata` gelesen |
| Alte Python-Runtime startet und führt den bestehenden Prüfcode aus | **Nicht ausgeführt, nicht bewiesen** | Auf den begrenzten Verifiercode beschränkt nachweisbar |
| Historisches Training oder Inferenz numerisch reproduziert | **Nicht ausgeführt, nicht bewiesen** | Auch der bisherige reine Vertragsprüfer führt keine vollständige ML-Trainings-/Inferenzreproduktion aus |
| Finanzielle Prognosegüte, OOS-Validierung oder P9-Freigabe | Nein | Nein |
| Security-/Operatorfreigabe | Nein | Nein |

Damit ist ein sichererer Vorprüfpfad vorhanden. Er ersetzt den **aktuell weiterhin erforderlichen exakten Recovery-Runtime-Vertrag nicht automatisch**. Eine spätere normative Ersetzung braucht einen gesonderten Architektur-/Kompatibilitätsentscheid mit aktualisierten Abnahmeverträgen; sie darf keine historische Ausführung als bestanden markieren.

### Vorbereiteter Aufruf

```powershell
python ops/verify_archive_metadata.py --image private-iip/backend@sha256:acb9d2027e8925f756ccd7d1a22e1fae989c0db3bf8bf486400e0bc963e21816 --envelope backups/VERTRAUENSWUERDIGER-EXISTIERENDER-UMSCHLAG.json --workdir backups --inventory docs/security/pr8-20261027/core-rc3/inventory.json --output backups/NEUER-STATISCHER-NACHWEIS.json
```

Die privaten Pfade müssen tatsächlich existieren und die Ausgabe darf noch nicht bestehen. Dies ist kein Aufruf zur Produktionswiederherstellung. Das Tool besitzt lokale Docker-Operatorrechte; ein niemals gestartetes altes Image beseitigt weder Host-/Docker-/Parserrisiken noch die Pflicht, eine aktuelle vertrauenswürdige Host-Runtime zu verwenden. `historical_image_started=false`, `historical_execution_reproducibility=NOT_EXECUTED_NOT_PROVEN`, `replaces_required_legacy_runtime_check=false` und `security_approval=false` bleiben im Ergebnis ausdrücklich erhalten.

## Option B – Begrenzten isolierten Ausnahmeentscheid vorbereiten

**Keine Ausnahme ist genehmigt.** Gegenstand eines möglichen Entscheids ist ausschließlich das oben gebundene Recovery-Image mit dem unveränderten [`ops/verify_legacy_model.py`](../../ops/verify_legacy_model.py). Keine allgemeine Zulassung des alten Images als API, Worker, Scheduler, MLflow oder Providerclient.

### Critical: konkrete Primärprüfung

Der installierte Pin `certifi==2026.7.22` ist vom **GHSA-6q48-6c7w-9gw2** betroffen; der Scanner nennt `2026.10.18` als gepatchte Version. Das [Maintainer-Advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2), am 28.10.2026 gelesen, beschreibt die Entfernung von emSign-Wurzeln nach kompromittierten beziehungsweise widerrufenen Zwischenzertifikaten und das daraus mögliche TLS-MITM-Risiko. Es ist als Critical eingestuft und nennt **keine bekannte CVE-ID**; die GHSA-ID darf nicht durch eine erfundene CVE ersetzt werden.

**Erreichbarkeit in diesem konkreten Prüfpfad:** Der bestehende Prüfcode verwendet Hash-, Base64-, JSON-, Dateizugriff und `importlib.metadata`. Er importiert weder certifi noch einen TLS-/HTTP-Client und öffnet keine Verbindung. Netzwerk ist auf Containerseite `none`. Daraus folgt eine technische Begründung, dass der dokumentierte TLS-MITM-Pfad in genau diesem beschränkten Prüfvorgang keine vorgesehene Ausführungsstrecke besitzt. Das ist eine Code-/Konfigurationsinferenz, **kein Exploitnachweis, kein Patch und keine automatisch akzeptierte Nichtbetroffenheit**. Ein anderes Entry-Point, zusätzlicher Import oder Netzwerkzugang würde diese Begründung entkräften.

### Ausführung und Schutzmaßnahmen, die ein Reviewer prüfen muss

Der vorhandene Runner setzt bereits:

- Digestpin, `--pull never`, kein Tagersatz;
- `--network none`, keine veröffentlichten Ports, keine Host-/VPN-Verbindung;
- unveränderliches Rootdateisystem, unprivilegierten Benutzer `10001:10001`, `cap-drop ALL`, `no-new-privileges`;
- keine Hostmounts, keinen Docker-Socket und keine vom Host übergebenen Produktivsecrets;
- begrenzte Eingabe über stdin, keine ausführbaren Modellformate und keine Provider-/Anwendungsimporte;
- `python -I -B` mit festem Standardbibliothek-Prüfcode;
- 512 MiB RAM, 1 CPU, 32 PIDs, 16 MiB `noexec,nosuid`-tmpfs und 90 Sekunden Prozess-Timeout;
- automatische Containerentfernung und einen begrenzten Ergebnisumfang ohne Druck der privaten Modellbytes.

Diese Maßnahmen müssen am tatsächlichen Zielhost/Restoreaufruf nachgewiesen werden. Das alte Python und die libc bleiben beim dynamischen Vertragsprüfer tatsächlich aktiv. Containerisolation beseitigt keine Kernel-/Docker-/Parserfehler. Auch bei fehlender Netzwerkexposition darf Paketpräsenz nicht ohne weiteren Review als ungefährlich abgelegt werden.

### Noch unbewertete High-Befunde

Die **47 High-Paketbefunde** bleiben unverändert offen. Die folgende Gruppierung ist ein Index des gebundenen Inventars, keine pauschale Exploitability-Freigabe. Fixangaben sind dessen damaliger Stand; `nicht angegeben` bedeutet keinen nachgewiesenen sicheren Paketstand.

| Paketgruppe / installierte Versionen | IDs im Inventar | Zahl High | Reviewgrenze |
| --- | --- | --- | --- |
| util-linux-Familie: `bsdutils` 1:2.41.5-0+deb13u1; `libblkid1`, `liblastlog2-2`, `libmount1`, `libsmartcols1`, `libuuid1`, `mount`, `util-linux` 2.41.5-0+deb13u1; `login` 1:4.16.0-2+really2.41.5-0+deb13u1 | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 je betroffenem Binärpaket | 36 | Kein Mount-/Loginwerkzeug im festgelegten Prüfcode vorgesehen; Bibliotheks-/Abhängigkeits- und Hostgrenzen trotzdem einzeln prüfen. Fix im Beleg nicht angegeben. |
| `libacl1` 2.3.2-2+b1 | CVE-2026-54369 | 1 | Kein ACL-Werkzeug vorgesehen; tatsächliche Bibliotheksreichweite nicht pauschal ausgeschlossen. Fix nicht angegeben. |
| `libncursesw6`, `libtinfo6`, `ncurses-base`, `ncurses-bin` 6.5+20250216-2 | CVE-2025-69720 je Paket | 4 | Kein interaktives Terminal im Runner; nicht als allgemeine Nichtbetroffenheit ausgegeben. Fix nicht angegeben. |
| `libsystemd0`, `libudev1` 257.13-1~deb13u1 | CVE-2026-16742 je Paket | 2 | Keine systemd-/udev-Dienste gestartet; möglicher Bibliothekspfad ist gesondert zu prüfen. Fix nicht angegeben. |
| `perl-base` 5.40.1-6+deb13u1 | CVE-2026-9538 | 1 | Kein Perlprozess vorgesehen. Keine vollständige native Reachability-Abnahme. Fix nicht angegeben. |
| `pypdf` 6.20.1 | CVE-2026-115572, CVE-2026-115580, CVE-2026-115585 | 3 | Kein PDF-Parsing und kein pypdf-Import im Verifier. Im Beleg Fix 6.21.2; Patch würde den historischen Paketvertrag ändern. |

Jede eventuell gewünschte Ausnahme muss **pro Finding, Komponente und Digest** den tatsächlichen Aufruf, Primärbeleg, technische Reachability, Schutzmaßnahmen und Restgefahr referenzieren. Die Critical-Ausnahme würde die übrigen High-Befunde nicht automatisch genehmigen. Das vollständige aktuelle Inventar bleibt Pflicht, einschließlich aller erforderlichen Recovery-Images.

### Vorgeschlagene Dauer, Review und fehlende Entscheidung

| Feld | Vorbereiteter Vorschlag / tatsächlicher Zustand |
| --- | --- |
| Zweck | Ein vorab benannter isolierter Archiv-/Restore-Vertragscheck; keine dauerhafte Anwendungsausführung. |
| Technisch notwendige Dauer | Maximal 90 Sekunden je vorhandenem Umschlagaufruf. Anzahl der tatsächlichen Umschläge und maximale Gesamtdauer vor dem Entscheid im Restoreplan festhalten. |
| Zeitliche Begrenzung eines möglichen Entscheids | Vorschlag: eine konkret terminierte Restoreprobe innerhalb höchstens 7 Tagen nach realer Freigabe, Betriebsfenster höchstens 24 Stunden. Das sind vorgeschlagene Grenzen, keine erteilte Gültigkeit. |
| Reviewer / Autorisierung | **OFFEN – keine reale Security-/Operatorfreigabe liegt diesem Dokument bei.** |
| `approved_at`, `expires_at`, Approval-Referenz | **NICHT ERTEILT.** Keine fingierten Personen, Termine oder Signaturen. |
| Re-Review-Trigger | Vor jedem neuen Restore; neues Finding/Advisory/DB-Ergebnis; geänderter Image-/Verifier-/Archiv-/Konfigurationshash; neue Packages/Imports; Netzwerk, Mounts, Benutzer, Ressourcen oder sonstige Schutzmaßnahmen ändern sich; andere Host-/Docker-/Kernelversion. |
| Ablauf / Widerruf | Nach dem benannten Vorgang oder spätestens am tatsächlich erteilten Ablaufdatum wieder sperren; Wiederverwendung braucht einen neuen überprüfbaren Entscheid. |
| Restgefahr | Alte Runtime und native Bibliotheken, Parser-/Container-/Hostgrenzen sowie noch nicht einzeln bewertete High-Befunde. Keine Aussage, dass ein Exploit unmöglich wäre. |

Die Policy in `ops/security_policy.py` verlangt echte Reviewer-/Approval-/Zeit-/Reachability-Felder und erlaubt keine unbegrenzte Ausnahme. Dieses Dokument ist absichtlich **kein gültiger Ausnahmeeintrag** und wird nicht in eine genehmigte Exceptionliste geschrieben. Bis vollständiger frischer Evidenz und tatsächlicher Entscheidung bleiben **LEGACY_VERIFIER_STATUS=SECURITY_BLOCKED** und der Private-Core-Release **NOT_RELEASED**.

## Fokussierte Tests

**10 Offline-Fixturetests bestanden** (`python -m unittest ops.tests.test_archive_metadata -v`): Archivhash, tatsächliche installierte Pins, unveränderte Aussagegrenzen, reguläre Lockdateien, Tagverbot vor Docker, SBOM-Bytebindung vor Docker, Digest-/Mehrdeutigkeitsprüfung, fehlende Metadaten, begrenzter benachbarter SBOMpfad und Ausschluss von Package-Code. Tests führen keinen alten Container und keinen Provider aus. Ein tatsächlicher statischer Lauf und die erforderliche isolierte Wiederherstellung müssen mit ihren eigenen exakten Ergebnisdateien im PR9-Gesamtbericht referenziert werden; Unit-Tests ersetzen diese Evidenz nicht.
