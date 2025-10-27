"""
Qdrant Manager for Aviation RAG System.

Handles all interactions with Qdrant vector database.
"""

import uuid
from typing import Dict, List, Optional

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition,
    DatetimeRange, MatchValue, PayloadSchemaType, HnswConfigDiff
)

from config import config


class QdrantManager:
    """Manager for Qdrant vector database operations."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        collection_name: str = None,
        api_key: str = None
    ):
        """
        Initialize Qdrant manager.

        Args:
            host: Qdrant host
            port: Qdrant port
            collection_name: Collection name
            api_key: API key for Qdrant Cloud
        """
        self.host = host or config.QDRANT_HOST
        self.port = port or config.QDRANT_PORT
        self.collection_name = collection_name or config.QDRANT_COLLECTION_NAME
        self.api_key = api_key or config.QDRANT_API_KEY

        # Initialize client
        if self.api_key:
            self.client = QdrantClient(url=self.host, api_key=self.api_key)
        else:
            self.client = QdrantClient(host=self.host, port=self.port)

        logger.info(f"QdrantManager initialized ({self.host}:{self.port})")

    def create_collection(
        self,
        vector_size: int = None,
        distance: Distance = Distance.COSINE,
        recreate: bool = False
    ) -> bool:
        """
        Create collection with optimized configuration.

        Args:
            vector_size: Embedding dimension
            distance: Distance metric
            recreate: Recreate if exists

        Returns:
            True if successful
        """
        vector_size = vector_size or config.EMBEDDING_DIMENSION

        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if exists and not recreate:
                logger.info(f"Collection '{self.collection_name}' already exists")
                return True

            if exists and recreate:
                self.client.delete_collection(self.collection_name)
                logger.warning(f"Deleted existing collection '{self.collection_name}'")

            # Create collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance,
                    hnsw_config=HnswConfigDiff(
                        m=config.HNSW_M,
                        ef_construct=config.HNSW_EF_CONSTRUCT
                    )
                )
            )

            logger.success(f"Created collection '{self.collection_name}'")

            # Create payload indexes
            self._create_payload_indexes()

            return True

        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            return False

    def _create_payload_indexes(self):
        """Create indexes on payload fields for fast filtering."""
        indexes = [
            ("effective_date", PayloadSchemaType.DATETIME),
            ("expiry_date", PayloadSchemaType.DATETIME),
            ("status", PayloadSchemaType.KEYWORD),
            ("regulation_id", PayloadSchemaType.KEYWORD),
            ("metadata.category", PayloadSchemaType.KEYWORD),
        ]

        for field_name, schema_type in indexes:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=schema_type
                )
                logger.debug(f"Created index on '{field_name}'")
            except Exception as e:
                logger.warning(f"Could not create index on '{field_name}': {e}")

    def upsert_points(
        self,
        points: List[Dict],
        batch_size: int = 100
    ) -> bool:
        """
        Upsert points to collection.

        Args:
            points: List of point dictionaries with id, vector, payload
            batch_size: Batch size for upload

        Returns:
            True if successful
        """
        try:
            # Convert to PointStruct
            qdrant_points = []
            for point in points:
                point_id = point.get("id") or str(uuid.uuid4())
                qdrant_points.append(PointStruct(
                    id=point_id,
                    vector=point["vector"],
                    payload=point.get("payload", {})
                ))

            # Upload in batches
            for i in range(0, len(qdrant_points), batch_size):
                batch = qdrant_points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                logger.debug(f"Uploaded batch {i//batch_size + 1}")

            logger.success(f"Upserted {len(points)} points")
            return True

        except Exception as e:
            logger.error(f"Error upserting points: {e}")
            return False

    def search(
        self,
        query_vector: List[float],
        limit: int = None,
        score_threshold: float = None,
        filters: Dict = None,
        with_payload: bool = True
    ) -> List:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding
            limit: Number of results
            score_threshold: Minimum similarity score
            filters: Qdrant filter dict
            with_payload: Return payload with results

        Returns:
            List of search results
        """
        limit = limit or config.SEARCH_TOP_K
        score_threshold = score_threshold or config.SEARCH_SCORE_THRESHOLD

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filters,
                with_payload=with_payload,
                search_params={"hnsw_ef": config.HNSW_EF_SEARCH}
            )

            logger.debug(f"Search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []

    def search_temporal(
        self,
        query_vector: List[float],
        target_date: str,
        limit: int = None,
        additional_filters: Dict = None
    ) -> List:
        """
        Search with temporal filtering (regulations valid on target_date).

        Args:
            query_vector: Query embedding
            target_date: ISO format date
            limit: Number of results
            additional_filters: Additional Qdrant filters

        Returns:
            List of search results valid on target_date
        """
        # Build temporal filter
        temporal_filter = Filter(
            must=[
                FieldCondition(key="status", match=MatchValue(value="active")),
                FieldCondition(key="effective_date", range=DatetimeRange(lte=target_date)),
                {
                    "should": [
                        FieldCondition(key="expiry_date", range=DatetimeRange(gte=target_date)),
                        FieldCondition(key="expiry_date", match=MatchValue(value=None))
                    ]
                }
            ]
        )

        # Merge with additional filters if provided
        if additional_filters:
            if isinstance(additional_filters, Filter):
                temporal_filter.must.extend(additional_filters.must or [])
            elif isinstance(additional_filters, dict):
                temporal_filter.must.append(additional_filters)

        return self.search(
            query_vector=query_vector,
            limit=limit,
            filters=temporal_filter
        )

    def get_collection_info(self) -> Dict:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}


if __name__ == "__main__":
    """Example usage."""
    manager = QdrantManager()
    info = manager.get_collection_info()
    print(f"Collection info: {info}")
