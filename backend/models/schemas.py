"""
Pydantic models for the SAP Customizing RAG application.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
    scope: Optional[str] = Field("both", description="Corpus scope: standard (SAP), nova (company), or both")


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
