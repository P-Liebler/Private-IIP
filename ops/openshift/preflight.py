"""Offline checks for the non-deployable OpenShift preparation package.

This tool does not contact Kubernetes, read cluster secrets, run apply/sync, or
grant a deployment approval. Exit 2 is intentional even when draft checks pass.
It complements, and cannot replace, the existing immutable release/security gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
IMAGE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
FORBIDDEN_KINDS = {"Secret", "SecurityContextConstraints", "Role", "RoleBinding", "ClusterRole",
                   "ClusterRoleBinding", "CronJob", "DaemonSet"}
SENSITIVE_KEYS = {"DATABASE_URL", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "TOTP_ENCRYPTION_KEY",
                  "POSTGRES_PASSWORD", "MC_HOST_local"}


def sensitive_key(name: str) -> bool:
    return name in SENSITIVE_KEYS or name.endswith(("_PASSWORD", "_SECRET_KEY", "_API_KEY", "_ENCRYPTION_KEY"))


def expand(document: dict) -> list[dict]:
    return document["items"] if document.get("kind") == "List" else [document]


def documents(root: Path) -> list[dict]:
    result = []
    for path in sorted(root.rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if "kind" in document:
            result.extend(expand(document))
    return result


def pod_spec(resource: dict) -> dict | None:
    if resource["kind"] == "Pod":
        return resource["spec"]
    if resource["kind"] in {"Deployment", "StatefulSet", "Job"}:
        return resource["spec"]["template"]["spec"]
    return None


def validate_resources(resources: list[dict]) -> list[str]:
    """Check preparation invariants without interpreting an approval receipt."""
    errors = []
    for obj in resources:
        kind, name = obj["kind"], obj["metadata"]["name"]
        key = f"{kind}/{name}"
        spec = obj.get("spec", {})
        if kind == "ConfigMap" and any(sensitive_key(field) for field in obj.get("data", {})):
            errors.append(f"{key}:CREDENTIALS_MUST_NOT_BE_CONFIGMAP_DATA")
        manual_rbac = kind in {"Role", "RoleBinding"} and obj["metadata"].get("annotations", {}).get("investment.local/bootstrap-only") == "true"
        if kind in FORBIDDEN_KINDS and not manual_rbac:
            errors.append(f"{key}:FORBIDDEN_RESOURCE")
        if kind in {"Deployment", "StatefulSet"} and spec.get("replicas") != 0:
            errors.append(f"{key}:DRAFT_REPLICAS_MUST_BE_ZERO")
        if kind == "Job" and (spec.get("suspend") is not True or spec.get("backoffLimit") != 0):
            errors.append(f"{key}:MANUAL_JOB_MUST_BE_SUSPENDED_NO_RETRY")
        annotations = obj["metadata"].get("annotations", {})
        if "argocd.argoproj.io/hook" in annotations:
            errors.append(f"{key}:AUTOMATIC_HOOK_FORBIDDEN")
        if kind == "Application" and (spec.get("syncPolicy", {}).get("automated") is not None
                                      or obj["metadata"].get("finalizers")):
            errors.append(f"{key}:AUTOMATIC_SYNC_OR_CASCADING_DELETE_FORBIDDEN")
        if kind == "Service" and (spec.get("type", "ClusterIP") != "ClusterIP"
                                   or spec.get("externalIPs") or spec.get("externalName")):
            errors.append(f"{key}:ONLY_INTERNAL_SERVICES_ALLOWED")
        if kind == "PersistentVolumeClaim":
            options = annotations.get("argocd.argoproj.io/sync-options", "")
            if "Prune=false" not in options or "Delete=false" not in options:
                errors.append(f"{key}:PERSISTENT_STORAGE_DELETE_PROTECTION_MISSING")
            if any(field in spec for field in ("volumeName", "dataSource", "dataSourceRef", "selector")):
                errors.append(f"{key}:EXISTING_STORAGE_REUSE_FORBIDDEN_IN_DRAFT")
        if kind == "NetworkPolicy":
            for direction, peers_key in (("ingress", "from"), ("egress", "to")):
                for rule in spec.get(direction, []):
                    peers = rule.get(peers_key, [])
                    if not peers or not rule.get("ports") or any("ipBlock" in peer or not peer for peer in peers):
                        errors.append(f"{key}:UNBOUNDED_NETWORK_ACCESS_FORBIDDEN")
                    if any(peer.get("namespaceSelector") == {} or peer.get("podSelector") == {} for peer in peers):
                        errors.append(f"{key}:BROAD_NETWORK_PEER_FORBIDDEN")
        if kind == "ConfigMap" and obj["metadata"]["name"] == "iip-config":
            for field in ("DATA_COLLECTION_ENABLED", "FORWARD_SHADOW_ENABLED", "SEC_ENABLED", "ASSISTANT_TEST_MODE"):
                if obj.get("data", {}).get(field) != "false":
                    errors.append(f"{key}:DRAFT_AUTOMATION_MUST_REMAIN_DISABLED:{field}")
            if obj.get("data", {}).get("MINIO_SECURE") != "true":
                errors.append(f"{key}:VERIFIED_S3_TLS_REQUIRED")
        if kind == "Role" and manual_rbac:
            for rule in obj.get("rules", []):
                if (any(verb in {"delete", "deletecollection", "*"} for verb in rule.get("verbs", []))
                        or any(kind in {"secrets", "jobs", "roles", "rolebindings", "securitycontextconstraints", "*"}
                               for kind in rule.get("resources", [])) or "*" in rule.get("apiGroups", [])):
                    errors.append(f"{key}:BOOTSTRAP_RBAC_SCOPE_EXCEEDED")
        if kind == "RoleBinding" and manual_rbac:
            role_ref = obj.get("roleRef", {})
            if role_ref.get("kind") != "Role" or role_ref.get("name") != "investment-gitops-managed":
                errors.append(f"{key}:BOOTSTRAP_BINDING_MUST_USE_REVIEWED_NAMESPACE_ROLE")
            if any(subject.get("kind") != "ServiceAccount" for subject in obj.get("subjects", [])):
                errors.append(f"{key}:BOOTSTRAP_BINDING_MUST_USE_CONTROLLER_SERVICEACCOUNT")
        pod = pod_spec(obj)
        if pod is None:
            continue
        if pod.get("automountServiceAccountToken") is not False:
            errors.append(f"{key}:SERVICEACCOUNT_TOKEN_MUST_BE_DISABLED")
        if pod.get("serviceAccountName") != "iip-runtime":
            errors.append(f"{key}:UNEXPECTED_SERVICEACCOUNT")
        security = pod.get("securityContext", {})
        if security.get("runAsNonRoot") is not True or security.get("seccompProfile") != {"type": "RuntimeDefault"}:
            errors.append(f"{key}:RESTRICTED_POD_SECURITY_REQUIRED")
        if any(field in security for field in ("runAsUser", "runAsGroup", "fsGroup", "supplementalGroups")):
            errors.append(f"{key}:NAMESPACE_ALLOCATED_IDENTITY_REQUIRED")
        if any(pod.get(field) for field in ("hostNetwork", "hostPID", "hostIPC", "initContainers", "ephemeralContainers")):
            errors.append(f"{key}:HOST_ACCESS_OR_EXTRA_CONTAINER_FORBIDDEN")
        if any("hostPath" in volume for volume in pod.get("volumes", [])):
            errors.append(f"{key}:HOSTPATH_FORBIDDEN")
        if not any(volume.get("name") == "tmp" and "emptyDir" in volume for volume in pod.get("volumes", [])):
            errors.append(f"{key}:WRITABLE_TMP_REQUIRED")
        for container in pod.get("containers", []):
            if any(sensitive_key(field.get("name", "")) and "value" in field for field in container.get("env", [])):
                errors.append(f"{key}:CREDENTIALS_MUST_USE_EXTERNAL_SECRET_REFERENCE")
            security = container.get("securityContext", {})
            if (security.get("runAsNonRoot") is not True or security.get("allowPrivilegeEscalation") is not False
                    or security.get("readOnlyRootFilesystem") is not True
                    or security.get("capabilities") != {"drop": ["ALL"]} or security.get("privileged", False)):
                errors.append(f"{key}:RESTRICTED_CONTAINER_SECURITY_REQUIRED")
            if any(field in security for field in ("runAsUser", "runAsGroup")):
                errors.append(f"{key}:FIXED_CONTAINER_ID_FORBIDDEN")
            image = container.get("image", "")
            if not IMAGE.fullmatch(image) or ":latest" in image or image.endswith("0" * 64):
                errors.append(f"{key}:EXACT_MEASURED_IMAGE_DIGEST_REQUIRED")
            if any(port.get("hostPort") or port.get("containerPort", 0) < 1024 for port in container.get("ports", [])):
                errors.append(f"{key}:ONLY_HIGH_CONTAINER_PORTS_ALLOWED")
    return sorted(set(errors))


def inspect(root: Path = ROOT) -> dict:
    contract = json.loads((root / "draft-contract.json").read_text(encoding="utf-8"))
    resources = documents(root)
    errors = validate_resources(resources)
    if contract.get("status") != "DRAFT_NOT_DEPLOYABLE" or contract.get("release_status") != "NOT_APPROVED":
        errors.append("DRAFT_CONTRACT_CANNOT_GRANT_RELEASE_APPROVAL")
    gate_names = ("target_cluster", "security_approval", "scc_arbitrary_uid_verification",
                  "storage_csi_permissions", "private_ingress_and_tls", "backup_restore_and_schedule",
                  "secret_recovery", "operator_approval")
    hashes = {str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(root.rglob("*")) if path.is_file() and path.suffix in {".json", ".yaml", ".py", ".md"}}
    return {"contract": "OPENSHIFT_OFFLINE_DRAFT_PREFLIGHT_V1", "executed_cluster_actions": False,
            "status": "DRAFT_NOT_DEPLOYABLE", "release_status": "NOT_APPROVED",
            "technical_checks": "FAILED" if errors else "OFFLINE_CONTRACTS_VALID",
            "errors": sorted(set(errors)), "resource_count": len(resources), "artifact_sha256": hashes,
            "open_external_gates": {name: contract.get(name, "MISSING") for name in gate_names},
            "financial_gates": contract.get("financial_gates", []),
            "blockers": ["DRAFT_PACKAGE_HAS_NO_DEPLOYMENT_AUTHORITY", "EXACT_TARGET_CONFIGURATION_REQUIRES_ITS_OWN_IMMUTABLE_RELEASE_REVIEW",
                         "CLUSTER_SCC_STORAGE_TLS_BACKUP_AND_OPERATOR_EVIDENCE_NOT_AVAILABLE"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        report = inspect()
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Never include file contents, settings values or secret material in errors.
        report = {"status": "DRAFT_NOT_DEPLOYABLE", "release_status": "NOT_APPROVED",
                  "technical_checks": "FAILED", "errors": [type(error).__name__], "executed_cluster_actions": False}
    print(json.dumps(report, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
