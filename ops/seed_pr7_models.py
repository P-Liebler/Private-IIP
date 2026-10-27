"""Copy only two existing public model manifests/blobs into a new stage volume.

The source volume must be mounted read-only; private Ollama identity keys and
other models are never copied. No downloads and no manifest modifications.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil


def copy_models(source: Path, target: Path):
    if target.exists():
        raise RuntimeError("NEW_MODEL_VOLUME_REQUIRED")
    target.mkdir()
    # Ollama 0.40.11 enumerates both roots even when all tags are legacy.
    # Provision the empty root before the serving volume is mounted read-only.
    (target / "manifests-v2").mkdir()
    models = []
    copied = set()
    for name in ("qwen3/0.6b", "embeddinggemma/300m"):
        relative = Path("manifests/registry.ollama.ai/library") / name
        manifest = (source / relative).read_bytes()
        value = json.loads(manifest)
        for item in [value["config"], *value["layers"]]:
            digest = item["digest"]
            assert re.fullmatch(r"sha256:[a-f0-9]{64}", digest)
            blob = Path("blobs") / digest.replace(":", "-")
            if blob in copied:
                continue
            destination = target / blob
            destination.parent.mkdir(exist_ok=True)
            shutil.copyfile(source / blob, destination)
            checksum = hashlib.sha256()
            with destination.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    checksum.update(block)
            assert checksum.hexdigest() == digest.split(":")[1]
            assert destination.stat().st_size == item["size"]
            copied.add(blob)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(manifest)
        models.append({"model": name, "manifest_sha256": hashlib.sha256(manifest).hexdigest()})
    return {"status": "EXACT_LOCAL_PUBLIC_MODEL_COPY_VERIFIED", "models": models,
            "blobs": len(copied), "private_identity_keys_copied": False}


def main():
    if os.environ.get("PR7_SYNTHETIC_STAGE") != "explicit-isolated-fixture":
        raise RuntimeError("ISOLATED_SYNTHETIC_STAGE_REQUIRED")
    print(json.dumps(copy_models(Path("/model-source/models"), Path("/model-target/models"))))


if __name__ == "__main__":
    main()
