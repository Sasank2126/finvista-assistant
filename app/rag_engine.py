"""
RAG Engine — FinVista Capital Financial Intelligence Assistant
Groq LLM (llama-3.3-70b-versatile) · Gemini Embeddings (gemini-embedding-001)
ChromaDB Vector Store · PyMuPDF PDF Parser
"""

import os
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple

import fitz
import chromadb
from chromadb.config import Settings
from google import genai
from google.genai import types
from groq import Groq
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

CHROMA_DB_PATH  = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = "finvista_docs"
EMBED_MODEL     = "gemini-embedding-001"
CHAT_MODEL      = "llama-3.3-70b-versatile"
CHUNK_SIZE      = 1000
CHUNK_OVERLAP   = 200
TOP_K_RESULTS   = 5


def _get_gemini_client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise ValueError("GEMINI_API_KEY is not set. Enter it in the sidebar.")
    return genai.Client(api_key=key)


def _get_groq_client() -> Groq:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise ValueError("GROQ_API_KEY is not set. Enter it in the sidebar.")
    return Groq(api_key=key)


def _get_chroma_client() -> chromadb.Client:
    return chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=Settings(anonymized_telemetry=False),
    )


def _get_collection(client: chromadb.Client) -> chromadb.Collection:
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def parse_pdf(file_path: str) -> List[Dict]:
    pages = []
    try:
        doc = fitz.open(file_path)
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append({
                    "page":   page_num,
                    "text":   text,
                    "source": Path(file_path).name,
                })
        doc.close()
        logger.info("Parsed %d pages from %s", len(pages), file_path)
    except Exception as exc:
        logger.error("PDF parse error for %s: %s", file_path, exc)
        raise RuntimeError(
            f"Could not parse PDF '{Path(file_path).name}': {exc}"
        ) from exc
    return pages


def chunk_pages(pages: List[Dict]) -> List[Dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = []
    for page in pages:
        for i, split in enumerate(splitter.split_text(page["text"])):
            chunks.append({
                "text":   split,
                "source": page["source"],
                "page":   page["page"],
                "chunk":  i,
            })
    logger.info("Created %d chunks", len(chunks))
    return chunks


def _embed_texts(texts: List[str]) -> List[List[float]]:
    client = _get_gemini_client()
    embeddings = []
    for i in range(0, len(texts), 100):
        batch = texts[i: i + 100]
        result = client.models.embed_content(
            model=EMBED_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        embeddings.extend([e.values for e in result.embeddings])
    return embeddings


def index_document(file_path: str) -> int:
    pages  = parse_pdf(file_path)
    chunks = chunk_pages(pages)
    if not chunks:
        return 0

    texts     = [c["text"] for c in chunks]
    metadatas = [{"source": c["source"], "page": c["page"], "chunk": c["chunk"]}
                 for c in chunks]
    ids       = [hashlib.md5(
                     f"{c['source']}_{c['page']}_{c['chunk']}".encode()
                 ).hexdigest() for c in chunks]

    embeddings = _embed_texts(texts)

    chroma = _get_chroma_client()
    col    = _get_collection(chroma)
    for i in range(0, len(chunks), 100):
        col.upsert(
            ids=ids[i: i + 100],
            embeddings=embeddings[i: i + 100],
            documents=texts[i: i + 100],
            metadatas=metadatas[i: i + 100],
        )
    logger.info("Indexed %d chunks for %s", len(chunks), file_path)
    return len(chunks)


def semantic_search(query: str, top_k: int = TOP_K_RESULTS) -> List[Dict]:
    chroma = _get_chroma_client()
    col    = _get_collection(chroma)

    total = col.count()
    if total == 0:
        return []

    n = min(top_k, total)

    client = _get_gemini_client()
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=query,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    query_vec = result.embeddings[0].values

    results = col.query(
        query_embeddings=[query_vec],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text":       doc,
            "source":     meta.get("source", "unknown"),
            "page":       meta.get("page", 0),
            "similarity": round(1 - dist, 4),
        })
    logger.info("Retrieved %d chunks for query", len(hits))
    return hits


def build_prompt(query: str, context_chunks: List[Dict], history: List[Dict]) -> str:
    context = "\n\n---\n\n".join(
        f"[Source: {c['source']}, Page {c['page']}]\n{c['text']}"
        for c in context_chunks
    )
    history_text = ""
    for turn in history[-6:]:
        history_text += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n\n"

    return (
        "You are FinVista Capital's Financial Intelligence Assistant.\n"
        "Answer questions accurately using ONLY the provided context.\n"
        "If the answer is not in the context, say so clearly.\n"
        "Always cite the source document and page number.\n\n"
        f"CONVERSATION HISTORY:\n{history_text}\n"
        f"CONTEXT FROM DOCUMENTS:\n{context}\n\n"
        f"CURRENT QUESTION: {query}\n\n"
        "Provide a detailed, accurate answer with citations in the format "
        "[Source: filename, Page X]."
    )


def generate_response(
    query: str, conversation_history: List[Dict]
) -> Tuple[str, List[Dict]]:
    context_chunks = semantic_search(query)
    if not context_chunks:
        return "No relevant documents found. Please upload documents first.", []

    prompt = build_prompt(query, context_chunks, conversation_history)
    client = _get_groq_client()
    chat   = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.1,
    )
    answer = chat.choices[0].message.content
    logger.info("Generated response (%d chars)", len(answer))
    return answer, context_chunks


def get_collection_stats() -> Dict:
    try:
        chroma = _get_chroma_client()
        col    = _get_collection(chroma)
        count  = col.count()
        sources: set = set()
        if count > 0:
            sources = {
                m.get("source", "unknown")
                for m in col.get(include=["metadatas"])["metadatas"]
            }
        return {
            "total_chunks":   count,
            "documents":      list(sources),
            "document_count": len(sources),
        }
    except Exception as exc:
        logger.error("Stats error: %s", exc)
        return {"total_chunks": 0, "documents": [], "document_count": 0}


def delete_document(source_name: str) -> bool:
    try:
        chroma  = _get_chroma_client()
        col     = _get_collection(chroma)
        results = col.get(where={"source": source_name}, include=["metadatas"])
        ids     = results.get("ids", [])
        if ids:
            col.delete(ids=ids)
            logger.info("Deleted %d chunks for %s", len(ids), source_name)
            return True
        return False
    except Exception as exc:
        logger.error("Delete error: %s", exc)
        return False
