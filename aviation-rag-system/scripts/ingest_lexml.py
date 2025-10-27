"""Script to ingest LexML documents."""

import argparse
from pathlib import Path
from loguru import logger

from parsers.lexml_scraper import LexMLScraper
from pipeline.ingestion import IngestionPipeline
from config import config


def main():
    parser = argparse.ArgumentParser(description="Ingest LexML documents")
    parser.add_argument("--keywords", type=str, help="Comma-separated keywords")
    parser.add_argument("--limit", type=int, default=100, help="Max documents")
    parser.add_argument("--download-dir", type=str, default="./data/lexml")
    args = parser.parse_args()

    # Parse keywords
    keywords = args.keywords.split(",") if args.keywords else config.lexml_keywords_list

    logger.info(f"Searching LexML for: {keywords}")

    # Search and download
    scraper = LexMLScraper()
    documents = scraper.search(keywords=keywords, limit=args.limit)

    logger.info(f"Found {len(documents)} documents")

    # Download XMLs
    download_dir = Path(args.download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)

    xml_paths = []
    for i, doc in enumerate(documents):
        urn = doc.get("urn")
        if not urn:
            continue

        xml_path = download_dir / f"doc_{i}.xml"
        if scraper.download_xml(urn, str(xml_path)):
            xml_paths.append(str(xml_path))

    logger.info(f"Downloaded {len(xml_paths)} XMLs")

    # Ingest
    pipeline = IngestionPipeline()
    total = pipeline.ingest_lexml(xml_paths)

    logger.success(f"✓ Ingested {total} chunks from {len(xml_paths)} documents")
    return 0


if __name__ == "__main__":
    exit(main())
