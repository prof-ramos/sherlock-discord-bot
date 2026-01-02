import asyncio
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

try:
    from docx import Document
except ImportError:
    Document = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore

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

def extract_text_from_docx(docx_path: Path) -> str:
    if not Document:
        logger.error("python-docx not installed. Cannot read DOCX files.")
        sys.exit(1)

    doc = Document(docx_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def extract_text_from_html(html_path: Path) -> str:
    if not BeautifulSoup:
        logger.error("beautifulsoup4 not installed. Cannot read HTML files.")
        sys.exit(1)

    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()

    # Get text
    text = soup.get_text()

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

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
    parser.add_argument("file_path", type=Path, help="Path to the PDF, DOCX, HTML, or TXT file to ingest")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Size of text chunks")
    parser.add_argument("--overlap", type=int, default=200, help="Overlap between chunks")

    args = parser.parse_args()
    file_path: Path = args.file_path.resolve()

    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        sys.exit(1)

    logger.info("📄 Processing file: %s", file_path.name)

    # Extract text based on file type
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".pdf":
            text = extract_text_from_pdf(file_path)
        elif suffix == ".docx":
            text = extract_text_from_docx(file_path)
        elif suffix == ".html":
            text = extract_text_from_html(file_path)
        elif suffix in [".txt", ".md", ".text"]:
            text = file_path.read_text(encoding="utf-8")
        else:
            logger.error("Unsupported file format: %s. Supported formats: PDF, DOCX, HTML, TXT, MD", suffix)
            sys.exit(1)
    except Exception as e:
        logger.error("Failed to extract text from %s: %s", file_path.name, e)
        sys.exit(1)

    if not text.strip():
        logger.warning("No text found in file.")
        sys.exit(0)

    # Chunk text
    chunks = chunk_text(text, chunk_size=args.chunk_size, overlap=args.overlap)
    logger.info("🧩 Split into %d chunks", len(chunks))

    # Prepare data for RAG
    documents = chunks
    ids = [f"{file_path.stem}_{i}" for i in range(len(chunks))]
    metadatas = [{"source": file_path.name, "chunk_index": i} for i in range(len(chunks))]

    async def ingest():
        try:
            # Add to RAG
            if await rag_service.add_documents(documents, metadatas, ids):
                logger.info("✅ Successfully ingested %s", file_path.name)
            else:
                logger.error("❌ Failed to ingest document.")
                sys.exit(1)
        except Exception as e:
            logger.error("❌ RAG service error during ingestion: %s", e)
            sys.exit(1)

    try:
        asyncio.run(ingest())
    except KeyboardInterrupt:
        logger.info("Ingestion cancelled.")
    except Exception as e:
        logger.exception("Ingestion failed: %s", e)

if __name__ == "__main__":
    main()