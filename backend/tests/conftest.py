"""
Pytest configuration and fixtures for backend tests.
Comprehensive mocking with proper data structures to prevent false positives.
"""
import json
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from pydantic import SecretStr

from backend.config import Settings, settings
from backend.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChunkInfo,
)


# =============================================================================
# Mock Configuration
# =============================================================================

@pytest.fixture
def mock_settings():
    """Mock settings for testing - no hardcoded GCP identifiers."""
    return Settings(
        app_host="127.0.0.1",
        app_port=8000,
        debug=False,
        gcp_project="test-project",
        bq_dataset="test_dataset",
        bucket_name="test-bucket",
        gcp_sa_key_base64=None,
        mistral_api_key=SecretStr("test-api-key"),
        mistral_base_url=None,
        embed_model="mistral-embed",
        chat_model="mistral-medium-latest",
        classify_model="mistral-small-latest",
        retrieval_k=8,
        standard_clean_table="doktl_clean",
        standard_embeddings_table="doktl_embeddings",
        nova_clean_table="doktl_nova_clean",
        nova_embeddings_table="doktl_nova_embeddings",
        mistral_rate_limit_delay=0.0
    )


@pytest.fixture(autouse=True)
def patch_global_settings(mock_settings):
    """Patch global settings for all tests."""
    import backend.config as config_module
    with patch.object(config_module, 'settings', mock_settings):
        yield


# =============================================================================
# Factory Functions for Test Data
# =============================================================================

def make_bq_row(
    chunk_id: str = "chunk-1",
    object_id: str = "SIMG/TEST/001",
    title: str = "Test Object",
    section_type: str = "USE",
    distance: float = 0.1,
    content: str = "Test content",
    corpus: str = "standard"
) -> Dict[str, Any]:
    """Factory for BigQuery row with all required fields."""
    return {
        "chunk_id": chunk_id,
        "object_id": object_id,
        "title": title,
        "section_type": section_type,
        "distance": distance,
        "content": content,
        "corpus": corpus,
        "content_clean": content,
        "embed": True,
    }


def make_chunk_info(
    chunk_id: str = "chunk-1",
    object_id: str = "SIMG/TEST/001",
    title: str = "Test Object",
    section_type: str = "USE",
    distance: float = 0.1,
    content: str = "Test content",
    corpus: Optional[str] = "standard",
    graph_expanded: bool = False,
    source_no: Optional[int] = None
) -> ChunkInfo:
    """Factory for ChunkInfo model instances."""
    return ChunkInfo(
        chunk_id=chunk_id,
        object_id=object_id,
        title=title,
        section_type=section_type,
        distance=distance,
        content=content,
        corpus=corpus,
        graph_expanded=graph_expanded,
        source_no=source_no
    )


def make_chat_response(
    message: str = "Test response",
    citations: Optional[List[ChunkInfo]] = None,
    matched_objects: Optional[List[str]] = None,
    graph_data: Optional[Dict[str, Any]] = None,
    trace: Optional[List[Dict[str, Any]]] = None,
    session_id: Optional[str] = None
) -> ChatResponse:
    """Factory for ChatResponse model instances (JSON-serializable)."""
    return ChatResponse(
        message=message,
        citations=citations or [],
        matched_objects=matched_objects or [],
        graph_data=graph_data or {"nodes": [], "edges": []},
        trace=trace or [],
        session_id=session_id
    )


def make_bq_ref_row(ref: str = "activity:SIMG/TEST/002") -> Dict[str, Any]:
    """Factory for BigQuery reference row."""
    return {"ref": ref}


def make_bq_object_row(
    object_id: str = "SIMG/TEST/001",
    title: str = "Test Object",
    section_type: str = "USE",
    content: str = "Test content",
    element_refs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Factory for BigQuery object info row."""
    return {
        "object_id": object_id,
        "title": title,
        "section_type": section_type,
        "content": content,
        "content_clean": content,
        "element_refs": element_refs or [],
        "corpus": "standard"
    }


# =============================================================================
# Mock BigQuery Client
# =============================================================================

@pytest.fixture
def mock_bigquery_client():
    """
    Create a thoroughly mocked BigQuery client with proper data structures.
    Returns data that matches actual BigQuery query results.
    """
    with patch('backend.integrations.bigquery_client.bigquery') as mock_module:
        # Create mock client
        mock_client = MagicMock()
        
        # Mock dataset operations
        mock_dataset = MagicMock()
        mock_dataset.location = "us-central1"
        mock_dataset_ref = MagicMock()
        
        def mock_get_dataset(dataset_ref):
            return mock_dataset
        
        def mock_create_dataset(dataset, timeout=None):
            return mock_dataset
        
        mock_client.get_dataset.side_effect = mock_get_dataset
        mock_client.create_dataset.side_effect = mock_create_dataset
        mock_client.dataset.return_value = mock_dataset_ref
        
        # Configure query to return proper data based on SQL pattern
        def mock_query(sql, job_config=None):
            mock_job = MagicMock()
            mock_result = MagicMock()
            
            # Return mock rows based on query type
            if "retrieve_similar_chunks" in sql or "ML.DISTANCE" in sql:
                # Similarity retrieval query
                rows = [
                    make_bq_row(
                        chunk_id="chunk-1",
                        object_id="SIMG/TEST/001",
                        title="Test Object 1",
                        section_type="USE",
                        distance=0.1,
                        content="Test content 1",
                        corpus="standard"
                    ),
                    make_bq_row(
                        chunk_id="chunk-2",
                        object_id="SIMG/TEST/002",
                        title="Test Object 2",
                        section_type="SHORTTEXT",
                        distance=0.2,
                        content="Test content 2",
                        corpus="nova"
                    )
                ]
                mock_result.__iter__ = lambda self: iter([
                    MagicMock(__getitem__=lambda _, k: row[k]) for row in rows
                ])
            
            elif "get_object_info" in sql or "object_id = @object_id" in sql:
                # Object info query
                rows = [
                    make_bq_object_row(
                        object_id="SIMG/TEST/001",
                        title="Test Object",
                        section_type="USE",
                        content="Use section content",
                        element_refs=["activity:SIMG/TEST/002"]
                    ),
                    make_bq_object_row(
                        object_id="SIMG/TEST/001",
                        title="Test Object",
                        section_type="SHORTTEXT",
                        content="Short text content",
                        element_refs=[]
                    )
                ]
                mock_result.__iter__ = lambda self: iter([
                    MagicMock(__getitem__=lambda _, k: row[k]) for row in rows
                ])
            
            elif "get_related_objects" in sql or "UNNEST(c.element_refs)" in sql:
                # Related objects query
                rows = [make_bq_ref_row("activity:SIMG/TEST/002")]
                mock_result.__iter__ = lambda self: iter([
                    MagicMock(__getitem__=lambda _, k: row[k]) for row in rows
                ])
            
            elif "IN UNNEST(@activity_refs)" in sql or "IN UNNEST(@ids)" in sql:
                # Batch object lookup
                rows = [
                    {
                        "object_id": "SIMG/TEST/001",
                        "title": "Test Object",
                        "corpus": "standard"
                    },
                    {
                        "object_id": "SIMG/TEST/002", 
                        "title": "Related Object",
                        "corpus": "standard"
                    }
                ]
                mock_result.__iter__ = lambda self: iter([
                    MagicMock(__getitem__=lambda _, k: row[k]) for row in rows
                ])
            
            else:
                # Default empty result
                rows = []
                mock_result.__iter__ = lambda self: iter([])
            
            mock_job.result.return_value = mock_result
            return mock_job
        
        mock_client.query.side_effect = mock_query
        
        mock_module.Client.return_value = mock_client
        
        # Create BigQueryClient with mocked module
        from backend.integrations.bigquery_client import BigQueryClient
        client = BigQueryClient()
        yield client


@pytest.fixture
def mock_bigquery_client_simple():
    """Simplified mock BigQuery client for tests that don't need complex behavior."""
    client = MagicMock()
    client.VALID_SCOPES = ("standard", "nova", "both")
    
    # Retrieve similar chunks - return proper structure
    client.retrieve_similar_chunks = MagicMock(return_value=[
        make_bq_row(
            chunk_id="chunk-1",
            object_id="SIMG/TEST/001",
            title="Test Object",
            section_type="USE",
            distance=0.1,
            content="Test content",
            corpus="standard"
        )
    ])
    
    # Get object info - return proper structure
    client.get_object_info = MagicMock(return_value={
        "object_id": "SIMG/TEST/001",
        "title": "Test Object",
        "sections": {
            "USE": "Use section content",
            "SHORTTEXT": "Short text content"
        },
        "element_refs": ["activity:SIMG/TEST/002"]
    })
    
    # Get related objects
    client.get_related_objects = MagicMock(return_value={
        "nodes": [
            {"id": "SIMG/TEST/001", "title": "Test Object"},
            {"id": "SIMG/TEST/002", "title": "Related Object"}
        ],
        "edges": [
            {"source": "SIMG/TEST/001", "target": "SIMG/TEST/002", "type": "activity"}
        ]
    })
    
    # Batch operations
    client.get_related_objects_batch = MagicMock(return_value={
        "SIMG/TEST/001": {
            "nodes": [
                {"id": "SIMG/TEST/001", "title": "Test Object"},
                {"id": "SIMG/TEST/002", "title": "Related Object"}
            ],
            "edges": [
                {"source": "SIMG/TEST/001", "target": "SIMG/TEST/002", "type": "activity"}
            ]
        }
    })
    
    client.get_object_infos_batch = MagicMock(return_value={
        "SIMG/TEST/001": {
            "object_id": "SIMG/TEST/001",
            "title": "Test Object",
            "corpus": "standard",
            "sections": {
                "USE": "Use section",
                "SHORTTEXT": "Short text"
            }
        }
    })
    
    return client


# =============================================================================
# Mock Mistral Client
# =============================================================================

@pytest.fixture
def mock_mistral_client():
    """
    Create a thoroughly mocked Mistral client with proper data structures.
    Returns JSON-serializable data.
    """
    client = MagicMock()
    client.api_key = "test-api-key"
    
    # Embedding - return proper vector
    client.create_embedding = MagicMock(return_value=[0.1] * 1024)
    
    # Chat completion - return proper structure
    def mock_chat_completion(messages, **kwargs):
        return {
            "choices": [{
                "message": {
                    "content": "Test answer with [Source 1] citation."
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
    
    client.chat_completion = MagicMock(side_effect=mock_chat_completion)
    
    # JSON extraction - return proper dict
    def mock_extract_json(prompt, **kwargs):
        return {
            "type": "simple",
            "query": "test query"
        }
    
    client.extract_json_response = MagicMock(side_effect=mock_extract_json)
    
    # Token usage - return proper dict
    def mock_pop_usage():
        return {
            "prompt": 100,
            "completion": 50,
            "total": 150
        }
    
    client.pop_last_usage = MagicMock(side_effect=mock_pop_usage)
    
    return client


@pytest.fixture
def mock_mistral_client_error():
    """Mock Mistral client that raises errors for testing error handling."""
    from fastapi import HTTPException
    client = MagicMock()
    client.api_key = "test-api-key"
    
    # Make requests raise exceptions
    def mock_request(method, endpoint, **kwargs):
        raise Exception("Network error")
    
    client._request = MagicMock(side_effect=mock_request)
    client.create_embedding = MagicMock(side_effect=Exception("Embedding error"))
    client.chat_completion = MagicMock(side_effect=Exception("Chat error"))
    client.pop_last_usage = MagicMock(return_value=None)
    
    return client


# =============================================================================
# Mock Services
# =============================================================================

@pytest.fixture
def mock_chat_service():
    """Mock chat service that returns proper ChatResponse objects."""
    service = MagicMock()
    
    def mock_chat(request, session_id=None):
        return make_chat_response(
            message="Test response",
            citations=[make_chunk_info()],
            matched_objects=["SIMG/TEST/001"],
            graph_data={"nodes": [], "edges": []},
            trace=[],
            session_id=session_id or "test-session"
        )
    
    service.chat = MagicMock(side_effect=mock_chat)
    return service


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing."""
    return ChatRequest(
        message="What do I need to configure for dangerous goods?",
        scope="both",
        top_k=8
    )


@pytest.fixture
def sample_chunk_info():
    """Sample chunk info for testing."""
    return make_chunk_info()


@pytest.fixture
def sample_chunks():
    """Sample list of chunks for testing."""
    return [
        make_chunk_info(
            chunk_id="chunk-1",
            object_id="SIMG/TEST/001",
            title="Test Object 1",
            section_type="USE",
            distance=0.1,
            content="Test content 1",
            corpus="standard"
        ),
        make_chunk_info(
            chunk_id="chunk-2",
            object_id="SIMG/TEST/002",
            title="Test Object 2",
            section_type="SHORTTEXT",
            distance=0.2,
            content="Test content 2",
            corpus="nova"
        )
    ]


@pytest.fixture
def sample_chat_response():
    """Sample chat response for testing."""
    return make_chat_response(
        message="Test answer with [Source 1] citation.",
        citations=[make_chunk_info(source_no=1)],
        matched_objects=["SIMG/TEST/001"],
        graph_data={
            "nodes": [{"id": "SIMG/TEST/001", "title": "Test Object"}],
            "edges": []
        },
        trace=[
            {"step": "intent_classification", "result": {"type": "simple", "query": "test"}, "duration_ms": 100},
            {"step": "retrieval", "query": "test", "chunk_count": 1, "duration_ms": 200},
            {"step": "synthesis", "answer_length": 20, "duration_ms": 300}
        ]
    )


# =============================================================================
# Expected Test Results
# =============================================================================

@pytest.fixture
def expected_intent_simple():
    """Expected intent classification for simple query."""
    return {
        "type": "simple",
        "query": "test query"
    }


@pytest.fixture
def expected_intent_multi():
    """Expected intent classification for multi-intent query."""
    return {
        "type": "multi_intent",
        "sub_queries": [
            "sub query 1",
            "sub query 2"
        ]
    }


# =============================================================================
# Test Helpers
# =============================================================================

def create_test_embedding(size=1024):
    """Helper to create test embedding vector."""
    return [0.1] * size


def create_test_bq_result(rows):
    """Helper to create mock BigQuery result."""
    result = MagicMock()
    result.__iter__ = lambda self: iter([
        MagicMock(__getitem__=lambda _, k: row[k]) for row in rows
    ])
    return result
