"""
Tests for the object API endpoints.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_bq_client():
    """Create a mock BigQuery client with proper data structures."""
    client = MagicMock()
    client.VALID_SCOPES = ("standard", "nova", "both")
    
    # Mock get_object_info to return proper structure
    def mock_get_object_info(object_id, scope="both"):
        if object_id == "NONEXISTENT":
            return None
        return {
            "object_id": object_id,
            "title": "Test Object",
            "sections": {"USE": "Use section"},
            "element_refs": []
        }
    
    client.get_object_info = MagicMock(side_effect=mock_get_object_info)
    
    # Mock get_related_objects to return proper structure
    def mock_get_related_objects(object_id, depth=1, scope="both"):
        # Return empty graph for NONEXISTENT
        if object_id == "NONEXISTENT":
            return {"nodes": [], "edges": []}
        return {
            "nodes": [
                {"id": object_id, "title": "Test Object"},
                {"id": "SIMG/TEST/002", "title": "Related Object"}
            ],
            "edges": [
                {"source": object_id, "target": "SIMG/TEST/002", "type": "activity"}
            ]
        }
    
    client.get_related_objects = MagicMock(side_effect=mock_get_related_objects)
    
    return client


@pytest.fixture
def patch_bq_client(mock_bq_client):
    """Patch the global bq_client with a mock."""
    with patch('backend.main.bq_client', mock_bq_client):
        yield mock_bq_client


# =============================================================================
# Object Endpoint Tests
# =============================================================================

class TestObjectEndpoint:
    """Tests for /api/object/{object_id} endpoint."""
    
    def test_get_object(self, client, patch_bq_client):
        """Test GET request for object information."""
        response = client.get("/api/object/SIMG/TEST/001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["object_id"] == "SIMG/TEST/001"
        assert data["title"] == "Test Object"
        
    def test_get_object_with_scope(self, client, patch_bq_client):
        """Test GET request with scope parameter."""
        response = client.get("/api/object/SIMG/TEST/001?scope=standard")
        
        assert response.status_code == 200
        
    def test_get_object_nova_scope(self, client, patch_bq_client):
        """Test GET request with nova scope."""
        response = client.get("/api/object/SIMG/TEST/001?scope=nova")
        
        assert response.status_code == 200
        
    def test_get_object_both_scope(self, client, patch_bq_client):
        """Test GET request with both scope."""
        response = client.get("/api/object/SIMG/TEST/001?scope=both")
        
        assert response.status_code == 200
        
    def test_get_object_with_slashes(self, client, patch_bq_client):
        """Test GET request with object ID containing slashes."""
        response = client.get("/api/object/SIMG/SEHS/DG_020")
        
        assert response.status_code == 200
        
    def test_get_object_not_found(self, client, patch_bq_client):
        """Test GET request for non-existent object."""
        patch_bq_client.get_object_info.return_value = None
        
        response = client.get("/api/object/NONEXISTENT")
        
        assert response.status_code == 404
        
    def test_get_object_graph(self, client, patch_bq_client):
        """Test GET request for object graph."""
        response = client.get("/api/object/SIMG/TEST/001/graph")
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        
    def test_get_object_graph_with_scope(self, client, patch_bq_client):
        """Test GET request for graph with scope parameter."""
        response = client.get("/api/object/SIMG/TEST/001/graph?scope=standard")
        
        assert response.status_code == 200
        
    def test_get_object_graph_not_found(self, client, patch_bq_client):
        """Test GET request for graph of non-existent object."""
        # Need to patch the method on the fixture to return empty graph
        patch_bq_client.get_related_objects.return_value = {"nodes": [], "edges": []}
        
        response = client.get("/api/object/NONEXISTENT/graph")
        
        assert response.status_code == 200
        data = response.json()
        assert data["nodes"] == []
        assert data["edges"] == []


# =============================================================================
# Graph Endpoint Tests
# =============================================================================

class TestGraphEndpoint:
    """Tests for /api/object/{object_id}/graph endpoint."""
    
    def test_graph_endpoint_simple_id(self, client, patch_bq_client):
        """Test graph endpoint with simple object ID."""
        response = client.get("/api/object/SIMPLE_ID/graph")
        
        assert response.status_code == 200
        
    def test_graph_endpoint_complex_id(self, client, patch_bq_client):
        """Test graph endpoint with complex object ID containing slashes."""
        response = client.get("/api/object/SIMG/SEHS/DG_020/graph")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        
    def test_graph_endpoint_all_scopes(self, client, patch_bq_client):
        """Test graph endpoint with all scope variations."""
        for scope in ["standard", "nova", "both"]:
            response = client.get(f"/api/object/SIMG/TEST/001/graph?scope={scope}")
            assert response.status_code == 200


# =============================================================================
# URL Encoding Tests
# =============================================================================

class TestUrlEncoding:
    """Tests for proper URL encoding of object IDs."""
    
    def test_object_id_with_special_chars(self, client, patch_bq_client):
        """Test object ID with special characters that need encoding."""
        # Simulate an object ID that would need URL encoding
        # Note: FastAPI's :path converter handles this automatically
        response = client.get("/api/object/SIMG/TEST%2F001")
        
        # The actual object_id parameter will be URL-decoded by FastAPI
        assert response.status_code == 200
        
    def test_object_id_url_encoded(self, client, patch_bq_client):
        """Test pre-URL-encoded object ID."""
        # Use raw URL with encoded slashes
        response = client.get("/api/object/SIMG%2FSEHS%2FDG_020")
        
        assert response.status_code == 200


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestObjectErrorHandling:
    """Tests for error handling in object endpoints."""
    
    # def test_object_endpoint_service_error(self, monkeypatch):
    #     """Test object endpoint when BQ client raises error.
    #     TODO: Fix module-level instance patching issue
    #     """
    #     import backend.main as main_module
    #     mock_bq = MagicMock()
    #     mock_bq.get_object_info.side_effect = Exception("BQ error")
    #     monkeypatch.setattr(main_module, 'bq_client', mock_bq)
    #     client = TestClient(main_module.app)
    #     response = client.get("/api/object/SIMG/TEST/001")
    #     assert response.status_code == 500
    # 
    # def test_graph_endpoint_service_error(self, monkeypatch):
    #     """Test graph endpoint when BQ client raises error.
    #     TODO: Fix module-level instance patching issue
    #     """
    #     import backend.main as main_module
    #     mock_bq = MagicMock()
    #     mock_bq.get_related_objects.side_effect = Exception("BQ error")
    #     monkeypatch.setattr(main_module, 'bq_client', mock_bq)
    #     client = TestClient(main_module.app)
    #     response = client.get("/api/object/SIMG/TEST/001/graph")
    #     assert response.status_code == 500
