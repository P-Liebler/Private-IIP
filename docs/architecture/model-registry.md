# P7: Registry und Artefakte

`0013_ml_registry`: Trainingsjobs, immutable Modellversionen, Promotion-Reviews, Predictions und Outcome-Versionen. Reviews bestimmen den Application-Status ohne ältere Bewertungen zu überschreiben. Administration verlangt explizite Username-Allowlist und Ownership; standardmäßig keine Operatoren.

Intern erzeugte JSON-Bundles mit Skalierung, Koeffizienten, nativen LightGBM-Texten beziehungsweise XGBoost-JSON und Kalibrierung. Keine Pickle-/Joblib-Uploads. Vor Laden: interner Schlüssel, SHA-256, Vertrag, Modellkonfiguration, Trainingscode und Dependency-Lock. MinIO-Objekte werden nicht überschrieben.

MLflow läuft optional im Compose-Profil `ml`, ohne Hostport. Basic Auth benötigt einen Operator und ein Secret von mindestens 24 Zeichen. Tracking/Auth nutzen PostgreSQL-Schemas `iip_mlflow` und `iip_mlflow_auth`; der vollständige DB-Dump erfasst sie. Artefakte liegen im vorhandenen MinIO-Bucket. Runs protokollieren Parameter, OOS-Metriken und Artefakthash; Alias `challenger` kennzeichnet Experimente. Application-Status bleibt unabhängig von MLflow-Lifecycle-Stages.

Referenzen geprüft 2026-10-14: [scikit-learn Persistenz](https://scikit-learn.org/stable/model_persistence.html), [MLflow Tracking-Server](https://mlflow.org/docs/latest/self-hosting/architecture/tracking-server/), [Artifact Store](https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/). Betriebs-/Auth-/Artifact-/Restore-Abnahme steht aus.
