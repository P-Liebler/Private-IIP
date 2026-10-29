"""Offline runtime probe; no application services or financial providers used.

Pipe this file to the exact candidate image's Python with network none, read-only
root, an unprivileged user and a bounded /tmp tmpfs. JSON contains no secrets.
"""

import hashlib
import ctypes
import importlib.metadata
import importlib.util
import json
import locale
import os
from pathlib import Path
import pwd
import shutil
import socket
import ssl
import subprocess
import sys
from zoneinfo import ZoneInfo


def main() -> None:
    manifest = json.loads(Path("/usr/share/private-iip/runtime-closure.json").read_text())
    assert manifest["contract"] == "IIP_MEASURED_PYTHON_RUNTIME_V1"
    for path, expected in manifest["native_files"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    for package, version in manifest["locked_versions"].items():
        assert importlib.metadata.version(package) == version, package
    for name, expected in manifest["locks"].items():
        assert hashlib.sha256(Path("/app", name).read_bytes()).hexdigest() == expected, name
    assert os.getuid() == os.getgid() == 10001
    assert pwd.getpwuid(os.getuid()).pw_name == "appuser"
    assert all(shutil.which(name) is None for name in ("sh", "bash", "mount", "nsenter", "perl", "apt", "dpkg"))
    assert ssl.create_default_context().cert_store_stats()["x509_ca"] > 0
    assert socket.getaddrinfo("localhost", 0)
    for module in Path("/usr/lib/x86_64-linux-gnu").glob("libnss_*.so*"):
        ctypes.CDLL(str(module))
    assert ZoneInfo("Europe/Zurich").key == "Europe/Zurich"
    assert locale.setlocale(locale.LC_ALL, "C.UTF-8")
    result = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True)
    assert result.returncode == 0, "PIP_CHECK_FAILED"
    # Import native modules used by APIs, workers and archive parsing. Optional
    # TUI/GUI/line-editing/native-UUID modules are intentionally not in Core.
    import _ctypes  # noqa: F401
    import _sqlite3  # noqa: F401
    import _ssl  # noqa: F401
    import uuid
    assert manifest["runtime_profile"] == "IIP_CORE_NONINTERACTIVE_V1"
    for module in ("_curses", "_curses_panel", "_uuid", "readline", "_tkinter"):
        assert importlib.util.find_spec(module) is None, module
    identifiers = {uuid.uuid4() for _ in range(1000)}
    assert len(identifiers) == 1000 and all(value.version == 4 for value in identifiers)
    assert uuid.UUID(str(uuid.uuid1())).version == 1
    import asyncpg  # noqa: F401
    import celery  # noqa: F401
    import cryptography  # noqa: F401
    import fastapi  # noqa: F401
    import pgvector  # noqa: F401
    import pypdf  # noqa: F401
    import numpy as np
    from argon2 import PasswordHasher
    from lightgbm import LGBMRegressor
    from scipy.linalg import solve
    from sklearn.linear_model import Ridge
    from xgboost import XGBRegressor

    hasher = PasswordHasher()
    assert hasher.verify(hasher.hash("offline-runtime-probe"), "offline-runtime-probe")
    x = np.arange(24, dtype=np.float64).reshape(12, 2)
    y = np.arange(12, dtype=np.float64)
    assert np.isfinite(solve(np.eye(2), np.ones(2))).all()
    for model in (
        Ridge(),
        LGBMRegressor(n_estimators=2, min_child_samples=2, n_jobs=1, verbosity=-1),
        XGBRegressor(n_estimators=2, max_depth=2, n_jobs=1),
    ):
        assert np.isfinite(model.fit(x, y).predict(x)).all()
    print(json.dumps({
        "status": "OFFLINE_RUNTIME_PROBE_PASSED",
        "uid": os.getuid(),
        "gid": os.getgid(),
        "locked_packages_verified": len(manifest["locked_versions"]),
        "native_file_hashes_verified": len(manifest["native_files"]),
        "python": sys.version.split()[0],
        "tls_trust_store": "NONEMPTY",
        "dns_hosts": "LOCALHOST_RESOLVED_WITHOUT_PROVIDER_CALL",
        "shell_and_administration_tools": "ABSENT",
        "numerical_smokes": ["numpy", "scipy", "scikit-learn", "lightgbm", "xgboost"],
        "synthetic_probe": True,
        "historical_dynamic_execution_equivalence": "NOT_CLAIMED",
        "production_release": "NOT_APPROVED",
        "runtime_profile": manifest["runtime_profile"],
        "excluded_optional_module_source_hashes": manifest["excluded_optional_module_source_hashes"],
    }, indent=2))


if __name__ == "__main__":
    main()
