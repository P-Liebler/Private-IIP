"""Offline contract for the opt-in GitOps start candidate.

Does not access the cluster, create images, run builds or approve release.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1] / "base"
STARTUP = ROOT.parents[2] / "gitops-startup"
PIN = "4f3b8b83e58554fd74fc21c3c338ee0af62bb07a"
TAG = "bootstrap-4f3b8b83"
NAMES = {"api", "worker", "scheduler", "web", "postgres", "valkey", "minio", "caddy"}
COMPONENTS = {"postgres": -48, "seaweed": -46, "caddy": -44, "backend": -42, "web": -40}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def operations(config, kind, name):
    return [op
            for p in config["patches"]
            if p["target"]["kind"] == kind and p["target"].get("name") == name
            for op in json.loads(p["patch"])]


cfg = load(ROOT / "kustomization.yaml")
assert cfg["namespace"] == "gitops-demo"
assert set(cfg["resources"]) == {
    "../../base", "../../../gitops-startup", "builds-application.json",
    "private-ingress-policy.yaml", "private-route.yaml",
}
assert {p["name"]: p["count"] for p in cfg["replicas"]} == dict.fromkeys(NAMES, 1)

base = load(BASE / "workloads.json")["items"]
assert {obj["metadata"]["name"] for obj in base} == NAMES
assert all(obj["spec"]["replicas"] == 0 for obj in base), "Never activate shared base"
pvc = load(BASE / "storage.json")["items"]
assert {item["metadata"]["name"] for item in pvc} == {"postgres-data", "seaweed-data", "valkey-data"}
assert all("Prune=false" in item["metadata"]["annotations"]["argocd.argoproj.io/sync-options"]
           for item in pvc)

builds = load(ROOT / "builds-application.json")["items"]
streams = [x for x in builds if x["kind"] == "ImageStream"]
configs = [x for x in builds if x["kind"] == "BuildConfig"]
assert len(streams) == 5 and len(configs) == 6, "Only one additional BuildConfig for Caddy retry"
for name, wave in COMPONENTS.items():
    bc = next(x for x in configs if x["metadata"]["name"] == "iip-" + name)
    assert bc["spec"]["source"]["git"]["ref"] == PIN
    assert bc["spec"]["source"]["git"]["uri"] == "https://github.com/P-Liebler/Private-IIP.git"
    assert bc["spec"]["output"]["to"]["name"] == f"iip-{name}:{TAG}"
    assert bc["spec"]["triggers"] == [{"type": "ConfigChange"}]
    assert int(bc["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"]) == wave

# A new BuildConfig is required because ConfigChange does not retry a failed
# existing Build on an unchanged BuildConfig. Preserve old builders and images.
retry_build = next(x for x in configs if x["metadata"]["name"] == "iip-caddy-retry-1")
original_caddy = next(x for x in configs if x["metadata"]["name"] == "iip-caddy")
assert retry_build["spec"] == original_caddy["spec"], "Retry must reproduce the exact pinned Caddy image"
assert retry_build["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "-44"
assert retry_build["spec"]["output"]["to"]["name"] == "iip-caddy:" + TAG
assert {x["metadata"]["name"] for x in configs} == (
    {"iip-" + name for name in COMPONENTS} | {"iip-caddy-retry-1"}
)

startup_cfg = load(STARTUP / "kustomization.yaml")
assert set(startup_cfg["resources"]) == {"build-waiters.json", "runtime-preflight.json", "s3-bootstrap.json", "db-bootstrap-job.json"}
assert startup_cfg["generatorOptions"]["disableNameSuffixHash"] is True
assert startup_cfg["configMapGenerator"][0]["name"] == "iip-first-use-schema"
waiters = load(STARTUP / "build-waiters.json")["items"]
role = next(x for x in waiters if x["kind"] == "Role")
assert all(rule["verbs"] == ["get"] for rule in role["rules"])
assert {x["kind"] for x in waiters} == {"Role", "RoleBinding", "ServiceAccount", "Job"}
jobs = [x for x in waiters if x["kind"] == "Job"]
assert len(jobs) == 5
for name, wave in COMPONENTS.items():
    job = next(x for x in jobs if x["metadata"]["name"] == f"iip-wait-{name}-4f3b")
    assert int(job["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"]) == wave + 1
    assert job["metadata"]["annotations"]["argocd.argoproj.io/hook"] == "Sync"
    body = job["spec"]["template"]["spec"]["containers"][0]["args"][0]
    assert "get imagestreamtag" in body and "get build" in body
    if name == "caddy":
        assert "name='iip-caddy-retry-1'" in body
        assert "stream='iip-caddy'" in body
        assert 'get buildconfig "$name"' in body
        assert 'get build "$name-$version"' in body
        assert 'get imagestreamtag "$stream:$tag"' in body
        assert 'get imagestreamtag "$name:$tag"' not in body
        assert job["metadata"]["annotations"]["argocd.argoproj.io/hook-delete-policy"] == (
            "HookSucceeded,BeforeHookCreation"
        )
    else:
        assert "name='iip-" + name + "'" in body
    assert not any(s in body for s in ("start-build", "oc delete", "oc apply", "oc patch"))

registry = "image-registry.openshift-image-registry.svc:5000/gitops-demo/"
for name in NAMES:
    kind = "StatefulSet" if name in {"postgres", "valkey", "minio"} else "Deployment"
    ops = operations(cfg, kind, name)
    images = [x["value"] for x in ops if x["path"] == "/spec/template/spec/containers/0/image"]
    expected_component = {"api": "backend", "worker": "backend", "scheduler": "backend",
                          "web": "web", "postgres": "postgres",
                          "minio": "seaweed", "caddy": "caddy"}.get(name)
    expected = f"{registry}iip-{expected_component}:{TAG}" if expected_component else "valkey/valkey:8.1.11-alpine"
    assert images == [expected], name
    annotation = [x["value"] for x in ops
                  if x["path"] == "/metadata/annotations/argocd.argoproj.io~1sync-wave"]
    assert annotation == ["-10" if name in {"postgres", "valkey", "minio", "caddy"} else "3"]

config_patches = operations(cfg, "ConfigMap", "iip-config")
origin = "https://privat-iip-gitops-demo.apps.test-slieu0202.slieu0201.local"
values = {x["path"]: x["value"] for x in config_patches if x["op"] == "replace"}
assert all(values.get(k) == v for k, v in {
    "/data/FRONTEND_ORIGIN": origin,
    "/data/API_PUBLIC_ORIGIN": origin,
    "/data/CODE_COMMIT": PIN,
}.items())
route = (ROOT / "private-route.yaml").read_text(encoding="utf-8")
assert f"host: {origin[8:]}" in route
assert 'argocd.argoproj.io/sync-wave: "4"' in route, "Do not expose route before readiness gate"
ca_patch = operations(cfg, "ConfigMap", "iip-service-ca")
assert any(x["path"].endswith("ignore-differences") and
           "/data" in x["value"] for x in ca_patch)

gate = load(STARTUP / "runtime-preflight.json")
assert gate["metadata"]["annotations"]["argocd.argoproj.io/hook"] == "Sync"
assert int(gate["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"]) == 2
preflight = gate["spec"]["template"]["spec"]["containers"][0]["args"][0]
assert "public.alembic_version" in preflight and "bucket_exists" in preflight
assert "alembic upgrade" not in preflight and "make_bucket" not in preflight

migration = load(STARTUP / "db-bootstrap-job.json")
assert migration["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "0"
assert migration["spec"]["template"]["spec"]["containers"][0]["command"] == ["python", "/bootstrap/bootstrap.py"]
script = (STARTUP / "bootstrap-schema.py").read_text(encoding="utf-8")
assert "Nonempty database without version" in script
assert 'subprocess.run(["alembic", "upgrade", "head"]' in script
assert "DROP " not in script and "truncate" not in script.lower()
s3 = load(STARTUP / "s3-bootstrap.json")["items"]
assert {x["kind"] for x in s3} == {"Service", "Job", "NetworkPolicy"}
assert len([x for x in s3 if x["kind"] == "NetworkPolicy"]) == 2
bucket_job = next(x for x in s3 if x["kind"] == "Job")
assert bucket_job["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "-1"
assert "s3.bucket.create -name raw-ingestions" in bucket_job["spec"]["template"]["spec"]["containers"][0]["args"][0]
assert "s3.bucket.delete" not in bucket_job["spec"]["template"]["spec"]["containers"][0]["args"][0]
print("PASS: offline GitOps candidate contracts; CLUSTER START NOT VERIFIED")
