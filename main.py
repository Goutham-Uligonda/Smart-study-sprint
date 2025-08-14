import dotenv
dotenv.load_dotenv()

import streamlit as st
from services.pdf_utils import preview_pdf_text, read_pdf_bytes
from services.rag import get_collection, build_index_from_pdf, retrieve_context
from services.llm import key_topics_with_rag, answer_hybrid

st.set_page_config(page_title="Smart Study Sprint (Hybrid RAG)", layout="wide")
st.title("📘 Smart Study Sprint – Personalized Exam Prep Assistant (Hybrid RAG)")

# Single file uploader with unique key
uploaded_file = st.file_uploader(
    "📄 Upload your syllabus or textbook PDF",
    type=["pdf"],
    key="uploader_syllabus"
)

# Reset state if a new file is selected
prev_name = st.session_state.get("last_uploaded_name")
if uploaded_file is not None and prev_name != uploaded_file.name:
    for k in ["rag_collection", "topics"]:
        st.session_state.pop(k, None)
    st.session_state["last_uploaded_name"] = uploaded_file.name

# Build index after upload
if uploaded_file:
    with st.spinner("📖 Reading & indexing your PDF (RAG)…"):
        pdf_bytes = read_pdf_bytes(uploaded_file)
        preview = preview_pdf_text(pdf_bytes, max_chars=2000, max_pages=3)

        st.success("✅ PDF uploaded and processed!")
        with st.expander("🔍 Preview Extracted Text"):
            st.write(preview)

        collection = get_collection("syllabus")
        build_index_from_pdf(pdf_bytes, collection)
        st.session_state["rag_collection"] = collection
        st.success("🔎 RAG index built (syllabus is now searchable).")

        if st.button("📚 Extract Key Topics", key="btn_topics"):
            with st.spinner("🧠 Summarizing key topics from your syllabus…"):
                topics = key_topics_with_rag(collection)
                st.session_state["topics"] = topics
                st.success("🎉 Key topics extracted!")

# Show key topics
if "topics" in st.session_state:
    st.subheader("🧠 Key Topics to Study")
    st.markdown(st.session_state["topics"])

# Ask Me Anything (Hybrid RAG)
st.divider()
st.subheader("💬 Ask Me Anything from Your Syllabus")

with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([10, 1])
    user_query = col1.text_input(
        label="",
        placeholder="e.g. Explain Unit I, Give 10 MCQs on Treasury Bills, 3 theory Qs on Cryptocurrency",
        label_visibility="collapsed",
        key="user_query_input"
    )
    submitted = col2.form_submit_button("➤")

if submitted and user_query:
    if "rag_collection" not in st.session_state:
        st.warning("Please upload your syllabus first so I can build the search index.")
    else:
        syllabus_outline = st.session_state.get("topics")  # helps guide fallback generation
        with st.spinner("🔎 Searching your syllabus & generating…"):
            answer = answer_hybrid(
                question=user_query,
                collection=st.session_state["rag_collection"],
                syllabus_outline=syllabus_outline
            )
            st.markdown("### 🧾 Answer (Hybrid RAG):")
            st.write(answer)