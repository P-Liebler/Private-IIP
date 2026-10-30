"""Offline contract for the opt-in GitOps start candidate.

Does not access the cluster, create images, run builds or approve release.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1] / "base"
STARTUP = ROOT.parents[2] / "gitops-startup"
PIN = "dbf6b892f16f380f4784acf1884ef964f7a13e8a"
TAG = "bootstrap-dbf6b892"
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
assert len(streams) == len(configs) == 5
for name, wave in COMPONENTS.items():
    bc = next(x for x in configs if x["metadata"]["name"] == "iip-" + name)
    assert bc["spec"]["source"]["git"]["ref"] == PIN
    assert bc["spec"]["source"]["git"]["uri"] == "https://github.com/P-Liebler/Private-IIP.git"
    assert bc["spec"]["output"]["to"]["name"] == f"iip-{name}:{TAG}"
    assert bc["spec"]["triggers"] == [{"type": "ConfigChange"}]
    assert int(bc["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"]) == wave

assert set(load(STARTUP / "kustomization.yaml")["resources"]) == {"build-waiters.json", "runtime-preflight.json"}
waiters = load(STARTUP / "build-waiters.json")["items"]
role = next(x for x in waiters if x["kind"] == "Role")
assert all(rule["verbs"] == ["get"] for rule in role["rules"])
assert {x["kind"] for x in waiters} == {"Role", "RoleBinding", "ServiceAccount", "Job"}
jobs = [x for x in waiters if x["kind"] == "Job"]
assert len(jobs) == 5
for name, wave in COMPONENTS.items():
    job = next(x for x in jobs if x["metadata"]["name"] == f"iip-wait-{name}-dbf6")
    assert int(job["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"]) == wave + 1
    assert job["metadata"]["annotations"]["argocd.argoproj.io/hook"] == "Sync"
    body = job["spec"]["template"]["spec"]["containers"][0]["args"][0]
    assert "get imagestreamtag" in body and "get build" in body
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
    assert annotation == ["-10" if name in {"postgres", "valkey", "minio", "caddy"} else "2"]

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
assert int(gate["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"]) == 1
preflight = gate["spec"]["template"]["spec"]["containers"][0]["args"][0]
assert "public.alembic_version" in preflight and "bucket_exists" in preflight
assert "alembic upgrade" not in preflight and "make_bucket" not in preflight

print("PASS: offline GitOps candidate contracts; CLUSTER START NOT VERIFIED")
