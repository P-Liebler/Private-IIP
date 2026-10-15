"""Fixed local parser subprocess; document bytes never become executable commands."""

import io
import json
import sys


def extract(data: bytes) -> list[dict[str, object]]:
    from pypdf import PdfReader

    if len(data) > 5_000_000 or not data.startswith(b"%PDF-"):
        raise ValueError("INVALID_PDF")
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted or len(reader.pages) > 50:
        raise ValueError("PDF_ENCRYPTED_OR_PAGE_LIMIT")
    pages, total = [], 0
    for index, page in enumerate(reader.pages):
        content = page.get_contents()
        if content and len(content.get_data()) > 2_000_000:
            raise ValueError("PDF_CONTENT_LIMIT")
        text = page.extract_text() or ""
        total += len(text)
        if total > 100_000:
            raise ValueError("PDF_TEXT_LIMIT")
        if text.strip():
            pages.append({"page": index + 1, "text": text})
    if not pages:
        raise ValueError("PDF_TEXT_UNAVAILABLE_NO_OCR")
    return pages


if __name__ == "__main__":
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024, 384 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        pages = extract(sys.stdin.buffer.read(5_000_001))
        print(json.dumps({"pages": pages}, ensure_ascii=False))
    except Exception:
        print(json.dumps({"error": "PDF_EXTRACTION_UNAVAILABLE"}))
