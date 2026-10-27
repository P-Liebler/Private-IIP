"""Extract the official CPU payload safely; do not install unused GPU backends."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile


def extract(stream, destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    records, links, total = [], [], 0
    with tarfile.open(fileobj=stream, mode="r|") as archive:
        for member in archive:
            name = member.name
            while name.startswith("./"):
                name = name[2:]
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError("ARCHIVE_PATH_REJECTED")
            parts = path.parts
            if not (parts == ("bin", "ollama") or parts[:2] == ("lib", "ollama")):
                continue
            if any(token in name.lower() for token in ("cuda", "rocm", "vulkan", "mlx", "jetpack", "/include/")):
                continue
            target = destination.joinpath(*parts)
            if not target.resolve().is_relative_to(destination):
                raise RuntimeError("ARCHIVE_PATH_REJECTED")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if member.issym():
                link = PurePosixPath(member.linkname)
                if link.is_absolute() or ".." in link.parts:
                    raise RuntimeError("ARCHIVE_LINK_REJECTED")
                links.append((target, member.linkname))
                continue
            if not member.isfile() or member.size < 0:
                raise RuntimeError("ARCHIVE_TYPE_REJECTED")
            total += member.size
            if total > 1024**3:
                raise RuntimeError("CPU_PAYLOAD_SIZE_LIMIT")
            checksum = hashlib.sha256()
            source = archive.extractfile(member)
            assert source
            written = 0
            with source, target.open("xb") as output:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    checksum.update(block)
                    output.write(block)
                    written += len(block)
            if written != member.size:
                raise RuntimeError("ARCHIVE_LENGTH_MISMATCH")
            target.chmod(0o755 if member.mode & 0o111 else 0o644)
            records.append({"path": str(path), "size": written, "sha256": checksum.hexdigest()})
    for target, link in links:
        target.symlink_to(link)
    # Release archives may contain .so -> .so.0 -> concrete library chains.
    # Create the complete confined chain before resolving every final target.
    for target, link in links:
        resolved = (target.parent / link).resolve()
        if not resolved.is_relative_to(destination) or not resolved.is_file():
            raise RuntimeError("ARCHIVE_LINK_TARGET_REJECTED")
    if not (destination / "bin/ollama").is_file() or not any("lib/ollama/" in row["path"] for row in records):
        raise RuntimeError("CPU_PAYLOAD_INCOMPLETE")
    (destination / "cpu-files.json").write_text(json.dumps({"contract": "PR7_OFFICIAL_OLLAMA_CPU_PAYLOAD_V1",
        "bytes": total, "files": records, "links": [
            {"path": str(path.relative_to(destination)), "target": link} for path, link in links
        ]}, indent=2), encoding="utf-8")


def main():
    process = subprocess.Popen(["zstd", "-dc", sys.argv[1]], stdout=subprocess.PIPE)
    try:
        extract(process.stdout, Path(sys.argv[2]))
        process.stdout.read()  # Consume archive padding and let decompression finish.
        if process.wait(timeout=30) != 0:
            raise RuntimeError("RELEASE_DECOMPRESSION_FAILED")
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()


if __name__ == "__main__":
    main()
