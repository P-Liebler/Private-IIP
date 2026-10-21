"""Export allowlisted Docker runtime metadata; never export container environments."""
import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from security_audit import sha256, write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit-inventory", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,80}", args.project):
        parser.error("Invalid Compose project")
    ids = subprocess.check_output(["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=" + args.project], text=True).split()
    records = []
    audited = {item["component"]: item for item in json.loads(args.audit_inventory.read_text(encoding="utf-8"))["images"]} if args.audit_inventory else {}
    for identity in ids:
        value = json.loads(subprocess.check_output(["docker", "inspect", identity]))[0]
        config, host, state = value["Config"], value["HostConfig"], value["State"]
        service = config.get("Labels", {}).get("com.docker.compose.service")
        component = {"api": "backend", "worker": "backend", "scheduler": "backend", "ml-worker": "backend", "ca-export": "caddy", "backup": "minio"}.get(service, service)
        binding = audited.get(component)
        if args.audit_inventory and (not binding or binding["image_id"] != value["Image"]):
            raise ValueError("RUNTIME_AUDITED_IMAGE_MISMATCH")
        pid1_uid = None
        if state["Status"] == "running":
            observed = subprocess.run(["docker", "exec", identity, "cat", "/proc/1/status"], capture_output=True, text=True, timeout=30)
            match = re.search(r"^Uid:\s+(\d+)", observed.stdout, re.MULTILINE)
            if observed.returncode == 0 and match:
                pid1_uid = int(match.group(1))
        records.append({
            "service": service,
            "image_reference": config["Image"], "image_id": value["Image"],
            "audited_config_digest": binding["config_digest"] if binding else None,
            "configured_user": config.get("User") or "root (image default; inspect process privilege separately)",
            "observed_pid1_uid": pid1_uid,
            "state": state["Status"], "health": state.get("Health", {}).get("Status"),
            "read_only": host["ReadonlyRootfs"], "cap_drop": host.get("CapDrop"),
            "cap_add": host.get("CapAdd"), "security_opt": host.get("SecurityOpt"),
            "privileged": host["Privileged"], "network_mode": host["NetworkMode"],
            "ports": host.get("PortBindings"), "memory_limit_bytes": host["Memory"],
            "nano_cpus": host["NanoCpus"], "restart_policy": host["RestartPolicy"]["Name"],
            "mounts": [{"type": mount["Type"], "destination": mount["Destination"], "writable": mount["RW"]} for mount in value["Mounts"]],
            "tmpfs_destinations": sorted((host.get("Tmpfs") or {}).keys()),
        })
    if not records:
        raise ValueError("NO_RUNTIME_EVIDENCE")
    write_new(args.output, {"recorded_at": datetime.now(UTC).isoformat(), "project": args.project,
                           "audit_inventory_sha256": sha256(args.audit_inventory) if args.audit_inventory else None,
                           "scope": "OBSERVED_RUNTIME_CONFIGURATION_NOT_RELEASE_APPROVAL", "services": records})
    print("Runtime metadata recorded without environments")


if __name__ == "__main__":
    main()
