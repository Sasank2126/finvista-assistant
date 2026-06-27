"""
Unit tests for FinVista RAG engine
Run with:  pytest tests/ -v
All external services (Gemini, ChromaDB) are mocked — no API calls made.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-unit-tests")


# ── Fixtures ───────────────────────────────────────────────────────────────────
@pytest.fixture
def sample_pages():
    return [
        {"page": 1, "text": "FinVista Capital Q1 2024 Annual Report. Revenue grew 15% YoY.", "source": "annual_report.pdf"},
        {"page": 2, "text": "Risk factors include market volatility and regulatory changes in 2024.", "source": "annual_report.pdf"},
        {"page": 3, "text": "Investment guidelines require diversification across asset classes.", "source": "annual_report.pdf"},
    ]

@pytest.fixture
def sample_chunks():
    return [
        {"text": "Revenue grew 15% YoY", "source": "annual_report.pdf", "page": 1, "chunk": 0},
        {"text": "Risk factors include market volatility", "source": "annual_report.pdf", "page": 2, "chunk": 0},
    ]


# ── chunk_pages ────────────────────────────────────────────────────────────────
def test_chunk_pages_returns_list(sample_pages):
    from rag_engine import chunk_pages
    chunks = chunk_pages(sample_pages)
    assert isinstance(chunks, list)
    assert len(chunks) >= len(sample_pages)

def test_chunk_pages_required_keys(sample_pages):
    from rag_engine import chunk_pages
    for chunk in chunk_pages(sample_pages):
        for key in ("text", "source", "page", "chunk"):
            assert key in chunk

def test_chunk_pages_source_preserved(sample_pages):
    from rag_engine import chunk_pages
    for chunk in chunk_pages(sample_pages):
        assert chunk["source"] == "annual_report.pdf"


# ── build_prompt ───────────────────────────────────────────────────────────────
def test_build_prompt_contains_query(sample_chunks):
    from rag_engine import build_prompt
    query = "What are the revenue growth figures?"
    assert query in build_prompt(query, sample_chunks, [])

def test_build_prompt_contains_source(sample_chunks):
    from rag_engine import build_prompt
    assert "annual_report.pdf" in build_prompt("test", sample_chunks, [])

def test_build_prompt_contains_history(sample_chunks):
    from rag_engine import build_prompt
    history = [{"user": "What is revenue?", "assistant": "Revenue grew 15%."}]
    assert "What is revenue?" in build_prompt("Follow up", sample_chunks, history)


# ── get_collection_stats ───────────────────────────────────────────────────────
@patch("rag_engine._get_client")
def test_collection_stats_shape(mock_client):
    mock_col = MagicMock()
    mock_col.count.return_value = 42
    mock_col.get.return_value   = {"metadatas": [{"source": "report.pdf"}]}
    mock_client.return_value.get_or_create_collection.return_value = mock_col

    from rag_engine import get_collection_stats
    stats = get_collection_stats()
    assert stats["total_chunks"]   == 42
    assert stats["document_count"] == 1
    assert "report.pdf" in stats["documents"]


# ── parse_pdf (mocked fitz) ────────────────────────────────────────────────────
@patch("rag_engine.fitz.open")
def test_parse_pdf_returns_pages(mock_fitz):
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Sample financial text on page one."
    mock_doc  = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
    mock_fitz.return_value = mock_doc
    from rag_engine import parse_pdf
    pages = parse_pdf("/fake/report.pdf")
    assert isinstance(pages, list)


# ── semantic_search (mocked — including empty-collection guard) ────────────────
@patch("rag_engine._get_client")
@patch("rag_engine.genai.embed_content")
@patch("rag_engine._configure_gemini")
def test_semantic_search_returns_hits(mock_cfg, mock_embed, mock_client):
    mock_embed.return_value = {"embedding": [[0.1] * 768]}
    mock_col = MagicMock()
    mock_col.count.return_value = 3
    mock_col.query.return_value = {
        "documents": [["Relevant financial text"]],
        "metadatas": [[{"source": "report.pdf", "page": 2}]],
        "distances": [[0.12]],
    }
    mock_client.return_value.get_or_create_collection.return_value = mock_col

    from rag_engine import semantic_search
    hits = semantic_search("investment risks")
    assert len(hits) == 1
    assert hits[0]["source"]     == "report.pdf"
    assert hits[0]["page"]       == 2
    assert 0 <= hits[0]["similarity"] <= 1

@patch("rag_engine._get_client")
@patch("rag_engine._configure_gemini")
def test_semantic_search_empty_collection_returns_empty(mock_cfg, mock_client):
    """FIX TEST: empty collection must return [] not crash."""
    mock_col = MagicMock()
    mock_col.count.return_value = 0        # empty
    mock_client.return_value.get_or_create_collection.return_value = mock_col

    from rag_engine import semantic_search
    hits = semantic_search("any query")
    assert hits == []


# ── delete_document ────────────────────────────────────────────────────────────
@patch("rag_engine._get_client")
def test_delete_returns_true_when_found(mock_client):
    mock_col = MagicMock()
    mock_col.get.return_value = {"ids": ["id1", "id2"], "metadatas": []}
    mock_client.return_value.get_or_create_collection.return_value = mock_col
    from rag_engine import delete_document
    assert delete_document("report.pdf") is True
    mock_col.delete.assert_called_once_with(ids=["id1", "id2"])

@patch("rag_engine._get_client")
def test_delete_returns_false_when_not_found(mock_client):
    mock_col = MagicMock()
    mock_col.get.return_value = {"ids": [], "metadatas": []}
    mock_client.return_value.get_or_create_collection.return_value = mock_col
    from rag_engine import delete_document
    assert delete_document("nonexistent.pdf") is False
