"""FastAPI server for Aviation RAG System."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger

from config import config
from api.auth import verify_api_key
from api.schemas import SearchRequest, SearchResponse, StatsResponse
from search.rag import RAGPipeline
from database.qdrant_manager import QdrantManager

# Initialize
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description=config.API_DESCRIPTION
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize services
rag = RAGPipeline()
db = QdrantManager()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": config.API_TITLE,
        "version": config.API_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}


@app.post("/api/search-regulations", response_model=SearchResponse)
@limiter.limit(f"{config.RATE_LIMIT}/minute")
async def search_regulations(
    request: SearchRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Search for regulations using RAG.

    Requires X-API-Key header for authentication.
    """
    try:
        result = rag.query(
            question=request.query,
            date=request.date,
            limit=request.limit,
            return_sources=True
        )

        return SearchResponse(**result)

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(api_key: str = Depends(verify_api_key)):
    """Get system statistics."""
    try:
        info = db.get_collection_info()
        return StatsResponse(**info)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.RELOAD
    )
