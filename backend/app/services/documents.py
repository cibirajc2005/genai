"""Safe document storage and text extraction."""

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import fitz

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 20 * 1024 * 1024


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(name).name).strip()
    return cleaned or "document"


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        with fitz.open(path) as pdf:
            return "\n\n".join(page.get_text() for page in pdf)
    if suffix == ".docx":
        with zipfile.ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paragraphs = []
        for paragraph in root.iter(f"{namespace}p"):
            text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t"))
            if text.strip():
                paragraphs.append(text)
        return "\n".join(paragraphs)
    raise ValueError("Unsupported file type")


def chunks(text: str, size: int = 1400, overlap: int = 180) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    result, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        result.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return result
