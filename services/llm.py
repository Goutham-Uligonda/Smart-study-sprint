import os
import re
from openai import OpenAI
from .rag import retrieve_context
from .chunking import token_len

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- Intent Parsing ----------
def parse_intent(prompt: str):
    """
    Detect intent: 'mcq', 'theory', or 'explain' and a requested count (default 5 MCQs, 3 theory).
    Returns: (intent, count)
    """
    p = prompt.lower()
    m = re.search(r"\b(\d+)\b", p)
    count = int(m.group(1)) if m else None

    if "mcq" in p or "multiple choice" in p:
        return "mcq", (count or 5)
    if "theory" in p or "long answer" in p or "essay" in p:
        return "theory", (count or 3)
    return "explain", None

# ---------- Hybrid Answering ----------
def answer_hybrid(question: str, collection, syllabus_outline: str | None, max_tokens=950) -> str:
    """
    Hybrid:
      - Retrieve via RAG
      - If context strong -> ground strictly
      - If context weak -> allow domain knowledge, aligned to syllabus outline
    """
    intent, count = parse_intent(question)
    context = retrieve_context(question, collection, k=8)
    ctx_tokens = token_len(context)
    STRONG_CTX = 200
    WEAK_CTX = ctx_tokens < STRONG_CTX

    if intent == "mcq":
        count = count or 5
        system = (
            "You are a precise study assistant for exams. Prefer retrieved syllabus context when available. "
            "If context is insufficient, generate accurate, on-topic MCQs using domain knowledge, "
            "aligned to the syllabus outline if provided."
        )
        user = f"""Task: Create {count} MCQs with 4 options each and mark the correct answer.
Topic/Question: {question}

Retrieved Context (may be empty or partial):
{context if context else "[no retrieved context]"}

Syllabus Outline (if any):
{syllabus_outline or "[not provided]"}

Rules:
- If context is strong, base questions strictly on it and cite [Unit, Page] tags when relevant.
- If context is weak, you may generate MCQs from domain knowledge BUT keep them aligned to the syllabus outline terms (units/topics).
- Avoid introducing topics that clearly don't exist in the syllabus outline.
- Format:
Q1) ...
   A) ...
   B) ...
   C) ...
   D) ...
Correct: X
"""
    elif intent == "theory":
        count = count or 3
        system = (
            "You are a precise study assistant for theory exams. Prefer retrieved syllabus context when available. "
            "If context is insufficient, generate accurate, on-topic theory questions and model answers aligned to the syllabus outline."
        )
        user = f"""Task: Create {count} exam-style theory questions and provide model answers.
Topic/Question: {question}

Retrieved Context (may be empty or partial):
{context if context else "[no retrieved context]"}

Syllabus Outline (if any):
{syllabus_outline or "[not provided]"}

Rules:
- If context is strong, base questions and answers strictly on it and cite [Unit, Page] when helpful.
- If context is weak, you may use domain knowledge BUT keep content aligned to the syllabus outline.
- Keep answers concise, structured, and exam-focused.
"""
    else:
        system = (
            "You are a precise tutor. Prefer retrieved syllabus context when available. "
            "If context is insufficient, you may use domain knowledge, but align to the syllabus outline."
        )
        user = f"""Task: Explain the requested topic clearly and concisely.
Topic/Question: {question}

Retrieved Context (may be empty or partial):
{context if context else "[no retrieved context]"}

Syllabus Outline (if any):
{syllabus_outline or "[not provided]"}

Rules:
- If context is strong, stick closely to it and reference [Unit, Page] where helpful.
- If context is weak, you may expand using domain knowledge; ensure terms and scope match the syllabus outline.
- Avoid off-syllabus tangents.
"""

    temperature = 0.5 if WEAK_CTX else 0.2
    system += " Context appears limited; reasonable expansion is allowed." if WEAK_CTX else " Context appears sufficient; ground your answer strictly in it."

    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return resp.choices[0].message.content

# ---------- Key Topics via RAG ----------
def key_topics_with_rag(collection) -> str:
    """Summarize key topics using retrieved context across the syllabus."""
    # Broader retrieval prompt to get coverage
    from .rag import retrieve_context as _rc
    ctx = _rc("List the main topics and subtopics across the entire syllabus.", collection, k=20)
    prompt = f"""
Using ONLY the context below (syllabus excerpts with tags), produce a clean hierarchical list
of the most important topics and subtopics for exam prep.

Context:
{ctx}

Format:
- Topic
  - Subtopic
  - Subtopic
- Next Topic
  - Subtopic
"""
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=600
    )
    return resp.choices[0].message.content