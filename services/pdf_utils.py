import fitz  # PyMuPDF
from typing import Iterator, Tuple

def iter_pdf_pages_text(pdf_bytes: bytes) -> Iterator[Tuple[int, str]]:
    """Yield (page_number, text) for each page in PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for i, page in enumerate(doc):
        yield i + 1, page.get_text()

def preview_pdf_text(pdf_bytes: bytes, max_chars: int = 2000, max_pages: int = 3) -> str:
    """Build a short preview from the first few pages."""
    out = []
    total = 0
    for i, (pageno, text) in enumerate(iter_pdf_pages_text(pdf_bytes)):
        if i >= max_pages:
            break
        slice_text = text[: max(0, max_chars - total)]
        out.append(slice_text)
        total += len(slice_text)
        if total >= max_chars:
            break
    combined = "".join(out)
    return combined + ("..." if len(combined) >= max_chars else "")

def read_pdf_bytes(uploaded_file) -> bytes:
    return uploaded_file.getvalue()
