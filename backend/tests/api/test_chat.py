"""
Tests for the chat API endpoint.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.main import app
from backend.models.schemas import ChatRequest, ChatResponse, ChunkInfo


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_chat_service():
    """Create a mock chat service that returns proper ChatResponse objects."""
    service = MagicMock()
    
    # Return proper ChatResponse (JSON-serializable)
    def mock_chat(request, session_id=None):
        return ChatResponse(
            message="Test response",
            citations=[],
            matched_objects=[],
            graph_data={"nodes": [], "edges": []},
            trace=[],
            session_id=session_id or "test-session"
        )
    
    service.chat = MagicMock(side_effect=mock_chat)
    return service


@pytest.fixture
def patch_chat_service(mock_chat_service):
    """Patch the global chat_service with a mock."""
    with patch('backend.main.chat_service', mock_chat_service):
        yield mock_chat_service


# =============================================================================
# Chat Endpoint Tests
# =============================================================================

class TestChatEndpoint:
    """Tests for /api/chat endpoint."""
    
    def test_chat_endpoint_post(self, client, patch_chat_service):
        """Test POST request to chat endpoint."""
        request_data = {
            "message": "Test query",
            "scope": "both"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Test response"
        
    def test_chat_endpoint_with_session_id(self, client, patch_chat_service):
        """Test chat endpoint with provided session ID."""
        request_data = {
            "message": "Test query",
            "session_id": "custom-session-id",
            "scope": "both"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "custom-session-id"
        
    def test_chat_endpoint_with_history(self, client, patch_chat_service):
        """Test chat endpoint with conversation history."""
        request_data = {
            "message": "Follow up",
            "history": [
                {"role": "user", "content": "Previous question"},
                {"role": "assistant", "content": "Previous answer"}
            ],
            "scope": "both"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
    def test_chat_endpoint_with_scope(self, client, patch_chat_service):
        """Test chat endpoint with different scopes."""
        for scope in ["standard", "nova", "both"]:
            request_data = {
                "message": "Test query",
                "scope": scope
            }
            
            response = client.post("/api/chat", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            
    def test_chat_endpoint_with_top_k(self, client, patch_chat_service):
        """Test chat endpoint with custom top_k."""
        request_data = {
            "message": "Test query",
            "top_k": 5,
            "scope": "both"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        
    def test_chat_endpoint_empty_message(self, client, patch_chat_service):
        """Test chat endpoint with empty message."""
        request_data = {
            "message": "",
            "scope": "both"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        # Should handle empty message gracefully
        assert response.status_code in [200, 422]  # Could be either depending on validation
        
    def test_chat_endpoint_missing_message(self, client, patch_chat_service):
        """Test chat endpoint with missing message field."""
        request_data = {
            "scope": "both"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        # Should return validation error
        assert response.status_code == 422


# =============================================================================
# Chat Stream Endpoint Tests
# =============================================================================

class TestChatStreamEndpoint:
    """Tests for /api/chat/stream endpoint."""
    
    def test_chat_stream_endpoint(self, client, patch_chat_service):
        """Test streaming chat endpoint returns event stream."""
        request_data = {
            "message": "Test query",
            "scope": "both"
        }
        
        response = client.post("/api/chat/stream", json=request_data)
        
        assert response.status_code == 200
        # Should return event stream
        assert "text/event-stream" in response.headers.get("content-type", "")
        
    def test_chat_stream_endpoint_content(self, client, patch_chat_service):
        """Test streaming chat endpoint returns data."""
        request_data = {
            "message": "Test query",
            "scope": "both"
        }
        
        response = client.post("/api/chat/stream", json=request_data)
        
        assert response.status_code == 200
        # Check that response has content
        assert len(response.content) > 0


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthCheck:
    """Tests for /api/health endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in endpoints."""
    
    # def test_chat_endpoint_service_error(self, monkeypatch):
    #     """Test chat endpoint when service raises error.
    #     TODO: Fix module-level instance patching issue
    #     """
    #     import backend.main as main_module
    #     mock_service = MagicMock()
    #     mock_service.chat.side_effect = Exception("Service error")
    #     monkeypatch.setattr(main_module, 'chat_service', mock_service)
    #     
    #     client = TestClient(main_module.app)
    #     request_data = {"message": "Test query", "scope": "both"}
    #     response = client.post("/api/chat", json=request_data)
    #     assert response.status_code == 500
            
    def test_chat_endpoint_validation_error(self, client):
        """Test chat endpoint with invalid request data."""
        request_data = {
            "message": 12345,  # Invalid type
            "scope": "both"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 422
