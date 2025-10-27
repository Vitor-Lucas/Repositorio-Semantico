"""Pydantic schemas for API."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request schema."""
    query: str = Field(..., max_length=1000, description="Search query")
    date: Optional[str] = Field(None, description="Target date (ISO format: YYYY-MM-DD)")
    limit: int = Field(5, ge=1, le=50, description="Number of results")
    score_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    filters: Optional[Dict] = Field(None, description="Additional filters")


class SourceDocument(BaseModel):
    """Source document schema."""
    regulation_id: str
    text: str
    score: float
    version: Optional[str] = None
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    metadata: Dict = {}


class SearchResponse(BaseModel):
    """Search response schema."""
    answer: str
    sources: List[SourceDocument]
    search_time_ms: int
    llm_time_ms: int
    total_time_ms: int


class StatsResponse(BaseModel):
    """System statistics response."""
    vectors_count: int
    points_count: int
    status: str
