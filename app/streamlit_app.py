"""
FinVista Capital - Financial Intelligence Assistant
Streamlit UI | Groq LLM | Gemini Embeddings | ChromaDB RAG
"""

import os
import tempfile
import logging

import streamlit as st

from rag_engine import (
    index_document,
    generate_response,
    get_collection_stats,
    delete_document,
)

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="FinVista Capital - Financial Intelligence Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a3c5e 0%, #2d6a9f 100%);
        padding: 1.5rem 2rem; border-radius: 12px;
        color: #ffffff; margin-bottom: 1.5rem;
    }
    .main-header h1 { color: #ffffff !important; }
    .main-header p  { color: #add8e6 !important; }
    .chat-user {
        background: #1e3a5f;
        border-left: 4px solid #63b3ed;
        padding: 0.75rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
        color: #e2e8f0 !important;
    }
    .chat-assistant {
        background: #1a3a2a;
        border-left: 4px solid #68d391;
        padding: 0.75rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
        color: #e2e8f0 !important;
    }
    .citation-box {
        background: #2d2a1a;
        border: 1px solid #d69e2e;
        border-radius: 8px;
        padding: 0.5rem 0.75rem;
        font-size: 0.85rem;
        margin-top: 0.5rem;
        color: #fefcbf !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>📊 FinVista Capital</h1>
    <p style="margin:0;">
        Enterprise Financial Intelligence Assistant · RAG + Groq LLM + Gemini Embeddings
    </p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuration")

    gemini_key = st.text_input(
        "Gemini API Key (embeddings)",
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
        help="Used for embeddings only. Free at aistudio.google.com",
    )
    if gemini_key:
        os.environ["GEMINI_API_KEY"] = gemini_key

    groq_key = st.text_input(
        "Groq API Key (chat responses)",
        value=os.getenv("GROQ_API_KEY", ""),
        type="password",
        help="Free - no credit card. Get at console.groq.com/keys",
    )
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key

    keys_ready = bool(gemini_key and groq_key)

    if not keys_ready:
        st.warning("Enter both API keys above to enable all features.")

    st.divider()

    st.header("📁 Document Upload")
    uploaded_files = st.file_uploader(
        "Upload PDF documents",
        type=["pdf"],
        accept_multiple_files=True,
        help="Annual reports, compliance manuals, research notes, etc.",
    )

    if uploaded_files and keys_ready:
        for uf in uploaded_files:
            if uf.name not in st.session_state.processed_files:
                with st.spinner(f"Processing {uf.name}..."):
                    try:
                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=".pdf"
                        ) as tmp:
                            tmp.write(uf.read())
                            tmp_path = tmp.name
                        n_chunks = index_document(tmp_path)
                        st.session_state.processed_files.add(uf.name)
                        st.success(f"✅ {uf.name} — {n_chunks} chunks indexed")
                        os.unlink(tmp_path)
                    except Exception as exc:
                        logger.error("Upload error: %s", exc)
                        st.error(f"❌ Error processing {uf.name}: {exc}")
    elif uploaded_files and not keys_ready:
        st.warning("Enter both API keys first.")

    st.divider()

    st.header("🗄️ Knowledge Base")
    if st.button("🔄 Refresh Stats"):
        st.rerun()

    stats = get_collection_stats()
    col1, col2 = st.columns(2)
    col1.metric("Documents", stats["document_count"])
    col2.metric("Chunks",    stats["total_chunks"])

    if stats["documents"]:
        st.subheader("Indexed Documents")
        for doc in stats["documents"]:
            c1, c2 = st.columns([3, 1])
            c1.write(f"📄 {doc}")
            if c2.button("🗑️", key=f"del_{doc}", help=f"Remove {doc}"):
                if delete_document(doc):
                    st.success(f"Removed {doc}")
                    st.session_state.processed_files.discard(doc)
                    st.rerun()

    st.divider()

    st.header("💬 Conversation")
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.conversation_history = []
        st.rerun()
    st.caption(f"Turns: {len(st.session_state.conversation_history)}")


tab_chat, tab_history, tab_help = st.tabs(["💬 Chat", "📜 History", "❓ Help"])

with tab_chat:
    if not keys_ready:
        st.info("👈 Enter both API keys in the sidebar to get started.")
    elif stats["total_chunks"] == 0:
        st.info("👈 Upload and index at least one PDF document to begin querying.")
    else:
        if st.session_state.conversation_history:
            st.subheader("Recent Conversation")
            for turn in st.session_state.conversation_history[-5:]:
                st.markdown(
                    f'<div class="chat-user">🧑 <strong>You:</strong> {turn["user"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="chat-assistant">🤖 <strong>Assistant:</strong> {turn["assistant"]}</div>',
                    unsafe_allow_html=True,
                )
                if turn.get("citations"):
                    with st.expander("📎 Sources"):
                        for c in turn["citations"]:
                            st.markdown(
                                f'<div class="citation-box">'
                                f'📄 <b>{c["source"]}</b>'
                                f' — Page {c["page"]}'
                                f' &nbsp;(similarity: {c["similarity"]:.2%})'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

        st.divider()
        st.subheader("Ask a Question")

        sample_qs = [
            "What are the key risk factors?",
            "Summarise the investment guidelines.",
            "What compliance requirements are highlighted?",
            "What is the market outlook for 2025?",
        ]
        cols = st.columns(2)
        for i, q in enumerate(sample_qs):
            if cols[i % 2].button(q, key=f"sample_{i}", use_container_width=True):
                st.session_state["prefilled_query"] = q
                st.session_state["auto_submit"] = True
                st.rerun()

        default_query = st.session_state.pop("prefilled_query", "")
        query = st.text_area(
            "Your question",
            value=default_query,
            height=100,
            placeholder="e.g. What are the key investment risks mentioned in the annual report?",
        )

        c1, c2 = st.columns([1, 5])
        submit = c1.button("🚀 Ask", type="primary", use_container_width=True)
        c2.caption("Responses are grounded in your uploaded documents.")

        auto_submit = st.session_state.pop("auto_submit", False)

        if (submit or auto_submit) and query.strip():
            with st.spinner("Searching knowledge base and generating response..."):
                try:
                    answer, citations = generate_response(
                        query.strip(), st.session_state.conversation_history
                    )
                    st.session_state.conversation_history.append({
                        "user":      query.strip(),
                        "assistant": answer,
                        "citations": citations,
                    })
                    st.rerun()
                except Exception as exc:
                    logger.error("Query error: %s", exc)
                    st.error(f"Error generating response: {exc}")

with tab_history:
    st.subheader("Full Conversation History")
    if not st.session_state.conversation_history:
        st.info("No conversation history yet.")
    else:
        for i, turn in enumerate(st.session_state.conversation_history, 1):
            with st.expander(f"Turn {i}: {turn['user'][:80]}..."):
                st.markdown(f"**Question:** {turn['user']}")
                st.markdown(f"**Answer:**\n\n{turn['assistant']}")
                if turn.get("citations"):
                    st.markdown("**Sources:**")
                    for c in turn["citations"]:
                        st.markdown(
                            f"- `{c['source']}` · Page {c['page']}"
                            f" · similarity {c['similarity']:.2%}"
                        )

with tab_help:
    st.subheader("How to Use FinVista Financial Intelligence Assistant")
    st.markdown(
        "### Quick Start\n"
        "1. **Gemini API key** - free at aistudio.google.com (for embeddings)\n"
        "2. **Groq API key** - free at console.groq.com/keys (for chat, no credit card)\n"
        "3. **Upload PDFs** via sidebar\n"
        "4. **Ask questions** in the Chat tab\n\n"
        "### API Keys\n"
        "- Gemini: Embeddings only, generous free tier\n"
        "- Groq: LLM responses, 1000 req/day, no credit card\n\n"
        "### Sample Questions\n"
        "- What are the key risk factors for FinVista Capital?\n"
        "- What is the strategic asset allocation for equities?\n"
        "- What AML triggers are flagged in the compliance manual?\n"
        "- What is the market outlook for the technology sector in 2025?\n"
        "- What are the recovery time objectives in the BCP?\n"
    )
