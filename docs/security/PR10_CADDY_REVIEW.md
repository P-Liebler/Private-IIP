# PR10A3 – Caddy: Importkette, JWK-Pfade und Securityentscheidung

Prüfdatum: **29.10.2026**. Status: **TECHNICALLY_REVIEWED / DRAFT_NOT_APPROVED / SECURITY_BLOCKED**.

## Ergebnis

Für **CVE-2026-116587 / GHSA-mgcc-cww5-fp2q** ist weiterhin kein unterstützter
`go-jose/v3`-Fix veröffentlicht. Der aktuelle Core-Proxy aktiviert keinen
ACME-Server und keinen On-Demand-Issuer. Die betroffene Bibliothek bleibt jedoch
in der Binary und wird über die für `tls internal` benötigte Smallstep-PKI
eingebunden. Eine sichere Entfernung durch bloßes Abwählen des optionalen
ACME-Servermoduls ist damit nicht nachgewiesen. Keine Ausnahme wurde erteilt.

## Exakter Bezug und neue Belege

| Bezug | Wert |
| --- | --- |
| Image / lokale Image-ID | `private-iip/caddy@sha256:6416b8c2e10d8d62b131dbf3755c01069d7b3dcdb7af720b76c8aeed8bc9dcaf` |
| Dienste | `caddy`, einmaliger `ca-export`, einmaliger `storage-init` |
| Caddy-Quellcommit | `72dd0fb067f6d7826c7f79907670ba4a713bfe37` / v2.11.7 |
| Build | Go 1.27.3, `go-jose/v3` v3.0.5, separate `go-jose/v4` v4.1.6 |
| PR9-Core-Caddyfile | SHA-256 `4afa7786bd3eb3f9764915e3a9f48deefb812375c57463a74dcb1020fc5c8f0a` |
| Gehärtetes PR10-Core-Caddyfile | SHA-256 `2fc6df71c4b79b45f0ccd58a38a2bfb0e0af561a3961f3e9c8b2c73a0a2a236c` |
| Neue Offline-Probe | `build-info`, `list-modules`, je ein `adapt` für Core und OpenShift, kein Serverstart, Netzwerk `none`, read-only Root, UID 10001 |

Die [signierte Upstream-Releaseansicht](https://github.com/caddyserver/caddy/releases/tag/v2.11.7)
und die [Source- und Dateihashes](pr10-20261029/caddy-profile/source-review.json)
binden den untersuchten Quellstand. Die erste [Profilprobe der PR9-Konfiguration](pr10-20261029/caddy-profile/receipt.json)
bleibt erhalten. Die [finale PR10-Profilprobe](pr10-20261029/caddy-profile-hardened/receipt.json)
bindet dieselbe Binary und die gehärtete Core-/OpenShift-Konfiguration.
[Build-Info](pr10-20261029/caddy-profile/build-info.txt),
[registrierte Module](pr10-20261029/caddy-profile/modules.txt) und
[adaptierte PR9-JSON-Konfiguration](pr10-20261029/caddy-profile/adapted.json)
sind getrennt erhalten. Die synthetische Domain `private-iip.invalid` dient
ausschließlich der Offline-Konfigurationsauflösung.

Die PR9-Scans bleiben Originalbelege vom **28.10.2026**: 0 Critical, 1 High,
1 Medium, 1 Unknown für dieses Image. Die neue Quellprüfung ist kein neuer
Paket- oder nativer Scan. Der [PR9-Befund](PR9_CADDY_REVIEW.md) bleibt unverändert;
der abschließende PR10-Scope besitzt jetzt eigene aktuelle
[Scanner-/SBOM-Belege](pr10-20261029/core-rc1/inventory.json):
**0 Critical, 1 High, 3 Medium, 1 Unknown**, Scanner-DB vom 29.10.2026.
Der verbleibende High-Befund ist weiterhin ein Releaseblocker. Die ergänzende
[vollständige Coreprüfung](pr10-20261029/core-staging.json) und beide getrennten
Restores sind erfolgreich; sie erteilen keine Securityfreigabe.

## 1. Aktueller Upstream-Stand

Das [Maintainer-Advisory](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q)
führt v3 bis einschließlich 3.0.5 ohne gepatchte Version und v4 bis 4.1.5 mit
Fix 4.1.6 auf. Ursache ist eine kostspielige RSA-Privatschlüsselvalidierung
beim Parsen präparierter JWK-Parameter unter Go ab 1.24. Der Parser kann diese
Arbeit bereits vor einer erfolgreichen Signaturprüfung ausführen. Ein
fehlgeschlagener Authentifizierungsversuch schützt diesen Parser daher nicht.

Die am 29.10.2026 erneut abgefragten offiziellen Tags enthalten als jüngsten
v3-Tag weiterhin 3.0.5. Smallstep Certificates bleibt bei
[v0.30.2](https://github.com/smallstep/certificates/releases/tag/v0.30.2).
Die neue [Crypto-Version 0.91.1 vom 27.10.2026](https://github.com/smallstep/crypto/releases/tag/v0.91.1)
behebt Signer-Options-Verhalten; ihr [Modulmanifest](https://github.com/smallstep/crypto/blob/v0.91.1/go.mod)
verlangt weiterhin `go-jose/v3` 3.0.5. Ein pauschales Smallstep-Update schließt
diesen Befund somit nicht.

Der [v4.1.6-Parser](https://github.com/go-jose/go-jose/blob/v4.1.6/jwk.go)
begrenzt die RSA-Modulusgröße und prüft die Beziehung der Primfaktoren vor der
teuren Validierung. Ein entsprechender lokaler v3-Backport wäre ein eigener
Kryptografie-Fork mit vollständiger Prüfung seiner öffentlichen/privaten
RSA-, JWS-, JWE- und JWT-Verträge. Er wurde hier nicht gebaut oder als
gepatchter Upstream-Release ausgegeben. Ein Scanner würde unverändert
deklarierte v3.0.5 weiterhin melden; eine erfundene Versionsnummer oder
Unterdrückung des Befundes wäre keine Behebung.

## 2. Tatsächliche Import- und Aufrufstrecke

```text
cmd/caddy/main.go
  → modules/standard
    → modules/caddytls (InternalIssuer)
      → modules/caddypki
        → smallstep/certificates/authority + authority/provisioner
          → go.step.sm/crypto/jose
            → github.com/go-jose/go-jose/v3 (+ /jwt, /cryptosigner)

standard → modules/caddypki/acmeserver
  → smallstep/certificates/acme/api → crypto/jose → go-jose/v3
```

Diese Kette ist an den ausgewählten Originaldateien im Source-Beleg
nachvollziehbar; sie ist eine Quell-Importprüfung, kein `govulncheck`-Beweis
vollständiger Laufzeitnichterreichbarkeit.

Der [interne Issuer](https://github.com/caddyserver/caddy/blob/v2.11.7/modules/caddytls/internalissuer.go)
bezieht die PKI-App und ruft `CA.NewAuthority` sowie `SignWithContext` auf.
Die [PKI-Implementierung](https://github.com/caddyserver/caddy/blob/v2.11.7/modules/caddypki/ca.go)
erstellt hierzu eine eingebettete Smallstep-Authority mit vorhandenem
Root-/Intermediate-Signer. Das ist lokale X.509-Zertifikatsausstellung aus
einem CSR; der untersuchte Aufruf übergibt keinen externen JWK-/JWT-String.
Gleichzeitig bindet das Authority-/Provisioner-Paket die JOSE-Funktionen ein.

Der [Smallstep-Wrapper](https://github.com/smallstep/crypto/blob/v0.91.0/jose/types.go)
delegiert JWS/JWT/JWE-Parsing an v3. Die
[v3-Headeraufbereitung](https://github.com/go-jose/go-jose/blob/v3.0.5/shared.go)
deserialisiert eingebettete JWK-Header. Der
[v3-JWK-Parser](https://github.com/go-jose/go-jose/blob/v3.0.5/jwk.go)
ruft bei privaten RSA-Parametern ohne die v4.1.6-Grenzen die RSA-Validierung
auf. Der bereits aktualisierte v4-Paketpfad ersetzt diese v3-Typen und
Parserfunktionen nicht.

## 3. JWK-Eingänge und aktuelle Erreichbarkeit

| Eingang | Konkreter Pfad / heutiger Stand |
| --- | --- |
| Optionaler ACME-Server | Die Standardbinary registriert `http.handlers.acme_server`. Bei Aktivierung leitet er ACME-Anfragen an Smallstep weiter. Dessen [Middleware](https://github.com/smallstep/certificates/blob/v0.30.2/acme/api/middleware.go) parst den Requestbody mit `jose.ParseJWS`, bevor JWS-/Account-Prüfung abgeschlossen sind. Präparierte JWK-Header sind hier eine relevante DoS-Fläche. **Im aktuellen Coreprofil nicht konfiguriert.** |
| Öffentlicher Core-HTTP-Proxy | Aktiv sind nur Header/Kompression, statische Antworten und Reverse Proxy zu `api:8000`, `web:3000`, `minio:9000`. HTTP-Requestbodies und ein beliebiger Pfad `/acme/...` aktivieren für sich keinen Caddy-ACME-Server. Die in PR10 korrigierte exklusive Route beantwortet `/internal/*` vor dem allgemeinen Frontendproxy mit 404; die frühere Sortierungsabweichung ist unten dokumentiert. |
| Interne CA / TLS | Die automatische interne Ausstellung verarbeitet lokal erzeugte CSRs. Ein TLS-Handshake oder HTTP-Authorization-Header wird in dieser untersuchten Strecke nicht als JOSE-JWK an Smallstep übergeben. Dies begrenzt die belegte Exposition; es beweist keine Abwesenheit jedes unbekannten Aufrufpfads. |
| Admin-API | Die unveränderte Compose-Konfiguration benutzt den Caddy-Default `localhost:2019`; kein Host-Port 2019 ist veröffentlicht. Der [PKI-Adminhandler](https://github.com/caddyserver/caddy/blob/v2.11.7/modules/caddypki/adminapi.go) liefert CA-Informationen/Zertifikate per GET. Schreibzugriff auf die allgemeine Admin-API oder die Konfigurationsdatei könnte weitere Module aktivieren und verlangt sofortigen Re-Review. OpenShift setzt getrennt `admin off`. |
| CA-Export / Storage-Init | Führen Shell-Dateioperationen aus, starten keine Caddyserver-Binary. Sie bleiben mit demselben vollständigen Image im Securityinventar. Storage-Init hat für die einmalige Volumevorbereitung UID 0 und `CHOWN`, Netzwerk `none`. |

Die Profilprobe verwirft einen hinzugefügten ACME-Handler, On-Demand-Modus,
anderen Issuer, fremde Upstreams oder entfernte Adminbindung. Sechs gezielte
Tests sowie drei Routing-/Transportregressionen bestanden (insgesamt neun).
Das Werkzeug erteilt bei Erfolg ausdrücklich keine
Securityfreigabe. Es startet keinen Angriffstest und erzeugt keine
übermäßig rechenintensiven RSA-Parameter.

## 4. Entfernung, Ablösung und Betriebsfolgen

| Alternative | Bewertung |
| --- | --- |
| Nur `acme_server` aus einem eigenen Main entfernen | Verringert registrierte optionale Eingänge; `tls internal` bindet weiter Smallstep/JOSE ein. Kein belegter Paketfix; unnötiger neuer Binary-/Scanumfang ohne Blockerabschluss. |
| Vollständige Smallstep-/PKI-Entfernung | Bricht die bestehende automatische interne CA, Leaf-Erneuerung, Root-Export und S3-TLS-/Backup-Vertrauensstrecke. Kein sicherer kleiner PR10-Patch. |
| v3 per Modul-`replace` auf v4 setzen | Unterschiedliche Importpfade, Typen und Parser-API-Verträge; kein nachgewiesener kompatibler Ersatz. Nicht durchgeführt. |
| Vollständige upstreamgestützte Smallstep-Migration | Bevorzugter zukünftiger Fix, sobald ein unterstützter Release existiert. Danach neue Binary, Scan/SBOM, native Prüfung, interne CA-/Renewal-/S3-TLS-/Backup-/Browser-/Restore-Regression. |
| Bereits ausgestellte Zertifikate statt interner CA | Benötigt einen ausdrücklich bestätigten Zertifikatsbetreiber, Erneuerung, sichere Schlüsselablage und Recovery. Der fehlende Zielbetrieb liefert diesen Vertrag nicht. OpenShift-Service-CA ist eine getrennte Zieloption und ersetzt nicht den Compose-Nachweis. |
| Geprüfter v3-Backport | Technisch untersuchbare letzte Alternative mit Forkpflege und tatsächlichen Kryptografie-/Kompatibilitätstests; kein unbemerkter Majorwechsel und keine Umdeklaration des Paketbefundes. Derzeit nicht freigegeben oder implementiert. |

## 5. Befristete Reviewvorlage – weiterhin nicht genehmigt

Eine autorisierte Securityperson kann diese eng begrenzte Ausnahme prüfen;
die folgenden Bedingungen sind ein Vorschlag, keine aktive Freigabe.

| Pflichtfeld | Entwurf / offene Entscheidung |
| --- | --- |
| Finding | Nur CVE-2026-116587 / GHSA-mgcc-cww5-fp2q, v3.0.5, `/usr/bin/caddy`, exakt oben gebundener Digest. Andere Findings bleiben separat. |
| Zweck | Ausschließlich privater Core-Proxy mit unveränderter gebundener Konfiguration und internem S3-TLS; keine öffentlich erreichbare CA, kein ACME-Server, keine zusätzliche Auth-/JWT-Erweiterung. |
| DoS / Restrisiko | Ein noch nicht ausgeschlossener JWK-Aufruf kann den gemeinsamen TLS-/HTTP-/S3-Proxy blockieren. Private Erreichbarkeit begrenzt Angreifer, ist kein Patch. TLS-Schutz und Sessionauthentifizierung verhindern parserbasierte DoS nicht allgemein. |
| Exposition | VPN/Loopback-Hostbindung und private Netze müssen auf dem echten Ziel geprüft werden. Kein Docker-Socket, keine Host-Namespaces, kein Host-Root-Mount. |
| Privilegien | Das Image selbst hat weiterhin keine USER-Angabe. PR9-Compose erbte deshalb Containerroot. PR10 setzt für Caddy und CA-Export ausdrücklich `10001:10001`, behält `cap_drop: ALL`, read-only Root und `no-new-privileges` bei und verwendet hohe Containerports. 1 CPU / 256 MiB begrenzen Ressourcenverbrauch, garantieren aber keine Verfügbarkeit. Der neue lokale Nachweis ist keine Zielinstallation. OpenShift bleibt separater restricted-SCC-Vertrag. |
| Secrets / CA | Schreibbare Caddy-Daten-/Konfigurationsvolumes enthalten CA-/TLS-Zustand. Deren Schutz, Root-Vertrauen und Recovery sind auf dem Ziel zu prüfen; sie werden weder durch die Profilprobe noch durch Paketstatistik freigegeben. |
| Voraussetzungen | Neuer vollständiger digestbezogener Scan/SBOM, gültige Scanner-DB, unabhängige native/Unknown-/CSP-/Netz-/TLS-Prüfung, aktuelle Profilprobe, Ziel-/Operatorfreigaben separat. |
| Dauer | Vorschlag: höchstens **7 Tage ab tatsächlicher Autorisierung**, konkreter UTC-Beginn und Ablauf vor Start einzutragen. Keine automatische Verlängerung. Bei fehlendem/abgelaufenem Entscheid bleibt der Start gesperrt. |
| Frühere Reviewtrigger | Upstreamfix, neue Advisorydaten, neue Binary/Go-/Modulversion, Konfigurations-/Admin-/Netz-/Domainwechsel, ACME-/On-Demand-Aktivierung, Zielwechsel oder DoS-/Neustartauffälligkeit. |
| Betreibermaßnahmen | Privater Zugang; Konfiguration und Admin-API nur für den Operator; Ressourcen-/Restart-/TLS-/Backupalarme tatsächlich testen; Wiederanlauf und datenerhaltenden Rollback bereithalten. Keine Änderung des bestehenden Gates allein für ein grünes Ergebnis. |
| Verantwortliche Person / Nachweis | **OFFEN** – Name, tatsächliche Entscheidung, Referenz, Rest-Risikoannahme sowie Beginn/Ablauf fehlen. |
| Wirksamer Status | **DRAFT_NOT_APPROVED / SECURITY_BLOCKED.** Dieser Bericht ist keine maschinenlesbare Ausnahme und keine Freigabesignatur. |

Der [Legacy-Recoveryvertrag](PR9_LEGACY_VERIFIER_REVIEW.md), Targetbetrieb,
Quellenrechte, reale Portfoliodaten und Modell-/Strategievalidierung bleiben
eigene Entscheidungen. Eine spätere Ausnahme für dieses Finding kann diese
Gates nicht schließen.

## 6. Nachgewiesene kleine Korrekturen in PR10

**Routing:** Die echte PR9-Adaptation sortierte `respond @internal 404`
hinter den allgemeinen `handle`-Proxy. Ein direkter Gegenversuch ohne
Frontendserver zeigte deshalb einen Web-Upstreamversuch statt der erwarteten
Proxy-404. Ein späteres Next.js-404 hätte die fehlende äußere Sperre verdecken
können. Core und OpenShift benutzen jetzt eine exklusive `handle @internal`
mit `respond 404`. Beide tatsächlichen
[adaptierten Konfigurationen](pr10-20261029/caddy-profile-hardened/receipt.json)
belegen die Reihenfolge vor dem allgemeinen Proxy; ein negativer Test
verwirft ausdrücklich die frühere Sortierung. Keine öffentliche Metricsroute
wird neu geöffnet.

**Benutzer und Ports:** Caddy und CA-Export laufen im Core-Overlay ausdrücklich
mit UID/GID 10001. Die offiziellen
[Portoptionen](https://caddyserver.com/docs/caddyfile/options#https-port)
erlauben interne HTTP-/HTTPS-Listener 8080/8443 bei unveränderten externen
Ports 80/443. S3 bleibt intern `caddy:9002`; Browserursprung und Secure-Cookies
bleiben `https://APP_DOMAIN`. Der lokale QA-Override mappt 9443 auf 8443.
Da beide Zielprofile ausschließlich TCP veröffentlichen, werden nur HTTP/1.1
und HTTP/2 aktiviert. Damit entfällt auch die irreführende HTTP/3-Ankündigung
des internen Ports über `Alt-Svc`.

**Neue Volumes und bestehende CA:** Frische Image-Verzeichnisse können die
neue UID für ihre eigenen PKI-/Config-Unterverzeichnisse verwenden. Die
einmalige vorhandene Compose-Storage-Init bereitet zusätzlich ausschließlich
eine leere CA-Export-Volumewurzel vor. Eine nicht leere, anders besitzende
CA-Exportwurzel wird mit Fehler abgewiesen. Bereits passende Wurzeln werden
nicht rekursiv umgeschrieben. Alte root-erzeugte Caddy-Daten-/Config-/CA-Volumes
benötigen einen ausdrücklich geprüften Migrations-/Recoveryablauf in **neue**
Volumes, der Zertifikat-/Schlüsselbytes erhält. Ein nicht lesbarer Altbestand
ist kein Anlass zur automatischen Neuausstellung oder zum rekursiven `chown`.
OpenShift erhält keinen Root-Initpod.

Die [Canary-Abnahme](pr10-20261029/caddy-nonroot-canary.json) verwendet nur neu
erzeugte, individuell markierte Volumes, synthetische Hostnamen und temporäre
Loopback-Hostports. **14 Prüfungen bestanden**: tatsächliche Prozess-UID,
leere effektive Capabilities, externer Redirect ohne internen Port,
HTTPS-/S3-TLS mit geprüfter CA, äußere `/internal/*`-404, keine HTTP/3-Ankündigung,
öffentlicher Root-Export unter UID 10001, Neustart und unveränderte CA-Bytes.
Alle eigenen Container/Volumes wurden entfernt. Der
[separate Test der tatsächlichen Storage-Init-Anweisung](pr10-20261029/caddy-storage-init.json)
bestand vier Fälle einschließlich Ablehnung eines synthetischen alten
root-eigenen Bestands ohne Eigentümer-/Byteänderung.

Diese Prüfungen belegen keinen S3-Objekttransfer, vollständigen Corebetrieb,
Browserdurchlauf, isolierten Gesamt-Restore oder realen Zielhost. Diese
Abnahmen werden getrennt an den finalen Core-Konfigurationsstand gebunden.
Die frühere fehlgeschlagene Routingprobe und vorläufige Harnessfehler bleiben
als private Originalbelege erhalten; die
[Belegübersicht](pr10-20261029/caddy-proof-index.json) kennzeichnet ihre Zustände.
**CVE-2026-116587 bleibt trotz dieser Korrekturen offen.**
