"""Static checks for the Argo-managed gitops-demo bootstrap (no cluster actions)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1] / "base"
config = json.loads((ROOT / "kustomization.yaml").read_text(encoding="utf-8"))
assert config["namespace"] == "gitops-demo"
assert set(config["resources"]) == {
    "../../base", "builds-application.json",
    "private-ingress-policy.yaml", "private-route.yaml",
}
workloads = json.loads((BASE / "workloads.json").read_text(encoding="utf-8"))["items"]
names = {o["metadata"]["name"] for o in workloads}
assert names == {"api", "web", "worker", "scheduler", "postgres", "valkey", "minio", "caddy"}
assert {p["name"]: p["count"] for p in config["replicas"]} == dict.fromkeys(names, 1)

def operations(kind, name):
    return [
        op
        for patch in config["patches"]
        if patch["target"]["kind"] == kind and patch["target"].get("name") == name
        for op in json.loads(patch["patch"])
    ]

patches = {p["target"].get("name"): json.loads(p["patch"])
           for p in config["patches"] if p["target"]["kind"] == "NetworkPolicy"}
assert operations("ConfigMap", "iip-config")[0]["value"] == "caddy.gitops-demo.svc:9002"
assert any(
    op["path"] == "/metadata/annotations/argocd.argoproj.io~1ignore-differences"
    and "/data/service-ca.crt" in op["value"]
    for op in operations("ConfigMap", "iip-service-ca")
)
base_policies = json.loads((BASE / "network-policies.json").read_text(encoding="utf-8"))["items"]
assert {p["metadata"]["name"] for p in base_policies} == set(patches) - {None}
for policy in base_policies:
    name = policy["metadata"]["name"]
    changes = patches[name]
    assert any(op["path"].startswith("/spec/podSelector") and (
        op.get("value") == "investment" or
        op.get("value") == {"matchLabels": {"app.kubernetes.io/part-of": "investment"}}
    ) for op in changes), name
    for direction in ("ingress", "egress"):
        field = "from" if direction == "ingress" else "to"
        for i, rule in enumerate(policy["spec"].get(direction, [])):
            for j, peer in enumerate(rule.get(field, [])):
                if "podSelector" in peer and "namespaceSelector" not in peer:
                    expect = f"/spec/{direction}/{i}/{field}/{j}/podSelector/matchLabels/app.kubernetes.io~1part-of"
                    assert any(op["path"] == expect and op["value"] == "investment" for op in changes), name

expected = {"api": "backend", "worker": "backend", "scheduler": "backend",
            "web": "web", "postgres": "postgres", "minio": "seaweed", "caddy": "caddy"}
for name, component in expected.items():
    kind = "StatefulSet" if name in {"postgres", "minio"} else "Deployment"
    images = [op["value"] for op in operations(kind, name)
              if op["path"] == "/spec/template/spec/containers/0/image"]
    assert images == [f"image-registry.openshift-image-registry.svc:5000/gitops-demo/iip-{component}:bootstrap-907851de"], name
assert any(op["value"].startswith("valkey/valkey:8.1.")
           for op in operations("StatefulSet", "valkey")
           if op["path"] == "/spec/template/spec/containers/0/image")

builds = json.loads((ROOT / "builds-application.json").read_text(encoding="utf-8"))["items"]
assert len([obj for obj in builds if obj["kind"] == "ImageStream"]) == 5
configs = [obj for obj in builds if obj["kind"] == "BuildConfig"]
assert len(configs) == 5
for obj in configs:
    assert obj["spec"]["source"]["git"]["uri"] == "https://github.com/P-Liebler/Private-IIP.git"
    assert obj["spec"]["source"]["git"]["ref"] == "907851def4f1851068d3a076ec0acdceb272aee6"
    assert {"type": "ConfigChange"} in obj["spec"]["triggers"]
assert "termination: reencrypt" in (ROOT / "private-route.yaml").read_text()
assert "port: 8443" in (ROOT / "private-ingress-policy.yaml").read_text()
print("gitops-demo manifests statically checked; target startup and release approval NOT VERIFIED")
