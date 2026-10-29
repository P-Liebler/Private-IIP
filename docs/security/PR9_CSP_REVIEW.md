# PR9 – CSP und dynamische Styles

Prüfdatum: **28.10.2026**. Technische Einschränkung umgesetzt; **Styleattribut-Review nicht genehmigt**.

## Vertrag

[Proxy](../../frontend/web/proxy.ts) und [Rootlayout](../../frontend/web/app/layout.tsx) erzeugen eine neue serverseitige Nonce je Dokumentrequest und übernehmen keine Clientnonce. Produktion erlaubt weder unsignierte Inline-Skripte noch `unsafe-eval`. Die Cacheantwort bleibt `private, no-store`.

`style-src` und `style-src-elem` erlauben eigene Stylesheets und Elemente mit genau dieser Nonce. Die bisherige breite Inline-Styleelement-Erlaubnis entfällt. Der kleine Clientadapter konfiguriert `get-nonce` in `useInsertionEffect`, bevor Radix seine Scroll-Lock-Styles erzeugt; kein globaler Serverstate wird pro Request verändert. `get-nonce` **1.0.1** war bereits transitiv gepinnt und wird nun direkt deklariert. Keine sonstige Node-Paketmigration.

## Verbleibende Ausnahme

`style-src-attr 'unsafe-inline'` bleibt erforderlich für variable Radix-/Chart-Geometrie und React-Styleattribute. Elementnonces autorisieren einzelne Attribute nicht. Statische Hashes decken wechselnde Pixelpositionen und Chartdimensionen nicht ab; `unsafe-hashes` für unbegrenzt variable Werte wäre keine belastbare Alternative.

Styleattribute können bei einer weiteren HTML-Injektionslücke Inhalt verdecken, umpositionieren und Benutzerinteraktion beeinflussen. Die getrennten `script-src`, `img-src`, `connect-src`, `object-src`, `base-uri`, `frame-ancestors` und `form-action` begrenzen zusätzliche Wege, beweisen aber keine Harmlosigkeit von CSS-Injektion. Keine Anwendung verarbeitet deshalb ungeprüftes HTML als vertrauenswürdige Finanzinformation.

Ein berechtigter Securityreviewer muss die konkrete Restgefahr zum exakten Image/Scope bewerten. Reviewer, Entscheidung und Ablauf fehlen; diese Datei ist **keine Ausnahmefreigabe**. Bei neuen Komponenten, geändertem Chart-/Dialogverhalten, CSP, Origins oder Browserzielen ist der Review erneut erforderlich.

## Browserprüfung und Grenzen

Der zusätzliche [PR9-Test](../../frontend/web/e2e/pr9-style-csp.spec.ts) injiziert Styles über den HTML-Parser: unsigniertes Styleelement muss wirkungslos bleiben, passendes Nonceelement muss wirken, erlaubtes Attribut wird getrennt geprüft. Die nachfolgende Anmeldung verwendet wieder ein echtes frisches Dokument. Der reale mobile Radixdialog muss eine Stylesheet-Nonce passend zum tatsächlichen Dokument besitzen und den Bodyscroll sperren; Escape schließt ihn.

Die Bestandsfälle decken Login, Dashboard, Charts, Dialoge, mobile/desktop Hauptseiten, Importe, Session-/Netzfehler und Schreibwiederholungen ab. Finale tatsächliche Zahlen und gebundene Belege stehen im [PR9E-Bericht](../PR9E_RELEASE_CANDIDATE_REPORT.md). Fehlversuche bleiben erhalten: ein Probe-Replay störte die Anmeldung, ein Textlocator konnte absichtlich ausgeblendete Styleelementtexte nicht finden. Der korrigierte Test liest die tatsächlichen DOM-`textContent`-/Noncewerte; keine CSP-Regel wurde für die Tests gelockert.

Automatisiert geprüft wird Chromium. Das ersetzt keine tatsächliche Windows-/Android-Clientabnahme auf dem noch fehlenden Zielhost, insbesondere keinen Nachweis für alte Browser ohne `style-src-elem`-/`style-src-attr`-Unterstützung. Der engere Fallback `style-src` kann dort dynamische Styles blockieren; solche Clients benötigen eigenen Nachweis und erhalten keine stillschweigende Lockerung.

Primärdokumentation: [Next.js CSP](https://nextjs.org/docs/app/guides/content-security-policy), [MDN style-src-attr](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/style-src-attr), [react-style-singleton](https://github.com/theKashey/react-style-singleton). Geprüft am 28.10.2026; kein Finanzproviderabruf.
