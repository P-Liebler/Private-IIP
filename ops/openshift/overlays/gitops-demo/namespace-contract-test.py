"""Offline, non-mutating checks for the gitops-demo namespace adaptation."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
config = json.loads((ROOT / "kustomization.yaml").read_text(encoding="utf-8"))
assert config["namespace"] == "gitops-demo"
assert config["resources"] == ["../../base"]
patches = {p["target"]["name"]: json.loads(p["patch"]) for p in config["patches"]}
assert patches["iip-config"][0]["value"] == "caddy.gitops-demo.svc:9002"
for name in ("default-deny", "dns-only"):
    assert patches[name][0]["value"] == {"matchLabels": {"app.kubernetes.io/part-of": "investment"}}
print("gitops-demo overlay static checks OK; deployment NOT APPROVED")
