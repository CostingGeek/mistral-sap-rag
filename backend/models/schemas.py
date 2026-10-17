"""
Pydantic models for the SAP Fit-Gap RAG application.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class SessionKind(str, Enum):
    """Type of analysis session."""
    CHAT = "chat"
    PDF = "pdf"
    AUDIO = "audio"


class SessionStatus(str, Enum):
    """Status of a session."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Verdict(str, Enum):
    """Fit-gap verdict for a requirement."""
    FIT = "fit"
    PARTIAL = "partial"
    GAP = "gap"
    QUESTION = "question"


class DecisionStatus(str, Enum):
    """Status of a decision."""
    OPEN = "open"
    ANSWERED = "answered"
    RESOLVED = "resolved"


# =============================================================================
# Database Models
# =============================================================================

class Session(BaseModel):
    """A user session for analysis."""
    session_id: str = Field(..., description="Unique session identifier")
    kind: SessionKind = Field(..., description="Type of session")
    title: str = Field(..., description="Human-readable title")
    created_at: datetime = Field(..., description="Creation timestamp")
    status: SessionStatus = Field(..., description="Current status")
    source_ref: Optional[str] = Field(None, description="GCS URI of uploaded file")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Requirement(BaseModel):
    """A requirement extracted from a document or transcript."""
    req_id: str = Field(..., description="Unique requirement identifier")
    session_id: str = Field(..., description="Parent session ID")
    ref_in_doc: Optional[str] = Field(None, description="Reference in document (e.g., 'R-12' or page number)")
    text: str = Field(..., description="The requirement text")
    category: Optional[str] = Field(None, description="Category or type")
    page: Optional[int] = Field(None, description="Page number if from PDF")
    speaker: Optional[str] = Field(None, description="Speaker if from transcript")
    created_at: datetime = Field(..., description="Creation timestamp")


class Match(BaseModel):
    """A match between a requirement and an SAP object."""
    req_id: str = Field(..., description="Requirement ID")
    session_id: str = Field(..., description="Session ID")
    object_id: str = Field(..., description="SAP object ID")
    distance: float = Field(..., description="Similarity distance")
    verdict: Verdict = Field(..., description="Fit-gap verdict")
    rationale: str = Field(..., description="Explanation of the verdict")
    model: str = Field(..., description="Model used for verdict")
    matched_objects: List[str] = Field(default_factory=list, description="All matched object IDs")
    created_at: datetime = Field(..., description="Creation timestamp")


class Decision(BaseModel):
    """A decision that needs to be made in a workshop."""
    decision_id: str = Field(..., description="Unique decision identifier")
    session_id: str = Field(..., description="Parent session ID")
    req_id: Optional[str] = Field(None, description="Related requirement ID if any")
    question: str = Field(..., description="The question to decide")
    options: List[str] = Field(default_factory=list, description="Candidate answers")
    status: DecisionStatus = Field(default=DecisionStatus.OPEN, description="Current status")
    answer: Optional[str] = Field(None, description="Answer if status is ANSWERED")
    source: str = Field(..., description="Source: pdf|transcript|manual")
    created_at: datetime = Field(..., description="Creation timestamp")


# =============================================================================
# API Request/Response Models
# =============================================================================

class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = Field(..., description="Role: user or assistant")
    content: str = Field(..., description="Message content")
    citations: Optional[List[Dict[str, Any]]] = Field(None, description="Source citations")


class ChatRequest(BaseModel):
    """Request for chat completion."""
    session_id: Optional[str] = Field(None, description="Session ID for conversation history")
    message: str = Field(..., description="User message")
    history: Optional[List[ChatMessage]] = Field(None, description="Previous messages in conversation")
    top_k: Optional[int] = Field(None, description="Number of chunks to retrieve")


class ChunkInfo(BaseModel):
    """Information about a retrieved chunk."""
    chunk_id: str = Field(..., description="Chunk identifier")
    object_id: str = Field(..., description="SAP object ID")
    title: str = Field(..., description="Object title")
    section_type: str = Field(..., description="Section type")
    distance: float = Field(..., description="Similarity distance")
    content: str = Field(..., description="Chunk content")


class ObjectInfo(BaseModel):
    """Full information about an SAP object."""
    object_id: str = Field(..., description="Object ID")
    title: str = Field(..., description="Title")
    sections: Dict[str, str] = Field(default_factory=dict, description="All sections by type")
    element_refs: List[str] = Field(default_factory=list, description="Related objects")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    message: str = Field(..., description="Assistant response")
    citations: List[ChunkInfo] = Field(default_factory=list, description="Source chunks")
    matched_objects: List[str] = Field(default_factory=list, description="Matched object IDs")
    graph_data: Optional[Dict[str, Any]] = Field(None, description="Graph data for visualization")
    trace: Optional[List[Dict[str, Any]]] = Field(None, description="Agent trace for debugging")
    session_id: Optional[str] = Field(None, description="Session ID for conversation history")


class FitGapResult(BaseModel):
    """Complete fit-gap analysis result."""
    session_id: str = Field(..., description="Session ID")
    requirements: List[Requirement] = Field(default_factory=list, description="Extracted requirements")
    matches: List[Match] = Field(default_factory=list, description="Requirement matches")
    decisions: List[Decision] = Field(default_factory=list, description="Generated decisions")
    summary: str = Field(..., description="Executive summary")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Statistics")


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""
    kind: SessionKind = Field(..., description="Session type")
    title: Optional[str] = Field(None, description="Session title")


class UploadFileRequest(BaseModel):
    """Request for file upload."""
    session_id: str = Field(..., description="Session ID")
