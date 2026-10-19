"""Export public image vulnerability facts, excluding image environment/configuration."""
import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

COMPONENTS = {
    "caddy-new": ("Caddy 2.11.7", "VPN HTTPS ingress; HTTP/TLS DoS paths require review"),
    "postgres": ("PostgreSQL/pgvector", "Internal only; authenticated SQL and OS package paths require review"),
    "valkey": ("Valkey", "Internal only; no host port"),
    "minio": ("MinIO", "Internal S3; root credentials in existing service contract; upstream archived"),
    "prometheus": ("Prometheus", "Loopback administration; scrape/Go/OS paths require review"),
    "grafana": ("Grafana", "Authenticated loopback administration; plugins/Go/OS paths require review"),
    "production-api": ("Backend production image", "Private proxy only; scanner facts concern exact audited image, not an unscanned rebuild"),
    "web": ("Next production image", "VPN HTTP application; Node/base packages require review"),
    "mlflow": ("MLflow image", "Optional authenticated internal service; no host port"),
    "ollama": ("Ollama", "Optional internal service; selected Go binary and OS dpkg manifest only; CUDA/library scan incomplete"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    records = []
    for name, (component, exposure) in COMPONENTS.items():
        path = args.input / (name + ".json")
        record = {"component": component, "exposure": exposure, "exploitability": "NOT_PROVEN_OR_DISMISSED; no exploit attempted", "action": "Patch/rebuild and rescan or document exact reachable-code risk review before target acceptance"}
        if not path.exists():
            record.update(status="SCAN_INCOMPLETE", findings=None)
        else:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            findings = []
            for result in value.get("Results", []):
                for vulnerability in result.get("Vulnerabilities", []):
                    findings.append({key: vulnerability.get(key) for key in (
                        "VulnerabilityID", "PkgName", "InstalledVersion", "FixedVersion", "Severity", "PrimaryURL",
                    )})
            record.update(status="PARTIAL_BINARY_AND_OS_MANIFEST_AUDIT" if name == "ollama" else "SCANNED_EXACT_ARTIFACT",
                          artifact=value.get("ArtifactName"),
                          image_id=value.get("Metadata", {}).get("ImageID"),
                          repo_digests=value.get("Metadata", {}).get("RepoDigests", []),
                          high=sum(v["Severity"] == "HIGH" for v in findings),
                          critical=sum(v["Severity"] == "CRITICAL" for v in findings),
                          findings=findings)
        records.append(record)
    payload = {"recorded_at": datetime.now(UTC).isoformat(), "scanner": "Trivy 0.70.0",
               "scope": "HIGH_AND_CRITICAL_ONLY; package findings are not confirmed exploit counts",
               "security_release": "BLOCKED", "records": records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
