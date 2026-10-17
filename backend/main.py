"""
FastAPI main application for SAP Fit-Gap RAG.
"""
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings, ensure_upload_dir
from backend.integrations.bigquery_client import BigQueryClient
from backend.integrations.gcs_client import GCSClient
from backend.integrations.mistral_client import MistralClient
from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
    CreateSessionRequest,
    FitGapResult,
    Session,
    SessionKind,
    SessionStatus,
)
from backend.services.chat_service import ChatService
from backend.services.decision_service import DecisionService
from backend.services.pdf_pipeline import PDFPipeline
from backend.services.requirement_service import RequirementService
from backend.services.verdict_service import VerdictService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize clients and services
bq_client = BigQueryClient()
mistral_client = MistralClient()
gcs_client = GCSClient()

requirement_service = RequirementService(mistral_client)
verdict_service = VerdictService(bq_client, mistral_client, requirement_service)
decision_service = DecisionService(mistral_client)
chat_service = ChatService(bq_client, mistral_client)
pdf_pipeline = PDFPipeline(
    bq_client, mistral_client, gcs_client,
    requirement_service, verdict_service, decision_service
)

# Create FastAPI app
app = FastAPI(
    title="SAP Fit-Gap RAG API",
    description="API for SAP Customizing fit-gap analysis using RAG",
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

# Ensure upload directory exists
ensure_upload_dir()


# =============================================================================
# Session Endpoints
# =============================================================================

@app.post("/api/sessions", response_model=Session)
def create_session(request: CreateSessionRequest):
    """Create a new analysis session."""
    session_id = str(uuid.uuid4())
    
    bq_client.create_session(
        session_id=session_id,
        kind=request.kind.value,
        title=request.title or f"Session {session_id[:8]}",
        source_ref=None
    )
    
    session = bq_client.get_session(session_id)
    return Session(**session)


@app.get("/api/sessions", response_model=List[Session])
def list_sessions(limit: int = 100):
    """List recent sessions."""
    sessions = bq_client.list_sessions(limit)
    return [Session(**s) for s in sessions]


@app.get("/api/sessions/{session_id}", response_model=Session)
def get_session(session_id: str):
    """Get session details."""
    session = bq_client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return Session(**session)


@app.delete("/api/sessions", response_model=Dict[str, int])
def clear_all_sessions():
    """Clear all sessions and their related data."""
    return bq_client.clear_all_sessions()


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
    # In production, this would stream tokens as they're generated
    response = chat_service.chat(request)
    
    async def generate():
        # Send the full response as a single event
        yield f"data: {json.dumps(response.model_dump())}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


# =============================================================================
# PDF Upload and Fit-Gap Analysis
# =============================================================================

@app.post("/api/upload/pdf", response_model=Session)
def upload_pdf(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """
    Upload a PDF file for fit-gap analysis.
    If session_id is not provided, creates a new session.
    """
    logger.info(f"Upload PDF called with session_id: {session_id}, title: {title}, filename: {file.filename}")
    
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Handle session_id - it might come as string "None" or empty string
    if session_id and session_id.lower() in ("none", "", "null"):
        session_id = None
    
    # Create session if not provided
    session_kind = SessionKind.PDF
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"Creating new session: {session_id}")
        bq_client.create_session(
            session_id=session_id,
            kind=session_kind.value,
            title=title or file.filename,
            source_ref=None  # Will be set after GCS upload
        )
    else:
        # Session was created separately, verify it exists and is PDF type
        logger.info(f"Using existing session: {session_id}")
        session = bq_client.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session["kind"] != "pdf":
            raise HTTPException(status_code=400, detail="Session is not a PDF session")
    
    # Save file temporarily
    # Use absolute path for upload directory
    upload_dir = os.path.abspath(settings.upload_dir)
    temp_path = os.path.join(upload_dir, f"{session_id}.pdf")
    
    # Ensure upload directory exists
    os.makedirs(upload_dir, exist_ok=True)
    
    logger.info(f"Saving PDF to: {temp_path}")
    with open(temp_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    logger.info(f"File saved successfully, size: {len(content)} bytes")
    
    session = bq_client.get_session(session_id)
    return Session(**session)


@app.post("/api/sessions/{session_id}/process-pdf")
def process_pdf(
    session_id: str,
    background_tasks: BackgroundTasks
):
    """
    Start PDF processing for a session.
    This is an async endpoint.
    """
    session = bq_client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["kind"] != "pdf":
        raise HTTPException(status_code=400, detail="Session is not a PDF session")
    
    # Mark as processing
    bq_client.update_session_status(session_id, "processing")
    
    # Start background task
    background_tasks.add_task(
        _process_pdf_background,
        session_id=session_id,
        bq_client=bq_client,
        pdf_pipeline=pdf_pipeline
    )
    
    return {"status": "processing", "session_id": session_id}


def _process_pdf_background(
    session_id: str,
    bq_client: BigQueryClient,
    pdf_pipeline: PDFPipeline
):
    """Background task for PDF processing."""
    try:
        # Get the session to find the file
        session = bq_client.get_session(session_id)
        if not session:
            return
        
        # For now, we need to know where the file is
        # In a real implementation, we'd have stored the temp path or GCS URI
        upload_dir = os.path.abspath(settings.upload_dir)
        temp_path = os.path.join(upload_dir, f"{session_id}.pdf")
        
        logger.info(f"Attempting to read PDF from: {temp_path}")
        logger.info(f"File exists: {os.path.exists(temp_path)}")
        
        # Process the PDF
        result = pdf_pipeline.process_pdf(
            file_path=temp_path,
            session_id=session_id,
            title=session["title"]
        )
        
        logger.info(f"PDF processing completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"PDF processing failed for {session_id}: {e}")
        bq_client.update_session_status(session_id, "failed")


@app.get("/api/sessions/{session_id}/status")
def get_session_status(session_id: str):
    """Get the processing status of a session."""
    session = bq_client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "status": session["status"],
        "kind": session["kind"]
    }


@app.get("/api/report/{session_id}", response_model=FitGapResult)
def get_report(session_id: str):
    """
    Get the fit-gap report for a session.
    Returns requirements, matches, decisions, and summary.
    """
    session = bq_client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["kind"] != "pdf":
        raise HTTPException(status_code=400, detail="Report available only for PDF sessions")
    
    if session["status"] == "failed":
        raise HTTPException(status_code=400, detail="Report generation failed. Please check logs for details.")
    
    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail="Report not ready yet")
    
    # Get all data
    requirements = bq_client.get_requirements(session_id)
    matches = bq_client.get_matches(session_id)
    decisions = bq_client.get_decisions(session_id)
    
    # Generate summary
    stats = _calculate_stats(requirements, matches)
    summary = _generate_summary(requirements, matches, decisions)
    
    return FitGapResult(
        session_id=session_id,
        requirements=requirements,
        matches=matches,
        decisions=decisions,
        summary=summary,
        stats=stats
    )


def _calculate_stats(requirements: List[Dict], matches: List[Dict]) -> Dict:
    """Calculate statistics from requirements and matches."""
    verdict_counts = {"fit": 0, "partial": 0, "gap": 0, "question": 0}
    
    for match in matches:
        verdict = match.get("verdict")
        if verdict in verdict_counts:
            verdict_counts[verdict] += 1
    
    total = len(requirements)
    
    return {
        "total_requirements": total,
        "verdict_counts": verdict_counts,
        "coverage_percentage": 100 * (verdict_counts["fit"] + verdict_counts["partial"]) / total if total > 0 else 0,
        "gap_percentage": 100 * verdict_counts["gap"] / total if total > 0 else 0
    }


def _generate_summary(requirements: List[Dict], matches: List[Dict], decisions: List[Dict]) -> str:
    """Generate a text summary."""
    verdict_counts = {"fit": 0, "partial": 0, "gap": 0, "question": 0}
    
    for match in matches:
        verdict = match.get("verdict")
        if verdict in verdict_counts:
            verdict_counts[verdict] += 1
    
    total = len(requirements)
    
    summary = f"""
Fit-Gap Analysis Summary
=======================

Total Requirements: {total}

Coverage:
- Fit: {verdict_counts['fit']} ({100 * verdict_counts['fit'] / total:.1f}%)
- Partial: {verdict_counts['partial']} ({100 * verdict_counts['partial'] / total:.1f}%)
- Gap: {verdict_counts['gap']} ({100 * verdict_counts['gap'] / total:.1f}%)
- Question: {verdict_counts['question']} ({100 * verdict_counts['question'] / total:.1f}%)

Open Decisions: {len(decisions)}
"""
    
    return summary


# =============================================================================
# Object Endpoints
# =============================================================================

@app.get("/api/object/{object_id}")
def get_object(object_id: str):
    """Get full information for an SAP object."""
    obj_info = bq_client.get_object_info(object_id)
    if not obj_info:
        raise HTTPException(status_code=404, detail="Object not found")
    
    return obj_info


@app.get("/api/object/{object_id}/graph")
def get_object_graph(object_id: str):
    """Get graph data (nodes and edges) for an object."""
    graph = bq_client.get_related_objects(object_id, depth=1)
    return graph


# =============================================================================
# Decision Endpoints
# =============================================================================

@app.get("/api/decisions/{session_id}")
def get_decisions(session_id: str):
    """Get all decisions for a session."""
    decisions = bq_client.get_decisions(session_id)
    return decisions


@app.patch("/api/decisions/{decision_id}")
def update_decision(
    decision_id: str,
    status: Optional[str] = None,
    answer: Optional[str] = None
):
    """Update a decision."""
    bq_client.update_decision(decision_id, status=status, answer=answer)
    return {"status": "updated", "decision_id": decision_id}


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
