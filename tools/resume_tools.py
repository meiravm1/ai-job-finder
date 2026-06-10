"""Resume text extraction helper used by the Streamlit app (not an LLM tool)."""

import io

from pypdf import PdfReader


def extract_resume_text(uploaded_file) -> str:
    """Extract plain text from an uploaded resume file (.pdf or .txt).

    uploaded_file is a Streamlit UploadedFile (file-like object with .name and read()).
    """
    name = (uploaded_file.name or "").lower()

    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    return uploaded_file.read().decode("utf-8", errors="ignore")
