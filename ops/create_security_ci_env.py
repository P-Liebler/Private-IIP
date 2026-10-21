"""Write generated, disposable CI-only Compose credentials without displaying them."""
import base64
from pathlib import Path
import secrets
import sys

target = Path(sys.argv[1])
backup_root = target.parent / "security-backup"
backup_root.mkdir(exist_ok=True)
values = {
    "APP_ENV": "production", "COMPOSE_PROJECT_NAME": "private-iip-security-production",
    "APP_DOMAIN": "iip.private.test", "VPN_BIND_ADDRESS": "10.9.0.2",
    "POSTGRES_DB": "security_ci", "POSTGRES_USER": "security_ci",
    "POSTGRES_PASSWORD": secrets.token_hex(24), "MINIO_ACCESS_KEY": "security_ci",
    "MINIO_SECRET_KEY": secrets.token_hex(24), "GRAFANA_ADMIN_USER": "security_ci",
    "GRAFANA_ADMIN_PASSWORD": secrets.token_hex(24),
    "MLFLOW_TRACKING_USERNAME": "security_ci", "MLFLOW_TRACKING_PASSWORD": secrets.token_hex(24),
    "TOTP_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    "BACKUP_ROOT": str(backup_root.resolve()),
}
with target.open("x", encoding="utf-8") as output:
    for key, value in values.items():
        output.write(f"{key}={value}\n")
target.chmod(0o600)
