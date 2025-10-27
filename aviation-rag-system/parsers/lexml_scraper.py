"""
LexML Scraper Module for Aviation RAG System.

This module scrapes legal documents from LexML Brasil API.

Usage:
    from parsers.lexml_scraper import LexMLScraper

    scraper = LexMLScraper()
    documents = scraper.search(keywords=["aviação", "ANAC"], limit=100)
"""

import time
from typing import Dict, List, Optional
from urllib.parse import quote

import requests
from loguru import logger
from lxml import etree

from config import config


class LexMLScraper:
    """Scraper for LexML Brasil SRU API."""

    def __init__(self, api_url: str = None, max_records_per_page: int = None):
        """
        Initialize LexML scraper.

        Args:
            api_url: LexML SRU API URL
            max_records_per_page: Maximum records per page
        """
        self.api_url = api_url or config.LEXML_API_URL
        self.max_records_per_page = max_records_per_page or config.LEXML_MAX_RECORDS_PER_PAGE
        self.session = requests.Session()
        logger.info(f"LexMLScraper initialized (API: {self.api_url})")

    def search(
        self,
        keywords: List[str] = None,
        doc_types: List[str] = None,
        authority_level: str = "federal",
        limit: int = 100,
        start_record: int = 1
    ) -> List[Dict]:
        """
        Search for documents in LexML.

        Args:
            keywords: Keywords to search (e.g., ["aviação", "ANAC"])
            doc_types: Document types (e.g., ["lei", "decreto"])
            authority_level: Authority level (federal, estadual, municipal)
            limit: Maximum number of documents
            start_record: Starting record number

        Returns:
            List of document metadata dictionaries
        """
        keywords = keywords or config.lexml_keywords_list
        query = self._build_query(keywords, doc_types, authority_level)

        logger.info(f"Searching LexML: {query} (limit={limit})")

        documents = []
        current_start = start_record

        while len(documents) < limit:
            records_to_fetch = min(self.max_records_per_page, limit - len(documents))

            params = {
                "operation": "searchRetrieve",
                "version": "1.1",
                "query": query,
                "startRecord": current_start,
                "maximumRecords": records_to_fetch
            }

            try:
                response = self.session.get(self.api_url, params=params, timeout=30)
                response.raise_for_status()

                # Parse XML response
                batch_docs = self._parse_sru_response(response.content)

                if not batch_docs:
                    logger.info("No more documents found")
                    break

                documents.extend(batch_docs)
                logger.info(f"Retrieved {len(documents)}/{limit} documents")

                current_start += len(batch_docs)
                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                logger.error(f"Error fetching documents: {e}")
                break

        return documents[:limit]

    def _build_query(
        self,
        keywords: List[str],
        doc_types: List[str] = None,
        authority_level: str = "federal"
    ) -> str:
        """Build SRU CQL query."""
        parts = []

        # Keywords
        if keywords:
            keyword_queries = [f'dc.subject any "{kw}"' for kw in keywords]
            parts.append(f"({' or '.join(keyword_queries)})")

        # Document types
        if doc_types:
            type_queries = [f'dc.type any "{dt}"' for dt in doc_types]
            parts.append(f"({' or '.join(type_queries)})")

        # Authority level
        if authority_level:
            parts.append(f'urn any "br:{authority_level}"')

        query = " and ".join(parts) if parts else "dc.subject any aviação"
        return query

    def _parse_sru_response(self, xml_content: bytes) -> List[Dict]:
        """Parse SRU XML response."""
        try:
            root = etree.fromstring(xml_content)
            namespaces = {
                'srw': 'http://www.loc.gov/zing/srw/',
                'dc': 'http://purl.org/dc/elements/1.1/'
            }

            records = root.xpath('//srw:record', namespaces=namespaces)
            documents = []

            for record in records:
                doc = self._parse_record(record, namespaces)
                if doc:
                    documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Error parsing SRU response: {e}")
            return []

    def _parse_record(self, record, namespaces: Dict) -> Optional[Dict]:
        """Parse individual SRU record."""
        try:
            doc = {
                "urn": self._get_text(record, './/dc:identifier', namespaces),
                "title": self._get_text(record, './/dc:title', namespaces),
                "type": self._get_text(record, './/dc:type', namespaces),
                "date": self._get_text(record, './/dc:date', namespaces),
                "description": self._get_text(record, './/dc:description', namespaces),
            }

            # Parse URN for more details
            if doc["urn"]:
                doc.update(self._parse_urn(doc["urn"]))

            return doc

        except Exception as e:
            logger.warning(f"Error parsing record: {e}")
            return None

    def _get_text(self, element, xpath: str, namespaces: Dict) -> Optional[str]:
        """Extract text from XML element."""
        result = element.xpath(xpath, namespaces=namespaces)
        return result[0].text if result and result[0].text else None

    def _parse_urn(self, urn: str) -> Dict:
        """
        Parse LexML URN.

        Example: urn:lex:br:federal:lei:1993-06-21;8666
        """
        parts = urn.split(':')
        if len(parts) >= 6:
            date_and_number = parts[5].split(';')
            return {
                "authority": parts[3],
                "doc_type": parts[4],
                "publication_date": date_and_number[0] if date_and_number else None,
                "number": date_and_number[1] if len(date_and_number) > 1 else None
            }
        return {}

    def download_xml(self, urn: str, output_path: str) -> bool:
        """
        Download full XML for a document.

        Args:
            urn: Document URN
            output_path: Path to save XML

        Returns:
            True if successful
        """
        # Construct XML URL (may vary by LexML implementation)
        xml_url = f"{self.api_url}/xml?urn={quote(urn)}"

        try:
            response = self.session.get(xml_url, timeout=30)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded XML: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error downloading XML for {urn}: {e}")
            return False


if __name__ == "__main__":
    """Example usage."""
    scraper = LexMLScraper()

    # Search for aviation-related laws
    documents = scraper.search(
        keywords=["aviação", "aeronave"],
        doc_types=["lei"],
        limit=10
    )

    print(f"\nFound {len(documents)} documents:")
    for doc in documents[:5]:
        print(f"- {doc.get('title')} ({doc.get('urn')})")
