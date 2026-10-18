"""
FastAPI main application for SAP Customizing RAG.
"""
import json
import logging
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.config import settings
from backend.integrations.bigquery_client import BigQueryClient
from backend.integrations.mistral_client import MistralClient
from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.chat_service import ChatService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize clients and services
bq_client = BigQueryClient()
mistral_client = MistralClient()
chat_service = ChatService(bq_client, mistral_client)

# Create FastAPI app
app = FastAPI(
    title="SAP Customizing RAG API",
    description="API for SAP Customizing documentation RAG chat",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Chat Endpoints
# =============================================================================

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Process a chat request with agentic retrieval.
    For streaming, use /api/chat/stream
    """
    # Create a session if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    response = chat_service.chat(request, session_id)
    # Add session_id to response
    response.session_id = session_id
    return response


@app.post("/api/chat/stream")
def chat_stream_endpoint(request: ChatRequest):
    """
    Process a chat request with streaming response.
    Returns a Server-Sent Events stream.
    """
    # For now, return the full response as a stream
    # In production, this would stream tokens as they are generated
    response = chat_service.chat(request)
    
    async def generate():
        # Send the full response as a single event
        yield f"data: {json.dumps(response.model_dump())}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


# =============================================================================
# Object Endpoints
# =============================================================================
# Note: the graph route must be declared before the object route because the
# :path converter is greedy and would otherwise also capture "/graph" suffixes.

@app.get("/api/object/{object_id:path}/graph")
def get_object_graph(object_id: str, scope: str = "both"):
    """Get graph data (nodes and edges) for an object."""
    graph = bq_client.get_related_objects(object_id, depth=1, scope=scope)
    return graph


@app.get("/api/object/{object_id:path}")
def get_object(object_id: str, scope: str = "both"):
    """Get full information for an SAP object."""
    obj_info = bq_client.get_object_info(object_id, scope=scope)
    if not obj_info:
        raise HTTPException(status_code=404, detail="Object not found")
    
    return obj_info


# =============================================================================
# Health Check
# =============================================================================

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
