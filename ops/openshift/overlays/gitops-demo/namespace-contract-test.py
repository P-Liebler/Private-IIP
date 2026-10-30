"""Static checks for the gitops-demo draft overlay; no cluster operations."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1] / "base" / "network-policies.json"
config = json.loads((ROOT / "kustomization.yaml").read_text(encoding="utf-8"))
assert config["namespace"] == "gitops-demo"
assert config["resources"] == ["../../base"]
patches = {p["target"]["name"]: json.loads(p["patch"]) for p in config["patches"]}
assert patches["iip-config"][0]["value"] == "caddy.gitops-demo.svc:9002"
base_policies = json.loads(BASE.read_text(encoding="utf-8"))["items"]
assert {p["metadata"]["name"] for p in base_policies} == set(patches) - {"iip-config"}
for policy in base_policies:
    name = policy["metadata"]["name"]
    changes = patches[name]
    assert any(op["path"].startswith("/spec/podSelector") and
               (op.get("value") == "investment" or
                op.get("value") == {"matchLabels": {"app.kubernetes.io/part-of": "investment"}})
               for op in changes), name
    for direction in ("ingress", "egress"):
        field = "from" if direction == "ingress" else "to"
        for i, rule in enumerate(policy["spec"].get(direction, [])):
            for j, peer in enumerate(rule.get(field, [])):
                if "podSelector" in peer and "namespaceSelector" not in peer:
                    expect = f"/spec/{direction}/{i}/{field}/{j}/podSelector/matchLabels/app.kubernetes.io~1part-of"
                    assert any(op["path"] == expect and op["value"] == "investment" for op in changes), name
print("gitops-demo draft selector guards checked; NOT APPROVED")
