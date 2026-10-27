"""Model-volume preparation uses local synthetic software bytes only."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seed_pr7_models import copy_models


class ModelSeedTests(unittest.TestCase):
    def test_exact_copy_provisions_readonly_runtime_roots_without_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "source", Path(folder) / "target"
            source.mkdir()
            (source / "id_ed25519").write_bytes(b"SYNTHETIC EXCLUDED KEY")
            payload = b"SYNTHETIC MODEL BYTES"
            digest = hashlib.sha256(payload).hexdigest()
            (source / "blobs").mkdir()
            (source / "blobs" / ("sha256-" + digest)).write_bytes(payload)
            original = json.dumps({"config": {"digest": "sha256:" + digest, "size": len(payload)}, "layers": []}).encode()
            for name in ("qwen3/0.6b", "embeddinggemma/300m"):
                path = source / "manifests/registry.ollama.ai/library" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(original)
            result = copy_models(source, target)
            self.assertEqual(result["blobs"], 1)
            self.assertEqual((target / "manifests/registry.ollama.ai/library/qwen3/0.6b").read_bytes(), original)
            self.assertTrue((target / "manifests-v2").is_dir())
            self.assertFalse((target / "id_ed25519").exists())
            self.assertEqual((source / "blobs" / ("sha256-" + digest)).read_bytes(), payload)
            with self.assertRaisesRegex(RuntimeError, "NEW_MODEL_VOLUME_REQUIRED"):
                copy_models(source, target)


if __name__ == "__main__":
    unittest.main()
