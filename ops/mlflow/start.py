"""Internal authenticated tracking; metadata shares the application's backup DB."""

import configparser
import os
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

username = os.environ.get("MLFLOW_TRACKING_USERNAME", "")
password = os.environ.get("MLFLOW_TRACKING_PASSWORD", "")
if not username or len(password) < 24:
    raise RuntimeError("Configure a private MLflow operator and a secret of at least 24 characters")
url = make_url(os.environ["DATABASE_URL"]).set(drivername="postgresql+psycopg2")
engine = create_engine(url)
with engine.begin() as connection:
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS iip_mlflow"))
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS iip_mlflow_auth"))
engine.dispose()
tracking_uri = url.update_query_dict({"options": "-csearch_path=iip_mlflow"}).render_as_string(hide_password=False)
auth_uri = url.update_query_dict({"options": "-csearch_path=iip_mlflow_auth"}).render_as_string(hide_password=False)
configuration = configparser.ConfigParser(interpolation=None)
configuration["mlflow"] = {"default_permission": "NO_PERMISSIONS", "database_uri": auth_uri,
                            "admin_username": username, "admin_password": password,
                            "authorization_function": "mlflow.server.auth:authenticate_request_basic_auth"}
for key in configuration["mlflow"]:
    # MLflow reads its config using ConfigParser's default interpolation.
    configuration["mlflow"][key] = configuration["mlflow"][key].replace("%", "%%")
path = Path("/tmp/private-mlflow-auth.ini")
with path.open("w", encoding="utf-8") as output:
    configuration.write(output)
path.chmod(0o600)
environment = {**os.environ, "MLFLOW_AUTH_CONFIG_PATH": str(path),
               "MLFLOW_FLASK_SERVER_SECRET_KEY": password,
               "AWS_ACCESS_KEY_ID": os.environ["MINIO_ACCESS_KEY"],
               "AWS_SECRET_ACCESS_KEY": os.environ["MINIO_SECRET_KEY"],
               "MLFLOW_S3_ENDPOINT_URL": ("https://" if os.environ.get("MINIO_SECURE") == "true" else "http://") + os.environ["MINIO_ENDPOINT"]}
if os.environ.get("MINIO_CA_CERT_PATH"):
    environment["AWS_CA_BUNDLE"] = os.environ["MINIO_CA_CERT_PATH"]
# Application model artifacts are immutable data-only objects in the existing
# MinIO bucket; MLflow additionally tracks their URI/hash as run metadata.
raise SystemExit(subprocess.call(["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--workers", "1",
                                 "--app-name", "basic-auth", "--backend-store-uri", tracking_uri,
                                 "--artifacts-destination", "s3://" + os.environ.get("MINIO_BUCKET_RAW", "raw-ingestions") + "/mlflow-artifacts",
                                 "--allowed-hosts", "mlflow:5000,mlflow,localhost:5000,localhost"], env=environment))
