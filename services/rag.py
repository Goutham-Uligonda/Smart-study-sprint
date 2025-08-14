import chromadb
from chromadb.utils import embedding_functions
from typing import List
from .pdf_utils import iter_pdf_pages_text
from .chunking import simple_chunk, extract_unit
import os

# Initialized lazily in get_collection()
_chroma_client = None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_collection(collection_name="syllabus"):
    """Create/get an in-memory Chroma collection with OpenAI embeddings."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.Client()  # swap to PersistentClient for persistence
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-3-small"
    )
    return _chroma_client.get_or_create_collection(collection_name, embedding_function=ef)

def build_index_from_pdf(pdf_bytes: bytes, collection):
    """Read PDF → chunk → add to Chroma with metadata (unit/page)."""
    texts = []
    page_units = []
    current_unit = None

    for pageno, text in iter_pdf_pages_text(pdf_bytes):
        for line in text.splitlines():
            u = extract_unit(line)
            if u:
                current_unit = u
        texts.append(text)
        page_units.append((pageno, current_unit or "Unknown"))

    full_text = "\n".join(texts)
    chunks = list(simple_chunk(full_text))

    # Map chunk -> coarse page/unit via proportional estimate
    N = max(1, len(chunks) - 1)
    docs, metadatas, ids = [], [], []
    for idx, ck in enumerate(chunks):
        est = min(len(page_units), max(1, int((idx / N) * len(page_units))))
        pageno, unit = page_units[est - 1]
        docs.append(ck)
        metadatas.append({"page": pageno, "unit": unit, "source": "uploaded_pdf"})
        ids.append(f"chunk-{idx}")

    # Clear previous docs from same source (optional strategy)
    try:
        if collection.count() > 0:
            collection.delete(where={"source": "uploaded_pdf"})
    except Exception:
        pass

    collection.add(documents=docs, metadatas=metadatas, ids=ids)

def retrieve_context(question: str, collection, k=8) -> str:
    """Return top-k chunks as a readable context with [Unit, Page] tags."""
    res = collection.query(query_texts=[question], n_results=k)
    docs: List[List[str]] = res.get("documents", [[]])
    metas: List[List[dict]] = res.get("metadatas", [[]])

    chunks = docs[0] if docs else []
    mlist = metas[0] if metas else []

    blocks = []
    for c, m in zip(chunks, mlist):
        tag = f"[Unit: {m.get('unit')}, Page: {m.get('page')}]"
        blocks.append(f"{tag}\n{c}")
    return "\n\n---\n\n".join(blocks) if blocks else ""