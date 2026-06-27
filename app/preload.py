"""
Preload PDFs into ChromaDB on pod startup.
Runs once when container starts.
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, '/app/app')

def preload():
    # Only run if keys are set
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        logger.info("No GEMINI_API_KEY set — skipping preload")
        return

    from rag_engine import index_document, get_collection_stats

    # Check if already indexed
    stats = get_collection_stats()
    if stats["total_chunks"] > 0:
        logger.info("ChromaDB already has %d chunks — skipping preload", stats["total_chunks"])
        return

    # Index all PDFs in data folder
    data_dir = "/app/app/data"
    if not os.path.exists(data_dir):
        logger.info("No data directory found — skipping preload")
        return

    pdfs = [f for f in os.listdir(data_dir) if f.endswith(".pdf")]
    if not pdfs:
        logger.info("No PDFs found in data directory")
        return

    logger.info("Preloading %d PDFs...", len(pdfs))
    for pdf in sorted(pdfs):
        path = os.path.join(data_dir, pdf)
        try:
            n = index_document(path)
            logger.info("✅ Indexed %s — %d chunks", pdf, n)
        except Exception as e:
            logger.error("❌ Failed to index %s: %s", pdf, e)

    stats = get_collection_stats()
    logger.info("Preload complete: %d docs, %d chunks",
                stats["document_count"], stats["total_chunks"])

if __name__ == "__main__":
    preload()
