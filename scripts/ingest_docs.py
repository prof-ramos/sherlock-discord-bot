import argparse
import logging
import sys
from pathlib import Path

# Ensure src is in python path
sys.path.append(str(Path(__file__).parent.parent))

from src.rag_service import rag_service
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # type: ignore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: Path) -> str:
    if not PdfReader:
        logger.error("pypdf not installed. Cannot read PDF files.")
        sys.exit(1)

    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Simple chunking with overlap."""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size

        # Don't split words if possible (naive approach)
        if end < text_len:
            # Try to find a space near the break point
            while end > start and text[end] not in (' ', '\n', '.', ','):
                end -= 1
            if end == start:  # If no break point found, force split
                end = start + chunk_size

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks

def main():
    parser = argparse.ArgumentParser(description="Ingest documents into Sherlock's Knowledge Base")
    parser.add_argument("file_path", type=Path, help="Path to the PDF or TXT file to ingest")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Size of text chunks")
    parser.add_argument("--overlap", type=int, default=200, help="Overlap between chunks")

    args = parser.parse_args()
    file_path: Path = args.file_path.resolve()

    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        sys.exit(1)

    logger.info("📄 Processing file: %s", file_path.name)

    # Extract text
    if file_path.suffix.lower() == ".pdf":
        text = extract_text_from_pdf(file_path)
    else:
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("Failed to read text file: %s", e)
            sys.exit(1)

    if not text.strip():
        logger.warning("No text found in file.")
        sys.exit(0)

    # Chunk text
    chunks = chunk_text(text, chunk_size=args.chunk_size, overlap=args.overlap)
    logger.info("🧩 Split into %d chunks", len(chunks))

    # Prepare data for ChromaDB
    documents = chunks
    ids = [f"{file_path.stem}_{i}" for i in range(len(chunks))]
    metadatas = [{"source": file_path.name, "chunk_index": i} for i in range(len(chunks))]

    # Add to RAG
    if rag_service.add_documents(documents, metadatas, ids):
        logger.info("✅ Successfully ingested %s", file_path.name)
    else:
        logger.error("❌ Failed to ingest document.")

if __name__ == "__main__":
    main()
