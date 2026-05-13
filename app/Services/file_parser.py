from __future__ import annotations
from pathlib import Path


def parse_file(path: str | Path) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".txt", ".md"):
        return p.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    if ext == ".docx":
        from docx import Document
        doc = Document(str(p))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return p.read_text(encoding="utf-8", errors="ignore")


SUPPORTED_EXTS = {".txt", ".md", ".pdf", ".docx"}
