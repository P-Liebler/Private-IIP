# PR7 – ergänzender Upstream-Advisoryabgleich

Prüfdatum26.10.2026. **KEINE SECURITYFREIGABE.**

Die [offizielle SeaweedFS-Advisory-API](https://api.github.com/repos/seaweedfs/seaweedfs/security-advisories?per_page=100) lieferte25 veröffentlichte Einträge. Originalantwort und SHA-256 liegen privat unter `backups/pr7-upstream-advisories/`. Vollständige Liste dieses Abrufs:

| Advisory | Schwere laut Hersteller | Veröffentlichter betroffener Bereich | Explizite Patchangabe |
| --- | --- | --- | --- |
| [GHSA-q9rj-8p2j-whg4](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-q9rj-8p2j-whg4) | critical | <= 4.45 | Nicht ausgewiesen |
| [GHSA-qmx6-fpcw-q3xg](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-qmx6-fpcw-q3xg) | medium | <= 4.45 | Nicht ausgewiesen |
| [GHSA-jcgp-4284-p6g2](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-jcgp-4284-p6g2) | high | >= 4.43, <= 4.44 | Nicht ausgewiesen |
| [GHSA-5fx4-c9qp-36jc](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-5fx4-c9qp-36jc) | critical | <=4.45 | Nicht ausgewiesen |
| [GHSA-3j72-rgq3-c2j7](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-3j72-rgq3-c2j7) | critical | 4.24 through 4.42 | Nicht ausgewiesen |
| [GHSA-3883-fr8h-xrqg](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-3883-fr8h-xrqg) | critical | >= 3.00, <= 4.42 | Nicht ausgewiesen |
| [GHSA-vwwx-w898-9f4r](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-vwwx-w898-9f4r) | critical | < 4.42 | Nicht ausgewiesen |
| [GHSA-cprc-whx4-v3f5](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-cprc-whx4-v3f5) | medium | <= 4.41 | Nicht ausgewiesen |
| [GHSA-939f-xh28-2q48](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-939f-xh28-2q48) | high | <= 4.41 | Nicht ausgewiesen |
| [GHSA-39jr-32mg-hjwj](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-39jr-32mg-hjwj) | critical | >= 4.35, <= 4.41  | Nicht ausgewiesen |
| [GHSA-fjm8-2g3v-ffjw](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-fjm8-2g3v-ffjw) | high | >= 4.24, <= 4.41 | Nicht ausgewiesen |
| [GHSA-7fw3-5g74-c7p9](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-7fw3-5g74-c7p9) | high | <= 3.97 | Nicht ausgewiesen |
| [GHSA-h249-8wvq-pc5v](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-h249-8wvq-pc5v) | high | <= 3.97 | Nicht ausgewiesen |
| [GHSA-jw56-gm6j-34mp](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-jw56-gm6j-34mp) | critical | <= 4.40 | Nicht ausgewiesen |
| [GHSA-hqp5-j79g-vr89](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-hqp5-j79g-vr89) | medium | >= 4.0.388, <= 4.40.0 | Nicht ausgewiesen |
| [GHSA-9x53-cjpr-m682](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-9x53-cjpr-m682) | high | < 4.39 | None patched yet |
| [GHSA-fvpg-g364-j8vh](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-fvpg-g364-j8vh) | high | >= 3.88, <= 4.39 | Nicht ausgewiesen |
| [GHSA-757h-cm9x-wprg](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-757h-cm9x-wprg) | high | <= 4.39 | Nicht ausgewiesen |
| [GHSA-99q7-x53r-6j4g](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-99q7-x53r-6j4g) | high | = 4.39 | 4.40 |
| [GHSA-gv5w-hfx8-8cwq](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-gv5w-hfx8-8cwq) | high | < 4.24 | 4.24 |
| [GHSA-2v6v-25fm-p4fg](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-2v6v-25fm-p4fg) | critical | < 4.24 | 4.24 |
| [GHSA-87fv-vqqr-m4jr](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-87fv-vqqr-m4jr) | critical | < 4.24 | 4.24 |
| [GHSA-56wq-x3wv-3ff4](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-56wq-x3wv-3ff4) | high | < 4.34 | 4.34 |
| [GHSA-hgpf-8634-g44c](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-hgpf-8634-g44c) | medium | >= 4.08, < 4.34 | 4.34 |
| [GHSA-w62w-66v9-vvgv](https://github.com/seaweedfs/seaweedfs/security/advisories/GHSA-w62w-66v9-vvgv) | high | < 4.30 | 4.30 |

Der Kandidat meldet4.51 und liegt numerisch oberhalb der hier veröffentlichten Obergrenzen. Fehlende Patchangaben sind kein Nachweis einer Behebung; ein Paketbefund von0/0 ist ebenfalls keine vollständige native Codeabnahme. Die abweichende gemeldete Imagerevision wurde getrennt anhand der tatsächlich gemeldeten Commit-ID geprüft, nicht als reproduzierbar attestierter Build behandelt.

Der konkret verwendete S3-POST- und gRPC-Adminpfad enthält im geprüften gemeldeten Quellstand die Autorisierungsprüfungen. Neue negative Laufzeitprobes dafür liegen in `ops/probe_pr7_s3_policies.py` und `ops/pr7_s3_admin_probe.cjs`; ihr tatsächliches Ergebnis ist im Stagingbericht zu belegen. Die leeren gRPC-Anfragen dürfen auch bei fehlender Prüfung keine Identität anlegen oder entfernen.

SFTP-/Lance-/ArangoDB-Pfade sind im vorgesehenen Serverprofil nicht beabsichtigt. Das ersetzt keine Laufzeitprüfung der gestarteten Listener, Storekonfiguration und Netzgrenzen. Volume-/Filer-/Master-/gRPC-Ports bleiben im eigenen Storage-Netz; App-Clients verwenden ausschließlich den CA-geprüften S3-Proxy. Verbleibende relevante Pfade und die Buildzuordnung behalten ihr Freigabegate.

## Ollama und Browserpolicy

Die [offizielle Ollama-Advisoryseite](https://github.com/ollama/ollama/security/advisories) zeigt am Prüftag keine veröffentlichten Herstelleradvisories. Daraus folgt keine Abwesenheit von Schwachstellen. Die [Releaseliste](https://github.com/ollama/ollama/releases) nennt0.40.11 vom24.10.; der fest gepinnte getestete Runtimebestand bleibt0.40.4. Ein Upgrade braucht eigene Modell-/Embedding-/Streaming-/Restoreprüfungen. Der aktuelle vollständige Imagescan und die Grenzen nicht unterstützter nativer Analyzer werden separat ausgewiesen.

Die vorhandene CSP enthält weiterhin `unsafe-inline` für Skripte und Styles. Die [Next.js-Primärdokumentation](https://nextjs.org/docs/app/guides/content-security-policy) beschreibt pro Anfrage erzeugte Nonces; ein CSP-Header allein belegt keinen solchen Schutz. Erfolgreiche Hydration oder eine temporäre Browser-SPKI-Freigabe schließen weder diese Policyentscheidung noch das echte Client-CA-/Zielhostgate.

Next.js16.4.3 ist laut [offizieller Releasenotiz](https://github.com/vercel/next.js/releases/tag/v16.4.3) ein Fehlerkorrektur-Backport. Die in PR7 geprüfte16.4.2 wird nicht allein wegen einer neueren Versionsnummer ohne konkreten Befund als unsicher oder freigegeben erklärt. Dependency- und Imagescans gelten jeweils nur für ihre exakten Pins.
