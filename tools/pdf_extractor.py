"""PDF text extraction."""
import logging
from typing import Optional
from pathlib import Path
import PyPDF2
import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """
    Extract text from PDF file.
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Extracted text or None if error
    """
    try:
        # Try pdfplumber first (better for complex layouts)
        with pdfplumber.open(pdf_path) as pdf:
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            if text_parts:
                return "\n\n".join(text_parts)
    except Exception as e:
        logger.warning(f"pdfplumber failed for {pdf_path}, trying PyPDF2: {e}")
    
    try:
        # Fallback to PyPDF2
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            if text_parts:
                return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        return None
    
    return None


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Optional[str]:
    """
    Extract text from PDF bytes.
    
    Args:
        pdf_bytes: PDF file content as bytes
    
    Returns:
        Extracted text or None if error
    """
    import io
    try:
        # Try pdfplumber first
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            if text_parts:
                return "\n\n".join(text_parts)
    except Exception as e:
        logger.warning(f"pdfplumber failed, trying PyPDF2: {e}")
    
    try:
        # Fallback to PyPDF2
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text_parts = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        if text_parts:
            return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"Error extracting text from PDF bytes: {e}")
        return None
    
    return None

