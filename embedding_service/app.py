"""Embedding service for Hugging Face Space deployment."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Embedding Service")

# Load model once at startup
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
model = None


@app.on_event("startup")
async def load_model():
    """Load embedding model at startup."""
    global model
    try:
        logger.info(f"Loading embedding model: {MODEL_NAME}")
        model = SentenceTransformer(MODEL_NAME)
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


class EmbedRequest(BaseModel):
    """Request model for embedding endpoint."""
    texts: List[str]


class EmbedResponse(BaseModel):
    """Response model for embedding endpoint."""
    embeddings: List[List[float]]


@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest):
    """
    Generate embeddings for texts.
    
    Args:
        request: EmbedRequest with list of texts
        
    Returns:
        EmbedResponse with list of embedding vectors
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if not request.texts:
        raise HTTPException(status_code=400, detail="Texts list cannot be empty")
    
    try:
        embeddings = model.encode(request.texts, show_progress_bar=False).tolist()
        return EmbedResponse(embeddings=embeddings)
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating embeddings: {str(e)}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_name": MODEL_NAME if model is not None else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
