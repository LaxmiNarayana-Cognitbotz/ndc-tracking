import logging

import fitz

logger = logging.getLogger(__name__)


def trim_pdf_to_max_pages(file_bytes: bytes, max_pages: int = 2, filename: str = "document.pdf") -> bytes:
    """
    Trim a PDF document to a maximum number of pages.
    If the file is not a PDF, or has fewer pages, it returns the original file_bytes unchanged.
    """
    if not filename.lower().endswith(".pdf"):
        return file_bytes

    try:
        # Open PDF from bytes
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        # Check if trimming is needed
        if len(doc) <= max_pages:
            doc.close()
            return file_bytes
        
        doc.select(range(max_pages))
        
        # Save to new bytes.
        trimmed_bytes = doc.tobytes(garbage=3, deflate=True)
        doc.close()
        
        logger.info(f"Successfully trimmed {filename} to {max_pages} pages.")
        return trimmed_bytes
    except Exception as e:
        logger.error(f"Failed to trim PDF '{filename}': {e}")
        return file_bytes
