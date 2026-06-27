"""
Unit tests for FinVista RAG engine
Run with:  pytest tests/ -v
All external services (Gemini, Groq, ChromaDB) are mocked — no API calls made.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key-for-unit-tests")
os.environ.setdefault("GROQ_API_KEY",   "test-groq-key-for-unit-tests")

@pytest.fixture
def sample_pages():
    return [
        {"page": 1, "text": "FinVista Capital Q1 2024 Annual Report. Revenue grew 15% YoY.", "source": "annual_report.pdf"},
        {"page": 2, "text": "Risk factors include market volatility and regulatory changes.", "source": "annual_report.pdf"},
        {"page": 3, "text": "Investment guidelines require diversification across asset classes.", "source": "annual_report.pdf"},
    ]

@pytest.fixture
def sample_chunks():
    return [
        {"text": "Revenue grew 15% YoY", "source": "annual_report.pdf", "page": 1, "chunk": 0},
        {"text": "Risk factors include market volatility", "source": "annual_report.pdf", "page": 2, "chunk": 0},
    ]

def test_chunk_pages_returns_list(sample_pages):
    from rag_engine import chunk_pages
    assert isinstance(chunk_pages(sample_pages), list)
    assert len(chunk_pages(sample_pages)) >= len(sample_pages)

def test_chunk_pages_required_keys(sample_pages):
    from rag_engine import chunk_pages
    for chunk in chunk_pages(sample_pages):
        for key in ("text", "source", "page", "chunk"):
            assert key in chunk

def test_chunk_pages_source_preserved(sample_pages):
    from rag_engine import chunk_pages
    for chunk in chunk_pages(sample_pages):
        assert chunk["source"] == "annual_report.pdf"

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

@patch("rag_engine._get_chroma_client")
def test_collection_stats_shape(mock_client):
    mock_col = MagicMock()
    mock_col.count.return_value = 42
    mock_col.get.return_value = {"metadatas": [{"source": "report.pdf"}]}
    mock_client.return_value.get_or_create_collection.return_value = mock_col
    from rag_engine import get_collection_stats
    stats = get_collection_stats()
    assert stats["total_chunks"] == 42
    assert stats["document_count"] == 1
    assert "report.pdf" in stats["documents"]

@patch("rag_engine.fitz.open")
def test_parse_pdf_returns_pages(mock_fitz):
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Sample financial text on page one."
    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
    mock_fitz.return_value = mock_doc
    from rag_engine import parse_pdf
    assert isinstance(parse_pdf("/fake/report.pdf"), list)

@patch("rag_engine._get_chroma_client")
@patch("rag_engine._get_gemini_client")
def test_semantic_search_returns_hits(mock_gemini, mock_chroma):
    mock_embed_result = MagicMock()
    mock_embed_result.embeddings = [MagicMock(values=[0.1] * 768)]
    mock_gemini.return_value.models.embed_content.return_value = mock_embed_result
    mock_col = MagicMock()
    mock_col.count.return_value = 3
    mock_col.query.return_value = {
        "documents": [["Relevant financial text"]],
        "metadatas": [[{"source": "report.pdf", "page": 2}]],
        "distances": [[0.12]],
    }
    mock_chroma.return_value.get_or_create_collection.return_value = mock_col
    from rag_engine import semantic_search
    hits = semantic_search("investment risks")
    assert len(hits) == 1
    assert hits[0]["source"] == "report.pdf"
    assert 0 <= hits[0]["similarity"] <= 1

@patch("rag_engine._get_chroma_client")
def test_semantic_search_empty_collection_returns_empty(mock_chroma):
    mock_col = MagicMock()
    mock_col.count.return_value = 0
    mock_chroma.return_value.get_or_create_collection.return_value = mock_col
    from rag_engine import semantic_search
    assert semantic_search("any query") == []

@patch("rag_engine._get_chroma_client")
def test_delete_returns_true_when_found(mock_chroma):
    mock_col = MagicMock()
    mock_col.get.return_value = {"ids": ["id1", "id2"], "metadatas": []}
    mock_chroma.return_value.get_or_create_collection.return_value = mock_col
    from rag_engine import delete_document
    assert delete_document("report.pdf") is True

@patch("rag_engine._get_chroma_client")
def test_delete_returns_false_when_not_found(mock_chroma):
    mock_col = MagicMock()
    mock_col.get.return_value = {"ids": [], "metadatas": []}
    mock_chroma.return_value.get_or_create_collection.return_value = mock_col
    from rag_engine import delete_document
    assert delete_document("nonexistent.pdf") is False
