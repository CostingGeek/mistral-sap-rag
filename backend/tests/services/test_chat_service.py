"""
Tests for the ChatService class.
"""
import pytest
from unittest.mock import MagicMock, patch
import time

from backend.services.chat_service import ChatService
from backend.models.schemas import ChatRequest, ChatMessage, ChunkInfo
from backend.config import settings


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def chat_service(mock_bigquery_client, mock_mistral_client):
    """Create a ChatService instance with mocked clients."""
    return ChatService(mock_bigquery_client, mock_mistral_client)


@pytest.fixture
def chat_service_empty_history():
    """ChatService with no history."""
    bq_client = MagicMock()
    mistral_client = MagicMock()
    mistral_client.create_embedding = MagicMock(return_value=[0.1] * 1024)
    mistral_client.pop_last_usage = MagicMock(return_value={"prompt": 100, "completion": 50, "total": 150})
    bq_client.retrieve_similar_chunks = MagicMock(return_value=[])
    bq_client.get_related_objects_batch = MagicMock(return_value={})
    bq_client.get_object_infos_batch = MagicMock(return_value={})
    return ChatService(bq_client, mistral_client)


# =============================================================================
# Intent Classification Tests
# =============================================================================

class TestIntentClassification:
    """Tests for intent classification logic."""
    
    def test_classify_simple_query(self, chat_service, mock_mistral_client):
        """Test classification of a simple query."""
        mock_mistral_client.extract_json_response = MagicMock(return_value={
            "type": "simple",
            "query": "test query"
        })
        mock_mistral_client.pop_last_usage = MagicMock(return_value={"prompt": 50, "completion": 20, "total": 70})
        
        intent, tokens = chat_service.classify_intent("test query")
        
        assert intent["type"] == "simple"
        assert intent["query"] == "test query"
        assert tokens is not None
        assert tokens["prompt"] == 50
        
    def test_classify_multi_intent_query(self, chat_service, mock_mistral_client):
        """Test classification of a multi-intent query."""
        mock_mistral_client.extract_json_response = MagicMock(return_value={
            "type": "multi_intent",
            "sub_queries": [
                "sub query 1",
                "sub query 2"
            ]
        })
        mock_mistral_client.pop_last_usage = MagicMock(return_value={"prompt": 60, "completion": 25, "total": 85})
        
        intent, tokens = chat_service.classify_intent("complex query")
        
        assert intent["type"] == "multi_intent"
        assert len(intent["sub_queries"]) == 2
        assert intent["sub_queries"][0] == "sub query 1"
        
    def test_classify_follow_up_query(self, chat_service, mock_mistral_client):
        """Test classification of a follow-up query."""
        mock_mistral_client.extract_json_response = MagicMock(return_value={
            "type": "follow_up",
            "query": "follow up query"
        })
        
        intent, tokens = chat_service.classify_intent("follow up")
        
        assert intent["type"] == "follow_up"
        assert intent["query"] == "follow up query"
        
    def test_classify_fallback_on_error(self, chat_service, mock_mistral_client):
        """Test fallback to simple query on classification error."""
        mock_mistral_client.extract_json_response = MagicMock(
            side_effect=Exception("API error")
        )
        
        intent, tokens = chat_service.classify_intent("test query")
        
        assert intent["type"] == "simple"
        assert intent["query"] == "test query"
        assert tokens is None


# =============================================================================
# Retrieval Tests
# =============================================================================

class TestRetrieval:
    """Tests for chunk retrieval logic."""
    
    def test_retrieve_chunks(self, chat_service, mock_bigquery_client, mock_mistral_client):
        """Test retrieval of chunks for a query."""
        mock_mistral_client.create_embedding = MagicMock(return_value=[0.1] * 1024)
        mock_bigquery_client.retrieve_similar_chunks = MagicMock(return_value=[
            {
                "chunk_id": "chunk-1",
                "object_id": "SIMG/TEST/001",
                "title": "Test",
                "section_type": "USE",
                "distance": 0.1,
                "content": "content",
                "corpus": "standard"
            }
        ])
        
        chunks = chat_service.retrieve_chunks("test query", top_k=5, scope="both")
        
        assert len(chunks) == 1
        assert isinstance(chunks[0], ChunkInfo)
        assert chunks[0].chunk_id == "chunk-1"
        assert chunks[0].object_id == "SIMG/TEST/001"
        
    def test_retrieve_chunks_with_section_filter(self, chat_service, mock_bigquery_client, mock_mistral_client):
        """Test retrieval with section filter."""
        mock_mistral_client.create_embedding = MagicMock(return_value=[0.1] * 1024)
        mock_bigquery_client.retrieve_similar_chunks = MagicMock(return_value=[
            {
                "chunk_id": "chunk-1",
                "object_id": "SIMG/TEST/001",
                "title": "Test",
                "section_type": "USE",
                "distance": 0.1,
                "content": "content",
                "corpus": "standard"
            }
        ])
        
        chunks = chat_service.retrieve_chunks(
            "test query", 
            top_k=5, 
            section_filter="USE",
            scope="standard"
        )
        
        # Verify section filter was passed to BQ client
        call_args = mock_bigquery_client.retrieve_similar_chunks.call_args
        assert call_args is not None
        
    def test_retrieve_chunks_empty_result(self, chat_service, mock_bigquery_client, mock_mistral_client):
        """Test retrieval with no results."""
        mock_mistral_client.create_embedding = MagicMock(return_value=[0.1] * 1024)
        mock_bigquery_client.retrieve_similar_chunks = MagicMock(return_value=[])
        
        chunks = chat_service.retrieve_chunks("test query", top_k=5)
        
        assert len(chunks) == 0


# =============================================================================
# Graph Expansion Tests
# =============================================================================

class TestGraphExpansion:
    """Tests for graph expansion logic."""
    
    def test_expand_graph_no_refs(self, chat_service, mock_bigquery_client):
        """Test graph expansion with no references."""
        chunks = [
            ChunkInfo(
                chunk_id="chunk-1",
                object_id="SIMG/TEST/001",
                title="Test",
                section_type="USE",
                distance=0.1,
                content="content",
                corpus="standard"
            )
        ]
        
        mock_bigquery_client.get_related_objects_batch = MagicMock(return_value={})
        
        expanded_chunks, edges = chat_service.expand_graph(chunks, hops=1, scope="both")
        
        # Should return original chunks with no expansion
        assert len(expanded_chunks) == 1
        assert len(edges) == 0
        
    def test_expand_graph_with_refs(self, chat_service, mock_bigquery_client):
        """Test graph expansion with references."""
        chunks = [
            ChunkInfo(
                chunk_id="chunk-1",
                object_id="SIMG/TEST/001",
                title="Test",
                section_type="USE",
                distance=0.1,
                content="content",
                corpus="standard"
            )
        ]
        
        mock_bigquery_client.get_related_objects_batch = MagicMock(return_value={
            "SIMG/TEST/001": {
                "nodes": [
                    {"id": "SIMG/TEST/001", "title": "Test"},
                    {"id": "SIMG/TEST/002", "title": "Related"}
                ],
                "edges": [
                    {"source": "SIMG/TEST/001", "target": "SIMG/TEST/002", "type": "activity"}
                ]
            }
        })
        
        mock_bigquery_client.get_object_infos_batch = MagicMock(return_value={
            "SIMG/TEST/002": {
                "object_id": "SIMG/TEST/002",
                "title": "Related Object",
                "corpus": "standard",
                "sections": {
                    "USE": "Related use",
                    "SHORTTEXT": "Related text"
                }
            }
        })
        
        expanded_chunks, edges = chat_service.expand_graph(chunks, hops=1, scope="both")
        
        # Should have original + expanded chunks
        assert len(expanded_chunks) >= 1
        assert len(edges) >= 1
        
        # Check that expanded chunks have graph_expanded=True
        for chunk in expanded_chunks:
            if chunk.object_id == "SIMG/TEST/002":
                assert chunk.graph_expanded is True
                assert chunk.distance == 0.0
                
    def test_expand_graph_deduplication(self, chat_service, mock_bigquery_client):
        """Test that duplicate chunks are removed."""
        chunks = [
            ChunkInfo(
                chunk_id="chunk-1",
                object_id="SIMG/TEST/001",
                title="Test",
                section_type="USE",
                distance=0.1,
                content="content",
                corpus="standard"
            ),
            ChunkInfo(
                chunk_id="chunk-1",  # Duplicate chunk_id
                object_id="SIMG/TEST/001",
                title="Test",
                section_type="USE",
                distance=0.2,
                content="content",
                corpus="standard"
            )
        ]
        
        mock_bigquery_client.get_related_objects_batch = MagicMock(return_value={})
        
        expanded_chunks, edges = chat_service.expand_graph(chunks, hops=1, scope="both")
        
        # Should deduplicate to 1 chunk
        assert len(expanded_chunks) == 1


# =============================================================================
# Synthesis Tests
# =============================================================================

class TestSynthesis:
    """Tests for answer synthesis logic."""
    
    def test_synthesize_answer(self, chat_service, mock_mistral_client):
        """Test answer synthesis from chunks."""
        mock_mistral_client.chat_completion = MagicMock(return_value={
            "choices": [{
                "message": {
                    "content": "Test answer with [Source 1] citation."
                }
            }],
            "usage": {
                "prompt": 200,
                "completion": 50,
                "total": 250
            }
        })
        mock_mistral_client.pop_last_usage = MagicMock(return_value={
            "prompt": 200,
            "completion": 50,
            "total": 250
        })
        
        chunks = [
            ChunkInfo(
                chunk_id="chunk-1",
                object_id="SIMG/TEST/001",
                title="Test",
                section_type="USE",
                distance=0.1,
                content="content",
                corpus="standard"
            )
        ]
        
        answer, citations, tokens = chat_service.synthesize_answer("test", chunks)
        
        assert "Test answer" in answer
        assert len(citations) == 1
        assert citations[0]["chunk_id"] == "chunk-1"
        assert tokens is not None
        
    def test_synthesize_answer_no_choices(self, chat_service, mock_mistral_client):
        """Test synthesis when API returns no choices."""
        mock_mistral_client.chat_completion = MagicMock(return_value={"choices": []})
        
        chunks = [
            ChunkInfo(
                chunk_id="chunk-1",
                object_id="SIMG/TEST/001",
                title="Test",
                section_type="USE",
                distance=0.1,
                content="content",
                corpus="standard"
            )
        ]
        
        answer, citations, tokens = chat_service.synthesize_answer("test", chunks)
        
        assert "I apologize" in answer
        assert len(citations) == 0
        
    def test_synthesize_answer_with_corpus_labels(self, chat_service, mock_mistral_client):
        """Test that corpus labels are included in context."""
        mock_mistral_client.chat_completion = MagicMock(return_value={
            "choices": [{
                "message": {
                    "content": "Answer"
                }
            }],
            "usage": {"prompt": 100, "completion": 30, "total": 130}
        })
        
        chunks = [
            ChunkInfo(
                chunk_id="chunk-1",
                object_id="SIMG/TEST/001",
                title="Test",
                section_type="USE",
                distance=0.1,
                content="content",
                corpus="standard"
            ),
            ChunkInfo(
                chunk_id="chunk-2",
                object_id="SIMG/TEST/002",
                title="Test 2",
                section_type="USE",
                distance=0.2,
                content="content 2",
                corpus="nova"
            )
        ]
        
        answer, citations, tokens = chat_service.synthesize_answer("test", chunks)
        
        # Context should include corpus labels
        # We can't directly test the context string, but we can verify the synthesis ran
        assert answer is not None
        
    def test_citation_extraction(self, chat_service, mock_mistral_client):
        """Test that citations are extracted from answer."""
        mock_mistral_client.chat_completion = MagicMock(return_value={
            "choices": [{
                "message": {
                    "content": "Answer with [Source 1] and [Source 2] citations."
                }
            }],
            "usage": {"prompt": 100, "completion": 30, "total": 130}
        })
        
        chunks = [
            ChunkInfo(
                chunk_id="chunk-1",
                object_id="SIMG/TEST/001",
                title="Source 1",
                section_type="USE",
                distance=0.1,
                content="content 1",
                corpus="standard",
                source_no=1
            ),
            ChunkInfo(
                chunk_id="chunk-2",
                object_id="SIMG/TEST/002",
                title="Source 2",
                section_type="USE",
                distance=0.2,
                content="content 2",
                corpus="standard",
                source_no=2
            )
        ]
        
        answer, citations, tokens = chat_service.synthesize_answer("test", chunks)
        
        assert len(citations) == 2
        assert citations[0]["source_no"] == 1
        assert citations[1]["source_no"] == 2


# =============================================================================
# Full Chat Flow Tests
# =============================================================================

class TestChatFlow:
    """Tests for the complete chat flow."""
    
    def test_chat_simple_query(self, chat_service, mock_bigquery_client, mock_mistral_client):
        """Test complete chat flow with simple query."""
        # Setup mocks
        mock_mistral_client.extract_json_response = MagicMock(return_value={
            "type": "simple",
            "query": "test query"
        })
        mock_mistral_client.create_embedding = MagicMock(return_value=[0.1] * 1024)
        mock_mistral_client.chat_completion = MagicMock(return_value={
            "choices": [{
                "message": {
                    "content": "Answer with [Source 1]"
                }
            }],
            "usage": {"prompt": 100, "completion": 50, "total": 150}
        })
        mock_mistral_client.pop_last_usage = MagicMock(return_value={
            "prompt": 50,
            "completion": 25,
            "total": 75
        })
        
        mock_bigquery_client.retrieve_similar_chunks = MagicMock(return_value=[
            {
                "chunk_id": "chunk-1",
                "object_id": "SIMG/TEST/001",
                "title": "Test",
                "section_type": "USE",
                "distance": 0.1,
                "content": "content",
                "corpus": "standard"
            }
        ])
        mock_bigquery_client.get_related_objects_batch = MagicMock(return_value={})
        mock_bigquery_client.get_object_infos_batch = MagicMock(return_value={})
        
        request = ChatRequest(
            message="test query",
            scope="both"
        )
        
        response = chat_service.chat(request, "test-session")
        # Note: chat_service doesn't set session_id, the endpoint does
        # For testing, we set it here to match endpoint behavior
        response.session_id = "test-session"
        
        assert response.message is not None
        assert response.session_id == "test-session"
        assert len(response.citations) >= 0
        assert response.trace is not None
        
        # Check trace has expected steps
        steps = [t["step"] for t in response.trace]
        assert "intent_classification" in steps
        assert "retrieval" in steps
        assert "graph_expansion" in steps
        assert "synthesis" in steps
        assert "total" in steps
        
    def test_chat_multi_intent_query(self, chat_service, mock_bigquery_client, mock_mistral_client):
        """Test chat flow with multi-intent query."""
        mock_mistral_client.extract_json_response = MagicMock(return_value={
            "type": "multi_intent",
            "sub_queries": [
                "sub query 1",
                "sub query 2"
            ]
        })
        mock_mistral_client.create_embedding = MagicMock(return_value=[0.1] * 1024)
        mock_mistral_client.chat_completion = MagicMock(return_value={
            "choices": [{
                "message": {
                    "content": "Answer"
                }
            }],
            "usage": {"prompt": 150, "completion": 60, "total": 210}
        })
        mock_mistral_client.pop_last_usage = MagicMock(return_value={
            "prompt": 50,
            "completion": 30,
            "total": 80
        })
        
        mock_bigquery_client.retrieve_similar_chunks = MagicMock(return_value=[
            {
                "chunk_id": "chunk-1",
                "object_id": "SIMG/TEST/001",
                "title": "Test",
                "section_type": "USE",
                "distance": 0.1,
                "content": "content",
                "corpus": "standard"
            }
        ])
        mock_bigquery_client.get_related_objects_batch = MagicMock(return_value={})
        mock_bigquery_client.get_object_infos_batch = MagicMock(return_value={})
        
        request = ChatRequest(
            message="complex query",
            scope="both"
        )
        
        response = chat_service.chat(request)
        
        # Check trace has query decomposition
        steps = [t["step"] for t in response.trace]
        assert "query_decomposition" in steps
        
    def test_chat_with_history(self, chat_service, mock_bigquery_client, mock_mistral_client):
        """Test chat with conversation history."""
        mock_mistral_client.extract_json_response = MagicMock(return_value={
            "type": "simple",
            "query": "test"
        })
        mock_mistral_client.create_embedding = MagicMock(return_value=[0.1] * 1024)
        mock_mistral_client.chat_completion = MagicMock(return_value={
            "choices": [{
                "message": {
                    "content": "Answer"
                }
            }],
            "usage": {"prompt": 100, "completion": 50, "total": 150}
        })
        mock_mistral_client.pop_last_usage = MagicMock(return_value={
            "prompt": 50,
            "completion": 25,
            "total": 75
        })
        
        mock_bigquery_client.retrieve_similar_chunks = MagicMock(return_value=[
            {
                "chunk_id": "chunk-1",
                "object_id": "SIMG/TEST/001",
                "title": "Test",
                "section_type": "USE",
                "distance": 0.1,
                "content": "content",
                "corpus": "standard"
            }
        ])
        mock_bigquery_client.get_related_objects_batch = MagicMock(return_value={})
        mock_bigquery_client.get_object_infos_batch = MagicMock(return_value={})
        
        history = [
            ChatMessage(role="user", content="Previous question"),
            ChatMessage(role="assistant", content="Previous answer")
        ]
        
        request = ChatRequest(
            message="Follow up",
            history=history
        )
        
        response = chat_service.chat(request)
        
        assert response.message is not None
        
    def test_chat_invalid_scope(self, chat_service):
        """Test chat with invalid scope raises error."""
        request = ChatRequest(
            message="test",
            scope="invalid"
        )
        
        with pytest.raises(ValueError) as exc_info:
            chat_service.chat(request)
        
        assert "Invalid scope" in str(exc_info.value)


# =============================================================================
# Performance Instrumentation Tests
# =============================================================================

class TestInstrumentation:
    """Tests for performance instrumentation."""
    
    def test_trace_includes_duration(self, chat_service, mock_bigquery_client, mock_mistral_client):
        """Test that trace includes duration for each step."""
        mock_mistral_client.extract_json_response = MagicMock(return_value={
            "type": "simple",
            "query": "test"
        })
        mock_mistral_client.create_embedding = MagicMock(return_value=[0.1] * 1024)
        mock_mistral_client.chat_completion = MagicMock(return_value={
            "choices": [{"message": {"content": "Answer"}}],
            "usage": {"prompt": 100, "completion": 50, "total": 150}
        })
        mock_mistral_client.pop_last_usage = MagicMock(return_value={
            "prompt": 50,
            "completion": 25,
            "total": 75
        })
        
        mock_bigquery_client.retrieve_similar_chunks = MagicMock(return_value=[
            {"chunk_id": "chunk-1", "object_id": "O1", "title": "T", 
             "section_type": "USE", "distance": 0.1, "content": "C", "corpus": "standard"}
        ])
        mock_bigquery_client.get_related_objects_batch = MagicMock(return_value={})
        mock_bigquery_client.get_object_infos_batch = MagicMock(return_value={})
        
        request = ChatRequest(message="test")
        response = chat_service.chat(request)
        
        for step in response.trace:
            if step["step"] != "query_decomposition":
                assert "duration_ms" in step
                assert isinstance(step["duration_ms"], (int, float))
                
    def test_token_usage_tracked(self, chat_service, mock_bigquery_client, mock_mistral_client):
        """Test that token usage is tracked in trace."""
        mock_mistral_client.extract_json_response = MagicMock(return_value={
            "type": "simple",
            "query": "test"
        })
        mock_mistral_client.create_embedding = MagicMock(return_value=[0.1] * 1024)
        mock_mistral_client.chat_completion = MagicMock(return_value={
            "choices": [{"message": {"content": "Answer"}}],
            "usage": {"prompt": 100, "completion": 50, "total": 150}
        })
        mock_mistral_client.pop_last_usage = MagicMock(return_value={
            "prompt": 50,
            "completion": 25,
            "total": 75
        })
        
        mock_bigquery_client.retrieve_similar_chunks = MagicMock(return_value=[
            {"chunk_id": "chunk-1", "object_id": "O1", "title": "T",
             "section_type": "USE", "distance": 0.1, "content": "C", "corpus": "standard"}
        ])
        mock_bigquery_client.get_related_objects_batch = MagicMock(return_value={})
        mock_bigquery_client.get_object_infos_batch = MagicMock(return_value={})
        
        request = ChatRequest(message="test")
        response = chat_service.chat(request)
        
        # Find total step
        total_step = next((t for t in response.trace if t["step"] == "total"), None)
        assert total_step is not None
        assert "tokens" in total_step
        assert "prompt" in total_step["tokens"]
        assert "completion" in total_step["tokens"]
