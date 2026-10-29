"""Offline OpenShift contracts; no cluster, Docker or financial provider calls."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "ops/openshift"
module_spec = importlib.util.spec_from_file_location("openshift_draft_preflight", ROOT / "preflight.py")
preflight = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(preflight)


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def base_resources():
    result = []
    for path in sorted((ROOT / "base").glob("*.json")):
        result.extend(preflight.expand(json.loads(path.read_text(encoding="utf-8"))))
    return result


def named(resources, kind, name):
    return next(obj for obj in resources if obj["kind"] == kind and obj["metadata"]["name"] == name)


def container(obj):
    return obj["spec"]["template"]["spec"]["containers"][0]


class OpenShiftManifestTests(unittest.TestCase):
    def setUp(self):
        self.resources = base_resources()
        self.workloads = {obj["metadata"]["name"]: obj for obj in self.resources
                          if obj["kind"] in {"Deployment", "StatefulSet"}}

    def test_preflight_is_offline_and_never_issues_a_release(self):
        report = preflight.inspect()
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["technical_checks"], "OFFLINE_CONTRACTS_VALID")
        self.assertEqual(report["status"], "DRAFT_NOT_DEPLOYABLE")
        self.assertEqual(report["release_status"], "NOT_APPROVED")
        self.assertFalse(report["executed_cluster_actions"])
        self.assertTrue(report["blockers"])
        self.assertIn("base/workloads.json", report["artifact_sha256"])
        process = subprocess.run([sys.executable, str(ROOT / "preflight.py")], capture_output=True, text=True, timeout=10)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(json.loads(process.stdout)["status"], "DRAFT_NOT_DEPLOYABLE")

    def test_core_is_disabled_and_staging_is_a_separate_explicit_opt_in(self):
        self.assertEqual(set(self.workloads), {"api", "web", "worker", "scheduler", "postgres", "valkey", "minio", "caddy"})
        self.assertTrue(all(obj["spec"]["replicas"] == 0 for obj in self.workloads.values()))
        stage = load("overlays/staging/kustomization.yaml")
        self.assertEqual(stage["namespace"], "investment-staging")
        self.assertEqual({row["name"]: row["count"] for row in stage["replicas"]}, dict.fromkeys(self.workloads, 1))
        self.assertEqual(self.workloads["scheduler"]["spec"]["strategy"], {"type": "Recreate"})
        for name in ("postgres", "valkey", "minio"):
            self.assertEqual(self.workloads[name]["kind"], "StatefulSet")
        optional = preflight.expand(load("components/prometheus/resources.json"))
        self.assertEqual(named(optional, "Deployment", "prometheus")["spec"]["replicas"], 0)

    def test_every_image_preserves_the_exact_current_core_candidate_digest(self):
        scope = json.loads((REPO / "ops/releases/pr10-core-v1-scope.json").read_text())["services"]
        for name, obj in self.workloads.items():
            reference = container(obj)["image"]
            self.assertRegex(reference, r"^registry\.invalid/investment/.+@sha256:[0-9a-f]{64}$")
            self.assertEqual(reference.split("@")[1], scope[name]["image"].split("@")[1])
        job = load("manual/migration-job.json")
        self.assertEqual(container(job)["image"], container(self.workloads["api"])["image"])
        source = (ROOT / "preflight.py").read_text()
        self.assertNotIn("subprocess", source)

    def test_restricted_v2_requirements_apply_to_all_containers_without_uid_or_scc_escape(self):
        self.assertEqual(preflight.validate_resources(preflight.documents(ROOT)), [])
        for obj in self.workloads.values():
            pod = preflight.pod_spec(obj)
            self.assertFalse(pod["automountServiceAccountToken"])
            self.assertEqual(pod["securityContext"]["seccompProfile"], {"type": "RuntimeDefault"})
            self.assertNotIn("runAsUser", pod["securityContext"])
            self.assertNotIn("fsGroup", pod["securityContext"])
            self.assertNotIn("initContainers", pod)
        mutated = copy.deepcopy(list(self.workloads.values()))
        container(mutated[0])["securityContext"]["privileged"] = True
        container(mutated[1])["image"] = "fixture:latest"
        mutated[2]["spec"]["template"]["spec"]["securityContext"]["runAsUser"] = 10001
        errors = "\n".join(preflight.validate_resources(mutated))
        self.assertIn("RESTRICTED_CONTAINER_SECURITY_REQUIRED", errors)
        self.assertIn("EXACT_MEASURED_IMAGE_DIGEST_REQUIRED", errors)
        self.assertIn("NAMESPACE_ALLOCATED_IDENTITY_REQUIRED", errors)

    def test_settings_and_secret_contracts_match_across_backend_roles(self):
        config = named(self.resources, "ConfigMap", "iip-config")["data"]
        self.assertEqual(config["APP_ENV"], "production")
        self.assertEqual(config["MINIO_SECURE"], "true")
        self.assertEqual(config["MINIO_ENDPOINT"], "caddy.investment-draft.svc:9002")
        self.assertEqual(config["MINIO_CA_CERT_PATH"], "/service-ca/service-ca.crt")
        secret_names = {"DATABASE_URL", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "TOTP_ENCRYPTION_KEY"}
        expected = container(self.workloads["api"])["env"]
        for name in ("api", "worker", "scheduler"):
            current = container(self.workloads[name])
            self.assertEqual(current["env"], expected)
            self.assertEqual(current["envFrom"], [{"configMapRef": {"name": "iip-config"}}])
            for field in current["env"]:
                if field["name"] in secret_names:
                    self.assertEqual(field["valueFrom"]["secretKeyRef"]["key"], field["name"])
                    self.assertNotIn("value", field)
        self.assertTrue(secret_names.isdisjoint(config))
        self.assertFalse(any(obj["kind"] == "Secret" for obj in preflight.documents(ROOT)))
        for key in ("SEC_ENABLED", "DATA_COLLECTION_ENABLED", "FORWARD_SHADOW_ENABLED", "ASSISTANT_TEST_MODE"):
            self.assertEqual(config[key], "false")
        mutation = copy.deepcopy(named(self.resources, "ConfigMap", "iip-config"))
        mutation["data"]["POSTGRES_PASSWORD"] = "fixture-only-forbidden-literal"
        self.assertIn("CREDENTIALS_MUST_NOT_BE_CONFIGMAP_DATA", " ".join(preflight.validate_resources([mutation])))

    def test_probes_and_writable_paths_follow_real_app_contracts(self):
        api = container(self.workloads["api"])
        self.assertEqual(api["livenessProbe"]["httpGet"]["path"], "/api/v1/health/live")
        self.assertEqual(api["readinessProbe"]["httpGet"]["path"], "/api/v1/health/ready")
        self.assertGreater(api["readinessProbe"]["timeoutSeconds"], 4)
        worker = container(self.workloads["worker"])
        probe = worker["readinessProbe"]["exec"]["command"]
        self.assertEqual(probe[:2], ["python", "-c"])
        self.assertIn("destination=[name]", probe[-1])
        self.assertIn("worker@", probe[-1])
        self.assertIn("--queues=celery", worker["args"])
        web = container(self.workloads["web"])
        self.assertIn("/app/.next/cache", {mount["mountPath"] for mount in web["volumeMounts"]})
        minio = container(self.workloads["minio"])
        self.assertIn("-ip=$(POD_IP)", minio["args"])
        self.assertEqual(minio["env"][0]["valueFrom"]["fieldRef"]["fieldPath"], "status.podIP")

    def test_service_ca_and_internal_proxy_keep_tls_and_metrics_private(self):
        service = named(self.resources, "Service", "caddy")
        self.assertEqual(service["metadata"]["annotations"]["service.beta.openshift.io/serving-cert-secret-name"], "iip-caddy-serving-cert")
        config = named(self.resources, "ConfigMap", "iip-service-ca")
        self.assertEqual(config["metadata"]["annotations"]["service.beta.openshift.io/inject-cabundle"], "true")
        self.assertEqual(config["data"], {})
        caddy = named(self.resources, "ConfigMap", "iip-caddy")["data"]["Caddyfile"]
        self.assertIn("tls /certs/tls.crt /certs/tls.key", caddy)
        self.assertIn("@internal path /internal/*", caddy)
        self.assertIn("handle @internal {\n        respond 404\n    }", caddy)
        self.assertNotIn("respond @internal 404", caddy)
        self.assertIn("protocols h1 h2", caddy)
        self.assertNotIn("tls internal", caddy)
        self.assertFalse(any(obj["kind"] in {"Route", "Ingress"} for obj in self.resources))

    def test_network_policies_deny_external_and_unbounded_traffic(self):
        deny = named(self.resources, "NetworkPolicy", "default-deny")["spec"]
        self.assertEqual(deny, {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]})
        dns = named(self.resources, "NetworkPolicy", "dns-only")["spec"]["egress"][0]
        self.assertEqual(dns["to"][0]["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"], "openshift-dns")
        backend = named(self.resources, "NetworkPolicy", "backend-egress")["spec"]["egress"]
        self.assertEqual({(row["to"][0]["podSelector"]["matchLabels"]["app.kubernetes.io/name"], row["ports"][0]["port"]) for row in backend}, {("postgres", 5432), ("valkey", 6379), ("caddy", 9002)})
        caddy = named(self.resources, "NetworkPolicy", "caddy-traffic")["spec"]["ingress"]
        self.assertEqual({port["port"] for row in caddy for port in row["ports"]}, {9002})
        mutation = copy.deepcopy(named(self.resources, "NetworkPolicy", "backend-egress"))
        mutation["spec"]["egress"].append({"to": [{"ipBlock": {"cidr": "0.0.0.0/0"}}], "ports": [{"port": 443}]})
        self.assertIn("UNBOUNDED_NETWORK_ACCESS_FORBIDDEN", " ".join(preflight.validate_resources([mutation])))

    def test_storage_and_migration_preserve_manual_audit_boundaries(self):
        claims = [obj for obj in self.resources if obj["kind"] == "PersistentVolumeClaim"]
        self.assertEqual({obj["metadata"]["name"] for obj in claims}, {"postgres-data", "valkey-data", "seaweed-data"})
        for claim in claims:
            self.assertEqual(claim["metadata"]["annotations"]["argocd.argoproj.io/sync-options"], "Prune=false,Delete=false")
            self.assertNotIn("volumeName", claim["spec"])
        job = load("manual/migration-job.json")
        self.assertTrue(job["spec"]["suspend"])
        self.assertEqual(job["spec"]["backoffLimit"], 0)
        self.assertEqual(container(job)["command"] + container(job)["args"], ["alembic", "upgrade", "head"])
        self.assertNotIn("ttlSecondsAfterFinished", job["spec"])
        self.assertNotIn("argocd.argoproj.io/hook", job["metadata"]["annotations"])
        self.assertFalse(any(obj["kind"] == "Job" for obj in self.resources))

    def test_gitops_app_is_manual_and_rbac_cannot_apply_secrets_jobs_or_cluster_resources(self):
        app = load("examples/argocd/application.json")
        self.assertEqual(app["metadata"]["namespace"], "openshift-gitops")
        self.assertEqual(app["spec"]["source"]["path"], "ops/openshift/overlays/staging")
        self.assertNotIn("automated", app["spec"]["syncPolicy"])
        self.assertNotIn("finalizers", app["metadata"])
        project = load("examples/argocd/project.json")["spec"]
        self.assertEqual(project["clusterResourceWhitelist"], [])
        allowed = {row["kind"] for row in project["namespaceResourceWhitelist"]}
        self.assertTrue({"Secret", "Job", "Role", "RoleBinding", "Route"}.isdisjoint(allowed))
        role = load("bootstrap/gitops-role.json")
        self.assertEqual(preflight.validate_resources([role]), [])
        self.assertFalse(any("delete" in rule["verbs"] for rule in role["rules"]))
        self.assertNotIn("argocd.argoproj.io/managed-by", load("bootstrap/namespace.json")["metadata"]["labels"])

    def test_writer_identity_is_shared_by_controller_and_pods_for_backup_quiescence(self):
        writers = {"api", "web", "worker", "scheduler"}
        for name, obj in self.workloads.items():
            if name in writers:
                for labels in (obj["metadata"]["labels"], obj["spec"]["template"]["metadata"]["labels"]):
                    self.assertEqual(labels["investment.local/backup-writer"], "true")
                    self.assertEqual(labels["investment.local/writer-role"], name)
            else:
                self.assertNotIn("investment.local/backup-writer", obj["metadata"]["labels"])

    def test_manual_backup_agent_is_isolated_and_not_owned_by_the_application(self):
        resources = preflight.expand(load("manual/backup-agent.json"))
        self.assertEqual(preflight.validate_resources(resources), [])
        pod = named(resources, "Pod", "backup-agent")["spec"]
        self.assertEqual(pod["nodeSelector"], {"investment.local/backup-approved": "REPLACE_AFTER_REVIEW"})
        self.assertEqual(pod["containers"][0]["env"][0]["valueFrom"]["secretKeyRef"]["name"], "iip-backup-client")
        self.assertEqual(pod["volumes"][1]["persistentVolumeClaim"]["claimName"], "backup-stage")
        self.assertEqual(pod["volumes"][2]["configMap"]["items"], [{"key": "service-ca.crt", "path": "root.crt"}])
        paths = load("base/kustomization.yaml")["resources"]
        self.assertFalse(any("manual" in path for path in paths))

    def test_kustomize_renders_base_staging_and_optional_prometheus_without_cluster(self):
        binary = shutil.which("kustomize") or shutil.which("kubectl")
        if not binary:
            self.skipTest("No optional local Kustomize/kubectl binary; static contracts still run")
        prefix = [binary, "build"] if Path(binary).stem.lower() == "kustomize" else [binary, "kustomize"]
        for name, count in (("example", 0), ("staging", 1)):
            result = subprocess.run([*prefix, str(ROOT / "overlays" / name)], capture_output=True, text=True, check=True, timeout=30)
            replicas = re.findall(r"^  replicas: (\d+)$", result.stdout, re.M)
            self.assertEqual(replicas, [str(count)] * 8)
            self.assertNotRegex(result.stdout, r"^kind: (Route|Ingress|Job|Secret|Role|RoleBinding)$")
            if name == "staging":
                self.assertIn("MINIO_ENDPOINT: caddy.investment-staging.svc:9002", result.stdout)
                self.assertIn("image: registry.invalid/replace-project/", result.stdout)
        result = subprocess.run([*prefix, str(ROOT / "overlays/staging-infra")], capture_output=True, text=True, check=True, timeout=30)
        counts = {}
        for document in result.stdout.split("\n---\n"):
            if re.search(r"^kind: (Deployment|StatefulSet)$", document, re.M):
                counts[re.search(r"^  name: (.+)$", document, re.M)[1]] = int(re.search(r"^  replicas: (\d+)$", document, re.M)[1])
        self.assertEqual(counts, {name: 0 if name in {"api", "web", "worker", "scheduler"} else 1 for name in self.workloads})
        with tempfile.TemporaryDirectory(dir=ROOT, prefix="render-test-") as directory:
            path = Path(directory)
            (path / "kustomization.yaml").write_text(json.dumps({"apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization", "resources": ["../base"], "components": ["../components/prometheus"]}))
            result = subprocess.run([*prefix, str(path)], capture_output=True, text=True, check=True, timeout=30)
            self.assertEqual(re.findall(r"^  replicas: (\d+)$", result.stdout, re.M), ["0"] * 9)
            self.assertIn("name: prometheus", result.stdout)


if __name__ == "__main__":
    unittest.main()
