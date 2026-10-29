# PR9A – Backend-Runtime und native Paketpfade

Prüfdatum: **28.10.2026**. Technische Analyse, **keine Securityfreigabe**.

## Ausgangsbestand

Der unveränderte PR8-Bestand ist `private-iip/backend@sha256:610dd6f6821c86bcaf870680a8bc623ab7947875529b833605cbfc67140831a6`. API, Worker und Scheduler verwenden dasselbe Image. Seine [ursprüngliche Bestandsaufnahme](security/pr8-20261027/core-rc3/inventory.json) enthält **44 High-Zeilen, 17 Binärpakete, acht unterschiedliche CVEs**. Mehrfachzuordnungen desselben Quellpakets sind keine zusätzlichen unabhängigen Schwachstellen. Alle dort erfassten Trixie-Fixversionen sind nicht verfügbar; die Originalbelege bleiben unverändert.

| Quellpaket / CVE | Betroffene installierte Binärpakete | Installierte Version laut PR8 | Fix laut Debian, geprüft 28.10.2026 |
| --- | --- | --- | --- |
| util-linux / CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 | bsdutils, libblkid1, liblastlog2-2, libmount1, libsmartcols1, libuuid1, login, mount, util-linux | überwiegend `2.41.5-0+deb13u1`; bsdutils `1:2.41.5-0+deb13u1`, login `1:4.16.0-2+really2.41.5-0+deb13u1` | Trixie weiterhin betroffen; Sid/Forky behoben. Einzelne Fixstände unterscheiden sich je CVE. |
| acl / CVE-2026-54369 | libacl1 | `2.3.2-2+b1` | Trixie betroffen; `2.4.0-1` in Sid/Forky; zusätzliche ABI, keine ungetestete Einzelpatch-Mischung. |
| ncurses / CVE-2025-69720 | libncursesw6, libtinfo6, ncurses-base, ncurses-bin | `6.5+20250216-2` | Trixie betroffen; Debian nennt Fix `6.6+20251231-1` in Unstable. |
| systemd / CVE-2026-16742 | libsystemd0, libudev1 | `257.13-1~deb13u1` | Trixie betroffen; Debian nennt Fix `261.2-1` in Unstable. |
| perl / CVE-2026-9538 | perl-base | `5.40.1-6+deb13u1` | Trixie betroffen; Debian nennt Fix `5.42.3-1` in Unstable. |

Primärquellen: Debian zu [76642](https://security-tracker.debian.org/tracker/CVE-2026-76642), [78408](https://security-tracker.debian.org/tracker/CVE-2026-78408), [78409](https://security-tracker.debian.org/tracker/CVE-2026-78409), [78410](https://security-tracker.debian.org/tracker/CVE-2026-78410), [54369](https://security-tracker.debian.org/tracker/CVE-2026-54369), [69720](https://security-tracker.debian.org/tracker/CVE-2025-69720), [16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) und [9538](https://security-tracker.debian.org/tracker/CVE-2026-9538). Bookworm ist für diese Quellen ebenfalls betroffen; ein bloßer Wechsel auf Bookworm schließt diese Befunde nicht. Die externe Prüfung betraf Sicherheitsdokumentation, keine Finanzprovider.

## Konkreter Verwendungspfad und Entscheidung

| Komponente | Geprüfter Pfad / Exposition | Entscheidung im Runtime-Kandidaten |
| --- | --- | --- |
| util-linux | Die vier CVEs betreffen privilegierte Mount-/nsenter-Pfade, einschließlich fstab, Mount-Helfern, cgroup-FDs und SUID-Mount. API/Worker benötigen weder diese Werkzeuge noch deren Administrationsbibliotheken. Die optionale Python-Erweiterung `_uuid` bindet `libuuid.so.1`. | Administrationsprogramme und nicht verlinkte Bibliotheken entfallen. Das versionierte Coreprofil entfernt zusätzlich nur die optionale native `_uuid`-Erweiterung. `uuid4` und der reine Python-Fallback bleiben geprüft verfügbar; libuuid gehört dadurch nicht mehr zur ELF-Closure. Keine gescannte verbliebene Paketidentität wird unterdrückt. |
| acl | Betroffen sind pathname-basierte libacl-Funktionen in privilegierten Aufrufern. Kein Backend-Aufruf von setfacl/getfacl; weder Python-native ELF-Wurzeln noch deren aufgelöste Abhängigkeiten benötigen libacl. | Keine ACL-Werkzeuge/-Bibliothek im Kandidaten; kein erzwungenes Entfernen aus einem laufenden Debian-System. |
| ncurses | Debian beschreibt den Stackoverflow im CLI-Werkzeug `infocmp`. Die vollständige Python-Installation enthält `_curses`, `_curses_panel` und readline; deren native Bibliotheken bleiben benötigt. | Das versionierte nichtinteraktive Coreprofil entfernt `_curses`, `_curses_panel` und `readline` samt ihren gemessenen Quellhashes. Ohne verbleibende ELF-Abhängigkeit entfallen auch ncurses-Bibliotheken und Terminfo. Das Web-/API-/Workerprodukt verspricht keine TUI oder interaktive Shell. |
| systemd | Debian beschreibt systemd-homed und verwaltete lokale Benutzer. Kein systemd-/homed-Dienst im Container; keine native Backend-Abhängigkeit auf libsystemd/libudev. | Beide Bibliotheken und Dienstwerkzeuge entfallen aus dem neu zusammengestellten Dateisystem. |
| perl | Der Pfad ist Perl Archive::Tar und ein übergroßes attacker-kontrolliertes Tar-Feld. Das Backend verwendet Python und den vorhandenen begrenzten PDF-Unterprozess; kein Perl-Aufruf im Anwendungscode. | Perl-Interpreter und Module entfallen. Die bestehenden Python-Archivgrenzen und Trust-Gates bleiben zusätzlich erforderlich. |

Diese Pfadanalyse begrenzt bestimmte Expositionen. Sie erzeugt **keine automatische Nichtbetroffenheits- oder Ausnahmeentscheidung** für weiterhin erkannte Pakete, native Modelle oder andere Angriffspfade.

## Aufbau des Kandidaten

[Dockerfile.pr9](../ops/backend/Dockerfile.pr9) baut in zwei Stufen. Die erste verwendet ausschließlich das vorhandene exakte PR8-Python-3.12.15-/Trixie-Image und aktuelle Backend-Dateien. [assemble_runtime.py](../ops/backend/assemble_runtime.py) prüft vor dem Kopieren alle Versionen aus `requirements.lock` und `requirements-assistant.lock` sowie `pip check`. Es gibt keine numerische Migration, Paketaktualisierung, Sid-Quelle oder erzwungene apt-Entfernung.

Die finale Scratch-Stufe erhält die unveränderten 66 gesperrten Core-/Supportdistributionen und Python mit dem expliziten Profil **IIP_CORE_NONINTERACTIVE_V1**. Genau fünf optionale Standardbibliothek-Erweiterungen (`_curses`, `_curses_panel`, `readline`, `_uuid`, `_tkinter`) entfallen; ihre ursprünglichen Dateihashes werden aufgezeichnet. Keine numerische Erweiterung wird entfernt. Sämtliche verbliebenen ELF-Dateien werden über ihre gemessene `ldd`-Closure aufgelöst. Hinzu kommen NSS-Konfiguration/-Module, TLS-CA, Zeitzonen, C.UTF-8-Locale, ausgewählte ursprüngliche Debian-Paketmetadaten und Copyrightdateien. Die Metadaten kennzeichnen ausdrücklich eine Auswahl ursprünglicher Paketdateien, keine vollständige dpkg-Installation. Identitäten verbliebener Bibliotheken bleiben für Scanner sichtbar; sie werden nicht zur Befundunterdrückung entfernt oder umbenannt.

Shell, apt/dpkg, Perl, mount/nsenter und systemd gehören nicht zum finalen Dateisystem. API/Worker/Beat starten direkt ihre Python-Programme. Ein geänderter Scheduler-Healthcheck muss deshalb ebenfalls direkt Python ausführen. `/tmp` kommt zur Laufzeit aus dem bestehenden begrenzten Tmpfs; Benutzer ist UID/GID 10001, die Root-Dateisysteme bleiben read-only und Fähigkeiten entfallen wie im bisherigen Core-Profil.

Die ursprüngliche Python-slim-Installation enthält `_tkinter` ohne Tcl/Tk. Das Coreprofil bietet keine Desktop-GUI und entfernt diese optionale Erweiterung ausdrücklich. Jede verbliebene unerklärte native Fehlauflösung bricht den Build ab. UUID4-Kollisions-/Versionsprobe und UUID1-Pythonfallback wurden separat geprüft; stabile Ledger-IDs verwenden UUID4.

[build_candidate.py](../ops/backend/build_candidate.py) prüft die tatsächliche ID des lokal archivierten Quellimages und verwendet eine eigene lokale Build-Aliasreferenz. So wird kein ungeprüftes Registry-Image nachgeladen, wenn BuildKit eine lokal synthetisierte RepoDigest-Referenz nicht auflösen kann. Die Fehlversuche bleiben erhalten; der Buildbeleg enthält Quell-ID, Eingabehashes und neue Kandidaten-ID.

## Abnahmekriterien und noch notwendige Nachweise

- Jeder erzeugte Kandidat benötigt einen eigenen frischen Scan, formal validierte SBOM und exakten Inventareintrag. Ein erfolgreicher Build ist kein Scan.
- [probe_runtime.py](../ops/backend/probe_runtime.py) prüft unter `--network none`, read-only, UID10001 und begrenztem Tmpfs die unveränderten nativen Hashes, Lockversionen, `pip check`, TLS-Trust, lokale NSS-Auflösung, Zeitzonen, Argon2id und kleine ausschließlich synthetische NumPy-/SciPy-/Ridge-/LightGBM-/XGBoost-Ausführungen.
- Die vollständige Backend-, Browser-, Migration-/Schema- und isolierte Restore-Abnahme bleibt für das geänderte Image erforderlich. Ein Offline-Smoke ersetzt diese Regression nicht.
- Ein statischer oder dynamischer Legacy-Verifikationsweg wird gesondert bewertet. Dieser neue Backend-Kandidat behauptet niemals, dieselbe historische Runtime zu sein.
- Verbleibende High-/Critical-Befunde und zusätzliche manuelle Reviews bleiben nach unveränderter Security-Policy gesperrt, bis ein tatsächlich autorisierter Review vorliegt.

Die finalen Kandidaten-, Scan- und Regressionsergebnisse werden im [PR9A-Sicherheitsbericht](PR9A_SECURITY_CLOSURE_REPORT.md) zusammengeführt. Dieser technische Einzelreview erteilt keine Operatorfreigabe.

## Tatsächlicher finaler Kandidat

`private-iip/backend@sha256:5a925e0ea0bfffabeda6ee735f60db9d0235b3ab149b059984f9150cf0d21667` hat den Offline-Nativ-/Lock-/NSS-/TLS-/Numerikprobe und **alle 306 Backendtests** bestanden. Die Tests liefen im exakten unprivilegierten read-only Produktionsimage mit separatem read-only Pytest-Werkzeugmount. Keine Core-/Supportdistribution wurde durch Testwerkzeuge überschattet; alle 66 Versionen blieben danach unverändert.

Der frische Scan mit Datenbank vom 28.10.2026 meldet **0 Critical, 0 High, 42 Medium, 19 Low und 2 Unknown**. Das ist eine gemessene Reduktion der 44 ursprünglichen High-Zeilen, keine Freigabe aller nativen Pfade. [Finales Inventar und Original-SBOMs](security/pr9-20261028/core-rc1/inventory.json). Kandidat 4 behielt die optionalen TUI-/UUID-Pfade und hatte noch sieben High-Zeilen; seine Belege bleiben als Zwischenversuch erhalten und werden nicht umgeschrieben.

Der normale `backend/Dockerfile`-Produktionspfad verwendet nun denselben gemessenen Assembler auf der gepinnten offiziellen Python-/Trixie-Basis. Damit kann auch ein frischer CI-Build die Reduktion anwenden. Er ist ein eigener Build mit eigener Scan-/Regressionspflicht; er wird niemals als bitidentisch zum aus archivierten PR8-Wheelbytes gebauten Core-Digest ausgegeben. Der Dev-Target bleibt für Ruff/Mypy/Pytest verfügbar. Scheduler- und optionale ML-Healthchecks benötigen keine Shell mehr. [Gesamtabnahme](PR9E_RELEASE_CANDIDATE_REPORT.md) bindet die tatsächlichen getrennten Nachweise.
