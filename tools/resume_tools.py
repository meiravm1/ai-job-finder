"""Resume text extraction helper used by the Streamlit app (not an LLM tool)."""

import io
import logging

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_resume_text(uploaded_file) -> str:
    """Extract plain text from an uploaded resume file (.pdf or .txt).

    uploaded_file is a Streamlit UploadedFile (file-like object with .name and read()).
    """
    name = (uploaded_file.name or "").lower()
    logger.info("Extracting resume text from %s", name)

    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        logger.info("Extracted %d chars from %d PDF page(s) in %s", len(text), len(reader.pages), name)
        return text

    text = uploaded_file.read().decode("utf-8", errors="ignore")
    logger.info("Extracted %d chars from text file %s", len(text), name)
    return text
