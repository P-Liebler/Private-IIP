# TLS und private CA

Caddy `tls internal` ist der bestehende private TLS-Vertrag. `caddy_data` enthält die private CA und muss erhalten bleiben. `ca-export` kopiert ausschließlich `root.crt` in das für Backenddienste schreibgeschützte Vertrauensvolume. API, Worker und Beat prüfen darüber MinIO-TLS. Fehlendes Vertrauen darf nicht durch `verify=False` ersetzt werden.

Operator prüft auf Windows 11 und Android: korrekter privater Hostname, Zertifikatskette, SAN, Gültigkeit und Ablauf, vertrauenswürdiger Aussteller, HTTPS ohne Warnung, Login/TOTP/Logout und Secure/HttpOnly/SameSite-Cookie. Nur das **öffentliche** Root-Zertifikat über einen authentifizierten Weg verteilen; Fingerprint über einen zweiten bekannten Kanal vergleichen. Windows-Zertifikatsverwaltung beziehungsweise Android-Einstellungen für Benutzer-CA verwenden und den tatsächlich verwendeten Browser prüfen. Android-Apps können Benutzer-CAs anders behandeln. Private Keys niemals auf Clients kopieren.

Caddy erneuert Leaf-Zertifikate aus persistiertem CA-Zustand. Ablauf, Zeitabgleich und Neustart prüfen. HSTS gilt nur für den konfigurierten Host; es ersetzt keine gültige Vertrauenskette. CSP erlaubt aktuell Inline-Scripts für Next-Hydration; object-src/base-uri/frame-ancestors/form-action sind eingeschränkt. Dies ist keine noncebasierte strenge CSP. Benutzerinhalte bleiben escaped; keine willkürlichen HTML-Renderpfade ergänzen.

## Geplante CA-Rotation

1. Alte CA sichern, Fingerprints und betroffene Dienste dokumentieren; neue CA in isolierter Vorbereitung erzeugen.
2. Neue **öffentliche** CA zusätzlich auf allen berechtigten Clients verteilen und Fingerprints bestätigen.
3. Zertifikate kontrolliert umstellen, öffentlichen Export aktualisieren, MinIO-Vertrauen/API/Worker/Beat neu starten.
4. Alle Clients, S3, Auth und negative Tests prüfen. Alten Vertrauensanker erst danach zurückziehen.

Verlust der CA bedeutet keinen Verlust der Finanzdaten, verhindert aber bestehende TLS-Vertrauensbeziehungen. Wiederherstellung aus getrenntem verschlüsseltem Secrets-Backup ist bevorzugt. Keine stille Neuerzeugung anstelle eines verlorenen produktiven CA-Volumes. Lokale TLS-Probe ist nicht TLS_CLIENT_TRUST_VERIFIED.
