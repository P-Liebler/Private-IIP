"""Untrusted archive boundary tests; never run a model or make network calls."""
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ollama"))
from extract_cpu import extract


def archive(items):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as output:
        for name, data, link in items:
            info = tarfile.TarInfo(name)
            if link is not None:
                info.type, info.linkname = tarfile.SYMTYPE, link
                output.addfile(info)
            else:
                info.size, info.mode = len(data), 0o755
                output.addfile(info, io.BytesIO(data))
    stream.seek(0)
    return stream


class OllamaCPUArchiveTests(unittest.TestCase):
    def test_installs_exact_cpu_bytes_without_gpu_backends(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "cpu"
            extract(archive([("./bin/ollama", b"SYNTHETIC SOFTWARE BINARY", None),
                ("lib/ollama/libggml-cpu.so", b"SYNTHETIC SOFTWARE LIBRARY", None),
                ("lib/ollama/cuda_v13/gpu.so", b"SYNTHETIC UNUSED GPU", None)]), target)
            self.assertEqual((target / "lib/ollama/libggml-cpu.so").read_bytes(), b"SYNTHETIC SOFTWARE LIBRARY")
            self.assertFalse((target / "lib/ollama/cuda_v13").exists())
            self.assertEqual(len(json.loads((target / "cpu-files.json").read_text())["files"]), 2)

    def test_parent_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, "ARCHIVE_PATH_REJECTED"):
                extract(archive([("lib/ollama/../../../outside", b"unsafe", None)]), Path(folder) / "cpu")
            self.assertFalse((Path(folder) / "outside").exists())

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, "ARCHIVE_LINK_REJECTED"):
                extract(archive([("lib/ollama/link", b"", "../../../outside")]), Path(folder) / "cpu")

    def test_incomplete_payload_never_becomes_a_valid_image_input(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, "CPU_PAYLOAD_INCOMPLETE"):
                extract(archive([("bin/ollama", b"SYNTHETIC BINARY WITHOUT CPU LIBRARIES", None)]), Path(folder) / "cpu")


if __name__ == "__main__":
    unittest.main()
