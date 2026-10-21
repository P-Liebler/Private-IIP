"""Remove authentication headers and fixture passwords from generated text reports."""
import argparse
import os
import re
from pathlib import Path


def redact(text: str) -> str:
    text = re.sub(r"(?im)^.*\b(?:cookie|set-cookie|authorization):[^\r\n]*", "[REDACTED AUTH HEADER]", text)
    text = re.sub(r"investment_session=[A-Za-z0-9_-]+", "investment_session=[REDACTED]", text)
    for key in ("E2E_PASSWORD", "RESTORE_TEST_PASSWORD"):
        value = os.environ.get(key)
        if value:
            text = text.replace(value, "[REDACTED]")
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="+")
    args = parser.parse_args()
    for source in args.paths:
        files = source.rglob("*") if source.is_dir() else [source]
        for path in files:
            if path.suffix.lower() not in {".md", ".txt", ".json", ".log"} or not path.is_file():
                continue
            raw = path.read_bytes()
            encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
            try:
                original = raw.decode(encoding)
            except UnicodeError:
                continue
            cleaned = redact(original)
            if cleaned != original:
                path.write_text(cleaned, encoding="utf-8")


if __name__ == "__main__":
    main()
