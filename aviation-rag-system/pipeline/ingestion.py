"""End-to-end ingestion pipeline."""

from typing import List, Dict
from loguru import logger
from tqdm import tqdm

from models.embeddings import EmbeddingModel
from parsers import LexMLParser, PDFParser
from pipeline.chunking import ArticleChunker
from database.qdrant_manager import QdrantManager


class IngestionPipeline:
    """End-to-end pipeline for ingesting documents."""

    def __init__(self):
        self.embedding_model = EmbeddingModel()
        self.lexml_parser = LexMLParser()
        self.pdf_parser = PDFParser()
        self.chunker = ArticleChunker()
        self.db = QdrantManager()
        logger.info("IngestionPipeline initialized")

    def ingest_lexml(self, xml_paths: List[str]) -> int:
        """Ingest LexML XML documents."""
        total_chunks = 0

        for xml_path in tqdm(xml_paths, desc="Ingesting LexML"):
            try:
                # Parse
                articles = self.lexml_parser.parse_xml(xml_path)

                # Chunk
                chunks = []
                for article in articles:
                    chunks.extend(self.chunker.chunk(article))

                # Embed
                texts = [c["text"] for c in chunks]
                embeddings = self.embedding_model.encode(texts, show_progress=False)

                # Prepare points
                points = []
                for chunk, embedding in zip(chunks, embeddings):
                    points.append({
                        "id": chunk.get("regulation_id"),
                        "vector": embedding.tolist(),
                        "payload": chunk
                    })

                # Upload
                self.db.upsert_points(points)
                total_chunks += len(points)

            except Exception as e:
                logger.error(f"Error ingesting {xml_path}: {e}")

        logger.success(f"Ingested {total_chunks} chunks from {len(xml_paths)} documents")
        return total_chunks

    def ingest_pdfs(self, pdf_paths: List[str]) -> int:
        """Ingest PDF documents."""
        total_sections = 0

        for pdf_path in tqdm(pdf_paths, desc="Ingesting PDFs"):
            try:
                sections = self.pdf_parser.parse_pdf(pdf_path)
                texts = [s["text"] for s in sections]
                embeddings = self.embedding_model.encode(texts, show_progress=False)

                points = []
                for section, embedding in zip(sections, embeddings):
                    points.append({
                        "id": section.get("regulation_id"),
                        "vector": embedding.tolist(),
                        "payload": section
                    })

                self.db.upsert_points(points)
                total_sections += len(points)

            except Exception as e:
                logger.error(f"Error ingesting {pdf_path}: {e}")

        logger.success(f"Ingested {total_sections} sections from {len(pdf_paths)} PDFs")
        return total_sections


if __name__ == "__main__":
    pipeline = IngestionPipeline()
    print("IngestionPipeline ready")
