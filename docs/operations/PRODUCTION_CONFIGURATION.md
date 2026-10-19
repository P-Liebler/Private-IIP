# Produktionskonfiguration

`ops/production.env.example` ist ausschließlich eine Vorlage. APP_DOMAIN darf weder Schema, Port noch Pfad enthalten. APP_ENV ist `staging` oder `production`; COMPOSE_PROJECT_NAME endet entsprechend auf `-staging` oder `-production`. Ein eigener Projektname isoliert automatisch benannte Volumes und Netzwerke. Unterschiedliche Projekte reichen nicht, wenn der Operator externe Volumes oder Mounts auf denselben Inhalt umbiegt.

Pflichtwerte: APP_DOMAIN, VPN_BIND_ADDRESS, POSTGRES_DB/USER/PASSWORD, MINIO_ACCESS_KEY/SECRET_KEY, TOTP_ENCRYPTION_KEY, GRAFANA_ADMIN_USER/PASSWORD und absoluter BACKUP_ROOT. Die drei Passwörter erhalten mindestens 24 zufällige URL-sichere Zeichen und müssen verschieden sein. Für DB-/S3-Credentials verhindert die URL-sichere Zeichenmenge unbemerkte URL-Interpolation. Der TOTP-Schlüssel muss ein echtes Fernet-Keyformat besitzen. Niemals Beispielwerte übernehmen.

API, Worker und Beat lesen denselben Compose-Settings-Anker. `OPERATIONS_OPERATOR_USERNAMES` ist eine explizite JSON-Allowlist vorhandener Konten für `/system/status`. Sie vergibt keine Datenquellen- oder Modellfreigaben. `DATA_OPERATOR_USERNAMES` und `ML_OPERATOR_USERNAMES` bleiben getrennt.

APP_DEBUG=false, sichere Cookies, HTTPS-Origins und MinIO-TLS sind Pflicht. ASSISTANT_TEST_MODE ist ausschließlich in `test` erlaubt. DATA_COLLECTION_ENABLED=false und FORWARD_SHADOW_ENABLED=false bleiben für PR3 verbindlich. Ein späterer geplanter Finanzbetrieb erfordert einen neuen Auftrag und die vorhandenen Rechte-/Policygates.

Preflight prüft Formate, Platzhalter, Domainübereinstimmung, Projektgrenze, Docker-Ressourcen, Backupverzeichnis und gerenderte Port-/Privilegienkonfiguration. Er verändert weder Dateien noch Dienste; der Offline-Modus ruft Docker nicht auf. Windows-ACL, NTP, echte Mountidentität, Erreichbarkeit und unabhängige Speicherhaltung benötigen zusätzliche Operatornachweise. Ein beschreibbarer Ordner oder 5 GiB freier Speicher ist kein ausreichender Produktionsnachweis. Staging/Produktion auf derselben Maschine brauchen unterschiedliche Ingressadressen oder bewusst geprüfte Port-/Monitoring-Overrides.
