import re
import tiktoken
from typing import Iterator

_UNIT_RE = re.compile(r"\bUnit\s*[IVX0-9]+\b", flags=re.I)

def extract_unit(line: str):
    """Heuristic to detect 'Unit I/II/III...' headings."""
    m = _UNIT_RE.search(line)
    return m.group(0) if m else None

def simple_chunk(text: str, chunk_tokens=350, overlap_tokens=70, enc_name="cl100k_base") -> Iterator[str]:
    """Token-based sliding window chunking."""
    enc = tiktoken.get_encoding(enc_name)
    toks = enc.encode(text)
    i = 0
    step = max(1, chunk_tokens - overlap_tokens)
    while i < len(toks):
        window = toks[i:i + chunk_tokens]
        yield enc.decode(window)
        i += step

def token_len(text: str, enc_name="cl100k_base") -> int:
    if not text:
        return 0
    enc = tiktoken.get_encoding(enc_name)
    return len(enc.encode(text))
