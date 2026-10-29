"""Inspect the exact PR9 Caddy binary and Core profile without starting a server.

This produces configuration evidence only. It cannot approve a vulnerability
exception, prove whole-program unreachability or authorize any deployment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "private-iip/caddy@sha256:6416b8c2e10d8d62b131dbf3755c01069d7b3dcdb7af720b76c8aeed8bc9dcaf"
HANDLERS = {"subroute", "headers", "encode", "static_response", "reverse_proxy"}
UPSTREAMS = {"api:8000", "web:3000", "minio:9000"}


def dictionaries(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from dictionaries(child)
    elif isinstance(value, list):
        for child in value:
            yield from dictionaries(child)


def inspect_internal_routing(config: dict[str, Any]) -> dict[str, Any]:
    """Ensure /internal/* terminates before a generic application proxy."""
    protected_groups = 0
    for node in dictionaries(config):
        routes = node.get("routes")
        if not isinstance(routes, list):
            continue
        for index, route in enumerate(routes):
            matches = route.get("match", [])
            if matches != [{"path": ["/internal/*"]}]:
                continue
            body = list(dictionaries(route.get("handle", [])))
            if any(item.get("handler") == "reverse_proxy" for item in body):
                raise ValueError("Internal path must not reach a proxy")
            if not any(item.get("handler") == "static_response"
                       and str(item.get("status_code")) == "404" for item in body):
                raise ValueError("Internal path must return terminal 404")
            for earlier in routes[:index]:
                if any(item.get("handler") == "reverse_proxy" for item in dictionaries(earlier)):
                    allowed = earlier.get("match") == [{"path": ["/api/v1/*"]}]
                    if not allowed:
                        raise ValueError("An earlier proxy can intercept the internal path")
            fallbacks = [item for item in routes[index + 1:] if not item.get("match")
                         and any(part.get("handler") == "reverse_proxy"
                                 for part in dictionaries(item))]
            if not route.get("group") or not fallbacks or any(
                item.get("group") != route["group"] for item in fallbacks
            ):
                raise ValueError("Internal 404 must precede the exclusive fallback proxy")
            protected_groups += 1
    if protected_groups != 1:
        raise ValueError("Expected one reviewed internal-path protection group")
    return {"internal_terminal_404_before_application_proxy": True}


def inspect_profile(config: dict[str, Any]) -> dict[str, Any]:
    """Reject changes that would invalidate this narrow JWK exposure review."""
    apps = config.get("apps", {})
    if not isinstance(apps, dict) or set(apps) - {"http", "tls", "pki"}:
        raise ValueError("Unexpected Caddy app; a new exposure review is required")
    servers = apps.get("http", {}).get("servers", {})
    if not servers or any(set(server.get("protocols", [])) != {"h1", "h2"}
                          for server in servers.values()):
        raise ValueError("TCP-only deployment must not advertise an unavailable HTTP/3 port")
    nodes = list(dictionaries(config))
    handlers = {n["handler"] for n in nodes if "handler" in n}
    if not handlers or handlers - HANDLERS:
        raise ValueError("Unexpected handler, including possible ACME/JWK input")
    issuers = {n["module"] for n in nodes if "module" in n}
    if issuers != {"internal"}:
        raise ValueError("Core must use explicit internal issuers in this review")
    if any(n.get("on_demand") or "ask" in n for n in nodes):
        raise ValueError("On-demand certificate policy requires a new review")
    upstreams = {n["dial"] for n in nodes if "dial" in n}
    if upstreams != UPSTREAMS:
        raise ValueError("Core upstream targets differ from the reviewed profile")
    admin = config.get("admin", {})
    if not isinstance(admin, dict) or admin.get("remote") or admin.get("identity"):
        raise ValueError("Remote administration requires a new review")
    listen = admin.get("listen", "localhost:2019")
    if not admin.get("disabled") and listen not in {
        "localhost:2019", "127.0.0.1:2019", "[::1]:2019"
    }:
        raise ValueError("Administration is not at the reviewed loopback endpoint")
    result = {
        "status": "STATIC_PROFILE_REVIEW_ONLY",
        "handlers": sorted(handlers),
        "issuers": sorted(issuers),
        "upstreams": sorted(upstreams),
        "configured_acme_server": False,
        "configured_on_demand": False,
        "admin": "disabled" if admin.get("disabled") else listen,
        "admin_default_inferred": "admin" not in config,
        "whole_program_unreachability_proven": False,
        "security_approved": False,
        "http_protocols": ["h1", "h2"],
    }
    result.update(inspect_internal_routing(config))
    return result


def run(image: str, output: Path) -> dict[str, Any]:
    if not re.fullmatch(r"private-iip/caddy@sha256:[0-9a-f]{64}", image):
        raise ValueError("A local digest-pinned Caddy image is required")
    source = ROOT / "ops/caddy/Core.Caddyfile"
    prefix = [
        "docker", "run", "--rm", "--pull=never", "--network=none", "--read-only",
        "--cap-drop=ALL", "--security-opt=no-new-privileges:true", "--memory=256m",
        "--cpus=1", "--user=10001:10001", "--tmpfs=/tmp:rw,nosuid,nodev,size=16m",
        "--entrypoint=caddy",
    ]

    def capture(args: list[str]) -> bytes:
        result = subprocess.run(args, check=False, capture_output=True, timeout=60)
        if result.returncode or len(result.stdout) > 2_000_000:
            raise RuntimeError("The bounded offline Caddy probe did not complete")
        return result.stdout

    image_id = capture(["docker", "image", "inspect", image, "--format", "{{.Id}}"])
    image_user = capture(["docker", "image", "inspect", image, "--format", "{{.Config.User}}"])
    module_bytes = capture([*prefix, image, "list-modules", "--versions"])
    build_bytes = capture([*prefix, image, "build-info"])
    config_bytes = capture([
        *prefix, "--env=APP_DOMAIN=private-iip.invalid",
        "--mount", f"type=bind,src={source},dst=/review/Core.Caddyfile,readonly",
        image, "adapt", "--config=/review/Core.Caddyfile", "--adapter=caddyfile",
    ])
    config = json.loads(config_bytes)
    result = inspect_profile(config)
    openshift_source = ROOT / "ops/openshift/base/caddy-config.json"
    openshift_bytes = openshift_source.read_bytes()
    openshift_config = json.loads(openshift_bytes)["data"]["Caddyfile"]
    with tempfile.TemporaryDirectory(prefix="pr10-caddy-profile-") as tmp:
        config_path = Path(tmp) / "OpenShift.Caddyfile"
        config_path.write_text(openshift_config, encoding="utf-8")
        openshift_adapted = capture([
            *prefix, "--mount", f"type=bind,src={config_path},dst=/review/Caddyfile,readonly",
            image, "adapt", "--config=/review/Caddyfile", "--adapter=caddyfile",
        ])
    result["openshift_routing"] = inspect_internal_routing(json.loads(openshift_adapted))
    result.update({
        "checked_at": datetime.now(UTC).isoformat(),
        "image": image,
        "image_id": image_id.decode("utf-8").strip(),
        "image_default_user": image_user.decode("utf-8").strip(),
        "probe_user": "10001:10001",
        "probe_is_production_deployment": False,
        "probe_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "caddyfile_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "adapted_config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "registered_modules_sha256": hashlib.sha256(module_bytes).hexdigest(),
        "build_info_sha256": hashlib.sha256(build_bytes).hexdigest(),
        "openshift_configmap_sha256": hashlib.sha256(openshift_bytes).hexdigest(),
        "openshift_adapted_sha256": hashlib.sha256(openshift_adapted).hexdigest(),
        "acme_server_registered": "http.handlers.acme_server" in module_bytes.decode("utf-8"),
        "go_jose_v3_in_build": "github.com/go-jose/go-jose/v3\tv3.0.5" in build_bytes.decode("utf-8"),
        "server_started": False,
        "network": "none",
    })
    output.mkdir(parents=True, exist_ok=False)
    for name, content in (("adapted.json", config_bytes), ("modules.txt", module_bytes),
                          ("build-info.txt", build_bytes),
                          ("openshift-adapted.json", openshift_adapted)):
        (output / name).write_bytes(content)
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default=IMAGE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = run(args.image, args.output)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        print("CADDY_PROFILE_PROBE_INCOMPLETE: no security or deployment approval")
        return 2
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
