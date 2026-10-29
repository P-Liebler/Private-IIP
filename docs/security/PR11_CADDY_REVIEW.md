# PR11B – Caddy: abschließende technische Prüfung

Prüfdatum: **29.10.2026, 15:24–15:26 UTC**. Ergebnis:
**SECURITY_OPERATOR_DECISION_REQUIRED**. Keine Securityfreigabe und keine
wirksame Ausnahme.

## Entscheidung

Für den exakt verwendeten Caddy-Digest ist weiterhin keine belegte,
unterstützte technische Behebung von **CVE-2026-116587 /
GHSA-mgcc-cww5-fp2q** verfügbar. Die aktuelle Core-Konfiguration stellt keinen
ACME-Server und keinen On-Demand-Issuer bereit. In den untersuchten aktiven
HTTP-/TLS-Pfaden wurde kein Eingang gefunden, der fremde JWKs an den
betroffenen Parser übergibt. Das begrenzt die nachgewiesene Exposition; eine
vollständige Nichterreichbarkeit oder ein Paketfix ist damit nicht bewiesen.

Der vorhandene interne CA-Vertrag bleibt erhalten. Eine Entfernung der
Smallstep-Abhängigkeit, ein eigener Kryptografie-Backport oder eine Umstellung
auf fremd verwaltete Zertifikate wird nicht als geprüfte Lösung ausgegeben.
Die verbleibende konkrete Entscheidung liegt bei der autorisierten
Securityperson. Bis zu einer zulässigen tatsächlichen Freigabe bleibt der
Produktivstart gesperrt.

## Exakter Stand und Nachweis

| Gegenstand | Ergebnis |
| --- | --- |
| Image / tatsächliche Image-ID | `private-iip/caddy@sha256:6416b8c2e10d8d62b131dbf3755c01069d7b3dcdb7af720b76c8aeed8bc9dcaf` |
| Enthaltene Laufzeit | Caddy v2.11.7, Go 1.27.3, `go-jose/v3` v3.0.5; eigener v4-Paketpfad bereits v4.1.6 |
| Compose-Profil | `tls internal`, lokale PKI; HTTP/1.1 und HTTP/2, interne Ports 8080/8443, S3-TLS auf 9002; Admin nur Containerloopback |
| OpenShift-Profil | Vorhandene Service-CA-Zertifikate, `auto_https off`, `admin off`; keine neue interne CA. Dasselbe vollständige Caddy-Image bleibt im Inventar. |
| Aktuelle Offlineprüfung | Tatsächliche Binary, Module und beide adaptierten Profile bytegleich zu PR10; `network none`, read-only Root, UID 10001, kein Serverstart |
| Gezielte Regression | Bestehende neun Profiltests erneut bestanden; keine zusätzlichen Tests zur Erhöhung der Testzahl |
| Letzter abgeschlossener Paketbefund | PR10 vom 29.10.2026: 0 Critical, **1 High**, 3 Medium, 1 Unknown. Dieser Bericht erklärt ihn nicht für behoben. Das vollständige PR11-Inventar wird separat gebunden. |

Der neue [datierte Beleg](pr11-20261029/caddy-review.json) enthält die aktuellen
offiziellen Abrufzeiten, Originalantwort-Hashes, tatsächlich ermittelte Tags,
Modulmanifestzeilen und Profilhashes. Die Originalantworten der öffentlichen
Security-/Quellcodeprüfung liegen unter dem dort angegebenen privaten
`backups/`-Pfad. Finanzendpunkte wurden nicht aufgerufen. Die früheren
[Canary-](pr10-20261029/caddy-nonroot-canary.json),
[Storage-Init-](pr10-20261029/caddy-storage-init.json) und
[Importkettenbelege](pr10-20261029/caddy-profile/source-review.json) bleiben
unverändert. Es wurde kein weiterer synthetischer Canary oder CA-Bestand
erzeugt.

## Offizielle Patchprüfung

Das [Maintainer-Advisory](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q)
führt am Prüfdatum für v3 bis einschließlich 3.0.5 weiterhin keine gepatchte
Version. Es beschreibt CPU-Überlastung beim Parsen manipulierter privater
RSA-JWKs unter Go ab 1.24. Der v4-Fix ist 4.1.6; der getrennte v3-Import wird
dadurch nicht ersetzt.

Die frisch abgefragten [offiziellen Tags](https://github.com/go-jose/go-jose/tags)
enthalten keinen jüngeren v3-Tag. Die offiziellen jüngsten Releases sind
weiterhin [Caddy v2.11.7](https://github.com/caddyserver/caddy/releases/tag/v2.11.7),
[Smallstep Certificates v0.30.2](https://github.com/smallstep/certificates/releases/tag/v0.30.2)
und [Smallstep Crypto v0.91.1](https://github.com/smallstep/crypto/releases/tag/v0.91.1).
Das [aktuelle Crypto-Modulmanifest](https://github.com/smallstep/crypto/blob/v0.91.1/go.mod)
benötigt weiterhin `go-jose/v3` v3.0.5. Der neue Patchstand bietet daher keinen
belegten Abschluss dieses Findings.

## Importkette und konkreter JWK-Pfad

Der interne Issuer gehört zum Go-Paket `caddytls`. Dessen
[Implementierung](https://github.com/caddyserver/caddy/blob/v2.11.7/modules/caddytls/internalissuer.go)
importiert die PKI und Smallstep-Provisioner direkt und verwendet
`CA.NewAuthority` und `SignWithContext` für lokal erzeugte CSRs. Die
[PKI-Authority](https://github.com/caddyserver/caddy/blob/v2.11.7/modules/caddypki/ca.go)
bindet Smallstep ein; dessen JOSE-Wrapper benötigt v3. Das Abwählen des
gesonderten `acme_server`-Moduls entfernt diese für `tls internal` benötigte
Importstrecke nicht.

Ein konkreter fremder JWK-Eingang existiert beim optionalen ACME-Server:
Die [Smallstep-ACME-Middleware](https://github.com/smallstep/certificates/blob/v0.30.2/acme/api/middleware.go)
parst den Requestbody vor der abschließenden Account-/Signaturprüfung.
Dieses Modul ist in der Standardbinary registriert, im aktuellen Core jedoch
nicht konfiguriert. Gewöhnliche HTTP-Header, proxied Requestbodies und ein
beliebiger URL-Pfad `/acme/...` aktivieren den Handler nicht. Der untersuchte
interne Issuer übergibt einen X.509-CSR, keinen fremden JWK-/JWT-String.

Die neun vorhandenen Negativtests verlangen einen neuen Review bei
ACME-/On-Demand-Aktivierung, anderem Issuer, fremdem Upstream oder einer
erweiterten Adminbindung. Sie belegen keine vollständige Aufrufgraphanalyse.
Ein Operator mit Schreibzugriff auf Caddys Konfiguration oder allgemeine
Admin-API kann die Exposition ändern. Dafür sind Zugriffsschutz und ein
sofortiger Re-Review erforderlich. Ein aufwendiger DoS-Angriff wurde nicht
ausgeführt.

## Erlaubt der TLS-Vertrag eine kleinere sichere Konfiguration?

| Möglichkeit | Technischer Schluss |
| --- | --- |
| Nur optionale ACME-Registrierung entfernen | Die interne CA benötigt weiter das betroffene Paket. Kein nachgewiesener Fix. |
| Nur automatische CA-Ausstellung abschalten | Würde vorhandene Leaf-Erneuerung, Root-Vertrauen und die S3-/Backup-TLS-Strecke ändern. Ein laufendes Zertifikat allein ist kein dauerhafter Recoveryvertrag. |
| Vorhandene OpenShift-Service-CA | Ist bereits eine eigene Zielkonfiguration und verlangt keinen neuen CA-Mechanismus. Ohne verfügbaren und autorisierten Cluster ersetzt sie keinen Compose-Nachweis; die betroffene Bibliothek bleibt in der unveränderten Binary. |
| Extern verwaltete Zertifikate für Compose | Caddy unterstützt dies, aber es fehlen tatsächlicher Zertifikatsbetreiber, Schlüsseltransport, Erneuerung, Vertrauensverteilung und geprüfter Wiederherstellungsweg. Ohne diese geschützten Eingaben ist keine sichere konkrete Änderung testbar. |
| v3 durch v4 ersetzen / eigener Backport | Unterschiedliche Paketpfade und Typverträge; kein nachgewiesener kleiner kompatibler Upstream-Patch. Keine eigene Kryptografiemigration durchgeführt. |

Die [Caddy-TLS-Dokumentation](https://caddyserver.com/docs/caddyfile/directives/tls)
beschreibt interne Ausstellung und manuell bereitgestellte Zertifikate als
verschiedene Betriebsweisen. Die bestehende interne CA pauschal zu ersetzen
würde neue Betreiberpflichten schaffen, während weiterhin kein Zielhost
bereitsteht. Der kleinste belegte PR11-Schritt ist deshalb der aktuelle
exakte Befund mit erhaltenem TLS-Vertrag und offenem Securityentscheid.

## Konkrete Übergabe an den Operator

| Punkt | Erforderlich |
| --- | --- |
| Entscheidung | Auf unterstützten Fix warten oder eine findingbezogene, befristete Rest-Risikoannahme für den exakten Digest und das gebundene Profil tatsächlich autorisieren. |
| Wer autorisiert? | Zuständige Securityperson; Zielhost- und Betriebsfreigabe bleiben zusätzliche Entscheidungen. Ein Agent, grüner Paketcheck oder Argo-Sync kann sie nicht ersetzen. |
| Geschützte Eingaben | Tatsächlicher Review mit Name/Referenz, UTC-Beginn und Ablauf, konkretem Ziel, Netz-/Adminzugang, Alarmierungs- und Wiederanlaufnachweis; keine Schlüssel oder Zugangsdaten in Git. |
| Prüfkriterien | Vollständiger aktueller Scan/SBOM; unveränderte Profil-/Imagehashes; private Erreichbarkeit, Adminschutz, CA-/Schlüsselsicherung, Ressourcenbegrenzung und tatsächlich geprüfte Ausfall-/Recoveryreaktion. Alle anderen Findings bleiben separat. |
| Restrisiko | CPU-DoS im gemeinsamen Browser-/API-/S3-TLS-Proxy bei einem erreichbaren verwundbaren JWK-Pfad. Private Netze, UID 10001, Caps-Drop und Limits ersetzen keinen Patch und garantieren keine Verfügbarkeit. |
| Frist und Trigger | Der PR10-Entwurf schlägt höchstens sieben Tage ab tatsächlicher Autorisierung vor. Patch, Advisory-, Image-, Go-/Modul-, Ziel-, Profil-, Admin- oder Netzwerkänderung erzwingt vorzeitig einen neuen Review; keine automatische Verlängerung. |
| Bis dahin | **Produktiver Start und Securityfreigabe gesperrt.** Kein genehmigter Review und keine wirksame maschinenlesbare Ausnahme wurden erstellt. |

Der [PR10-Review](PR10_CADDY_REVIEW.md) bleibt als historischer Befund erhalten.
PR11 ändert weder CA-Originale noch Images, Compose-/OpenShiftdateien oder
Scannerregeln für dieses Finding. Andere Recovery-, Quellen-, Portfolio-
und Benutzerabnahmen bleiben eigenständig.
