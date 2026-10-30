"""Static read-only checks: emergency-disabled gitops-demo overlay."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1] / "base"
cfg = json.loads((ROOT / "kustomization.yaml").read_text(encoding="utf-8"))
assert cfg["namespace"] == "gitops-demo"
assert cfg["resources"] == ["../../base"]
assert not cfg.get("replicas"), "IIP must remain scaled to zero"
assert "builds-application.json" not in cfg["resources"]
assert "private-route.yaml" not in cfg["resources"]

workloads = json.loads((BASE / "workloads.json").read_text(encoding="utf-8"))["items"]
assert {o["metadata"]["name"] for o in workloads} == {
    "api", "worker", "scheduler", "web", "postgres", "valkey", "minio", "caddy"
}
assert all(o["spec"]["replicas"] == 0 for o in workloads)

patches = {
    (p["target"]["kind"], p["target"].get("name")): json.loads(p["patch"])
    for p in cfg["patches"]
}
ca = patches[("ConfigMap", "iip-service-ca")]
assert any(op["path"].endswith("ignore-differences") and
           "/data/service-ca.crt" in op["value"] for op in ca)
assert patches[("ConfigMap", "iip-config")][0]["value"] == "caddy.gitops-demo.svc:9002"

network_policies = json.loads((BASE / "network-policies.json").read_text(encoding="utf-8"))["items"]
for policy in network_policies:
    name = policy["metadata"]["name"]
    changes = patches[("NetworkPolicy", name)]
    assert any(op["path"].startswith("/spec/podSelector") and (
        op.get("value") == "investment" or
        op.get("value") == {"matchLabels": {"app.kubernetes.io/part-of": "investment"}}
    ) for op in changes), name
    for direction in ("ingress", "egress"):
        field = "from" if direction == "ingress" else "to"
        for i, rule in enumerate(policy["spec"].get(direction, [])):
            for j, peer in enumerate(rule.get(field, [])):
                if "podSelector" in peer and "namespaceSelector" not in peer:
                    expected = f"/spec/{direction}/{i}/{field}/{j}/podSelector/matchLabels/app.kubernetes.io~1part-of"
                    assert any(op["path"] == expected and op["value"] == "investment"
                               for op in changes), name
print("gitops-demo disabled base configuration validated (no cluster action)")
