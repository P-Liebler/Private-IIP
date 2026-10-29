"""Build a measured Trixie runtime filesystem, never an apt removal recipe.

Run only in the trusted, digest-pinned build stage. Keep the Python Core runtime;
copy its native linkage closure and explicit TLS/TZ/NSS resources.
Debian metadata remains available for vulnerability and license identification.
"""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path("/runtime-root")
PYTHON = Path("/usr/local")
MANIFEST = Path("/usr/share/private-iip/runtime-closure.json")
# Core is a web/API/worker service with argparse operator commands. It does not
# provide a TUI, interactive line editing or a desktop GUI. UUID identifiers use
# Python's cryptographic uuid4; the standard-library pure-Python UUID fallback
# remains available. These exclusions are versioned, measured and tested; no
# locked distribution or numerical extension is excluded.
EXCLUDED_OPTIONAL_MODULES = {"_curses", "_curses_panel", "readline", "_uuid", "_tkinter"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_file(path: Path) -> None:
    destination = ROOT / path.relative_to("/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Dereference OS library aliases: no undeclared parent /lib -> /usr/lib link
    # or target outside this filesystem is required by the final loader.
    shutil.copy2(path, destination, follow_symlinks=True)


def locked_versions() -> dict[str, str]:
    versions = {}
    for name in ("requirements.lock", "requirements-assistant.lock"):
        for package, version in re.findall(
            r"^([A-Za-z0-9_.-]+)==([^\s]+)$", Path("/app", name).read_text(), re.M,
        ):
            actual = importlib.metadata.version(package)
            if actual != version:
                raise ValueError(f"LOCKED_VERSION_MISMATCH:{package}")
            versions[package] = actual
    return versions


def main() -> None:
    if ROOT.exists():
        raise ValueError("RUNTIME_ROOT_ALREADY_EXISTS")
    versions = locked_versions()
    subprocess.run(["python", "-m", "pip", "check"], check=True)
    ROOT.mkdir()
    shutil.copytree(PYTHON, ROOT / "usr/local", symlinks=True)
    excluded = {}
    for path in sorted((PYTHON / "lib/python3.12/lib-dynload").glob("*.so")):
        if path.name.split(".", 1)[0] in EXCLUDED_OPTIONAL_MODULES:
            excluded[str(path)] = digest(path)
            (ROOT / path.relative_to("/")).unlink()
    if {Path(name).name.split(".", 1)[0] for name in excluded} != EXCLUDED_OPTIONAL_MODULES:
        raise ValueError("OPTIONAL_MODULE_PROFILE_CHANGED")
    # Include all ELF objects, not just modules exercised by a single smoke run.
    elfs = []
    for path in sorted(PYTHON.rglob("*")):
        if str(path) in excluded:
            continue
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as stream:
                if stream.read(4) == b"\x7fELF":
                    elfs.append(path)
    nss_modules = sorted(Path("/usr/lib/x86_64-linux-gnu").glob("libnss_*.so*"))
    elfs.extend(nss_modules)
    dependencies = set()
    for path in elfs:
        result = subprocess.run(["ldd", str(path)], capture_output=True, text=True, check=False)
        if result.returncode and "not a dynamic executable" not in result.stderr:
            raise ValueError(f"LDD_FAILED:{path}")
        missing = set(re.findall(r"^\s*(\S+) => not found$", result.stdout, re.M))
        if missing:
            raise ValueError(f"UNRESOLVED_NATIVE_DEPENDENCY:{path}")
        for name in re.findall(r"(?:=>\s+|^\s*)(/\S+)\s+\(", result.stdout, re.M):
            dependencies.add(Path(name))
    for path in sorted(dependencies):
        if not path.is_relative_to(PYTHON):
            copy_file(path)
            if path.resolve() != path:
                copy_file(path.resolve())
    resources = ("/etc/ssl", "/usr/lib/ssl", "/usr/share/zoneinfo", "/usr/lib/locale/C.utf8")
    for name in resources:
        path = Path(name)
        if not path.is_dir():
            raise ValueError(f"RUNTIME_RESOURCE_MISSING:{name}")
        shutil.copytree(path, ROOT / path.relative_to("/"), symlinks=False, dirs_exist_ok=True)
    # Current glibc implements DNS/files NSS internally. Retain the runtime
    # configuration and every installed libnss module for compatibility.
    for path in nss_modules:
        copy_file(path)
        if path.resolve() != path:
            copy_file(path.resolve())
        dependencies.add(path)
    for name in ("/etc/nsswitch.conf", "/etc/host.conf", "/etc/gai.conf", "/etc/os-release", "/etc/debian_version", "/etc/ld.so.cache"):
        if Path(name).is_file():
            copy_file(Path(name))
    # Package metadata identifies actual selected files, including data files.
    # No package manager or administrative binaries are copied into this image.
    selected = {str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_file()}
    packages = set()
    package_lists = {}
    for listing in Path("/var/lib/dpkg/info").glob("*.list"):
        entries = set(line.lstrip("/") for line in listing.read_text().splitlines())
        if entries.intersection(selected):
            packages.add(listing.name.removesuffix(".list"))
            package_lists[listing.name] = sorted("/" + entry for entry in entries.intersection(selected))
    statuses = []
    for stanza in Path("/var/lib/dpkg/status").read_text().strip().split("\n\n"):
        match = re.search(r"^Package: (.+)$", stanza, re.M)
        arch = re.search(r"^Architecture: (.+)$", stanza, re.M)
        if match and (match[1] in packages or (arch and match[1] + ":" + arch[1] in packages)):
            statuses.append(stanza + "\nX-IIP-Content-Subset: measured-native-runtime")
            copyright_path = Path("/usr/share/doc", match[1], "copyright")
            if copyright_path.is_file():
                copy_file(copyright_path)
    metadata = ROOT / "var/lib/dpkg"
    (metadata / "info").mkdir(parents=True)
    (metadata / "status").write_text("\n\n".join(statuses) + "\n")
    for name, entries in package_lists.items():
        (metadata / "info" / name).write_text("\n".join(entries) + "\n")
    (ROOT / "etc/passwd").write_text("appuser:x:10001:10001:Application:/home/appuser:/sbin/nologin\n")
    (ROOT / "etc/group").write_text("appuser:x:10001:\n")
    for name in ("tmp", "app", "home/appuser"):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    (ROOT / "tmp").chmod(0o1777)
    os.chown(ROOT / "home/appuser", 10001, 10001)
    manifest = {
        "contract": "IIP_MEASURED_PYTHON_RUNTIME_V1",
        "distribution": "Debian Trixie; no foreign-suite package substitution",
        "python": subprocess.check_output(["python", "-V"], text=True).strip(),
        "elf_roots": [str(path) for path in elfs],
        "native_files": {str(path): digest(path) for path in sorted(dependencies)},
        "runtime_profile": "IIP_CORE_NONINTERACTIVE_V1",
        "excluded_optional_module_source_hashes": excluded,
        "preexisting_optional_gui_missing": {},
        "locked_versions": versions,
        "locks": {name: digest(Path("/app", name)) for name in ("requirements.lock", "requirements-assistant.lock")},
        "debian_packages_with_selected_files": sorted(packages),
        "package_metadata_note": "Identification of selected original package files; not a complete dpkg installation",
        "omitted_tools": ["shell", "mount", "nsenter", "systemd", "perl", "apt", "dpkg"],
    }
    destination = ROOT / MANIFEST.relative_to("/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"elf_roots": len(elfs), "native_files": len(dependencies), "debian_packages": len(packages), "excluded_optional_modules": len(excluded)}))


if __name__ == "__main__":
    main()
