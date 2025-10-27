"""Chunking module for splitting documents into optimal chunks."""

from typing import Dict, List
from loguru import logger
from config import config


class ArticleChunker:
    """Chunker that splits articles intelligently."""

    def __init__(self, max_tokens: int = None, overlap: int = None):
        self.max_tokens = max_tokens or config.CHUNK_MAX_TOKENS
        self.overlap = overlap or config.CHUNK_OVERLAP
        logger.info(f"ArticleChunker initialized (max_tokens={self.max_tokens})")

    def chunk(self, article: Dict) -> List[Dict]:
        """
        Chunk an article into smaller pieces if needed.

        Args:
            article: Article dictionary with 'text' field

        Returns:
            List of chunk dictionaries
        """
        text = article.get("text", "")
        estimated_tokens = len(text.split())

        # If article is small enough, return as single chunk
        if estimated_tokens <= self.max_tokens:
            return [article]

        # Split into paragraphs
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para.split())

            if current_size + para_size > self.max_tokens and current_chunk:
                # Save current chunk
                chunk = self._create_chunk(article, '\n\n'.join(current_chunk), len(chunks))
                chunks.append(chunk)

                # Start new chunk with overlap
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        # Add remaining
        if current_chunk:
            chunk = self._create_chunk(article, '\n\n'.join(current_chunk), len(chunks))
            chunks.append(chunk)

        logger.debug(f"Split article into {len(chunks)} chunks")
        return chunks

    def _create_chunk(self, article: Dict, text: str, chunk_idx: int) -> Dict:
        """Create chunk dictionary."""
        chunk = article.copy()
        chunk["text"] = text
        chunk["chunk_index"] = chunk_idx
        chunk["regulation_id"] = f"{article.get('regulation_id', 'unknown')}-chunk-{chunk_idx}"
        return chunk


if __name__ == "__main__":
    chunker = ArticleChunker()
    print("ArticleChunker ready")
