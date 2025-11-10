"""Text chunking for RAG."""
from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    url: str,
    title: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Dict[str, str]]:
    """
    Chunk text with heading awareness.
    
    Args:
        text: Text to chunk
        url: Source URL
        title: Document title
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
    
    Returns:
        List of chunks with metadata
    """
    if not text:
        return []
    
    # Split by headings (h1-h6 patterns)
    heading_pattern = re.compile(r'(^#{1,6}\s+.+$)', re.MULTILINE)
    sections = []
    last_pos = 0
    
    for match in heading_pattern.finditer(text):
        if match.start() > last_pos:
            sections.append({
                "heading": None,
                "text": text[last_pos:match.start()].strip(),
                "start": last_pos
            })
        sections.append({
            "heading": match.group(1),
            "text": match.group(1),
            "start": match.start()
        })
        last_pos = match.end()
    
    # Add remaining text
    if last_pos < len(text):
        sections.append({
            "heading": None,
            "text": text[last_pos:].strip(),
            "start": last_pos
        })
    
    # If no headings found, split by paragraphs
    if len(sections) == 1:
        paragraphs = text.split("\n\n")
        sections = [{"heading": None, "text": p.strip(), "start": 0} for p in paragraphs if p.strip()]
    
    # Create chunks with overlap
    chunks = []
    current_chunk = ""
    current_heading = None
    
    for section in sections:
        section_text = section["text"]
        section_heading = section["heading"]
        
        if section_heading:
            current_heading = section_heading
        
        # If adding this section would exceed chunk size, finalize current chunk
        if current_chunk and len(current_chunk) + len(section_text) > chunk_size:
            if current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "url": url,
                    "title": title,
                    "heading": current_heading,
                    "metadata": {
                        "url": url,
                        "title": title,
                        "heading": current_heading or ""
                    }
                })
            
            # Start new chunk with overlap
            if chunk_overlap > 0 and current_chunk:
                overlap_text = current_chunk[-chunk_overlap:]
                current_chunk = overlap_text + "\n\n" + section_text
            else:
                current_chunk = section_text
        else:
            if current_chunk:
                current_chunk += "\n\n" + section_text
            else:
                current_chunk = section_text
    
    # Add final chunk
    if current_chunk:
        chunks.append({
            "text": current_chunk.strip(),
            "url": url,
            "title": title,
            "heading": current_heading,
            "metadata": {
                "url": url,
                "title": title,
                "heading": current_heading or ""
            }
        })
    
    # Ensure chunks are within size limit
    final_chunks = []
    for chunk in chunks:
        if len(chunk["text"]) <= chunk_size:
            final_chunks.append(chunk)
        else:
            # Split oversized chunks
            words = chunk["text"].split()
            current_text = ""
            for word in words:
                if len(current_text) + len(word) + 1 <= chunk_size:
                    current_text += (" " if current_text else "") + word
                else:
                    if current_text:
                        final_chunks.append({
                            "text": current_text,
                            "url": url,
                            "title": title,
                            "heading": chunk["heading"],
                            "metadata": chunk["metadata"]
                        })
                    current_text = word
            if current_text:
                final_chunks.append({
                    "text": current_text,
                    "url": url,
                    "title": title,
                    "heading": chunk["heading"],
                    "metadata": chunk["metadata"]
                })
    
    logger.info(f"Created {len(final_chunks)} chunks from text (length: {len(text)})")
    return final_chunks

