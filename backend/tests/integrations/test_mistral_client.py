"""
Tests for the MistralClient class.
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
import json
import requests

from backend.integrations.mistral_client import MistralClient


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_requests_session():
    """Create a mock requests session."""
    with patch('backend.integrations.mistral_client.requests') as mock_requests:
        # Preserve the real requests.exceptions
        import requests as real_requests
        mock_requests.exceptions = real_requests.exceptions
        
        mock_session = MagicMock()
        mock_requests.Session.return_value = mock_session
        yield mock_session, mock_requests


@pytest.fixture
def mistral_client(mock_requests_session):
    """Create a MistralClient instance with mocked session."""
    session, _ = mock_requests_session
    return MistralClient()


# =============================================================================
# Initialization Tests
# =============================================================================

class TestInitialization:
    """Tests for client initialization."""
    
    def test_init_sets_headers(self, mock_requests_session):
        """Test that initialization sets proper headers."""
        session, _ = mock_requests_session
        
        client = MistralClient()
        
        # Check session headers were updated
        session.headers.update.assert_called()
        
    def test_init_uses_settings(self, mock_requests_session):
        """Test that initialization uses settings for configuration."""
        with patch('backend.integrations.mistral_client.settings') as mock_settings:
            mock_settings.mistral_api_key.get_secret_value.return_value = "test-key"
            mock_settings.mistral_base_url = "https://custom.api.com/v1"
            mock_settings.mistral_rate_limit_delay = 0.5
            
            client = MistralClient()
            
            # Verify settings were used
            assert client.api_key == "test-key"
            assert client.base_url == "https://custom.api.com/v1"
            assert client._rate_limit_delay == 0.5


# =============================================================================
# Request Tests
# =============================================================================

class TestRequest:
    """Tests for the _request method."""
    
    def test_request_post_json(self, mistral_client, mock_requests_session):
        """Test POST request with JSON data."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        result = mistral_client._request("POST", "/test", {"key": "value"})
        
        assert result == {"test": "data"}
        session.request.assert_called_once()
        
    def test_request_with_files(self, mistral_client, mock_requests_session):
        """Test request with file upload."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        files = {"file": ("test.txt", "content")}
        result = mistral_client._request("POST", "/upload", files=files)
        
        assert result == {"test": "data"}
        call_kwargs = session.request.call_args[1]
        assert call_kwargs.get("files") == files
        
    def test_request_streaming(self, mistral_client, mock_requests_session):
        """Test streaming request."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = iter([b"line1", b"line2"])
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        result = mistral_client._request("POST", "/stream", stream=True)
        
        assert result == mock_response.iter_lines.return_value
        
    def test_request_retry_on_timeout(self, mistral_client, mock_requests_session):
        """Test retry on timeout error."""
        session, mock_requests = mock_requests_session
        
        # First two calls raise timeout
        mock_response_1 = MagicMock()
        mock_response_1.raise_for_status.side_effect = requests.exceptions.Timeout()
        mock_response_2 = MagicMock()
        mock_response_2.raise_for_status.side_effect = requests.exceptions.Timeout()
        
        # Third call succeeds
        mock_response_3 = MagicMock()
        mock_response_3.json.return_value = {"test": "data"}
        mock_response_3.raise_for_status = MagicMock()
        
        session.request.side_effect = [mock_response_1, mock_response_2, mock_response_3]
        
        with patch('backend.integrations.mistral_client.time.sleep'):  # Don't actually sleep
            result = mistral_client._request("POST", "/test", {"key": "value"})
        
        assert result == {"test": "data"}
        assert session.request.call_count == 3
        
    def test_request_retry_on_error(self, mistral_client, mock_requests_session):
        """Test retry on generic error."""
        session, _ = mock_requests_session
        
        # First two calls raise error
        mock_response_1 = MagicMock()
        mock_response_1.raise_for_status.side_effect = Exception("Network error")
        mock_response_2 = MagicMock()
        mock_response_2.raise_for_status.side_effect = Exception("Network error")
        
        # Third call succeeds
        mock_response_3 = MagicMock()
        mock_response_3.json.return_value = {"test": "data"}
        mock_response_3.raise_for_status = MagicMock()
        
        session.request.side_effect = [mock_response_1, mock_response_2, mock_response_3]
        
        with patch('backend.integrations.mistral_client.time.sleep'):
            result = mistral_client._request("POST", "/test", {"key": "value"})
        
        assert result == {"test": "data"}
        
    def test_request_max_retries_exceeded(self, mistral_client, mock_requests_session):
        """Test that max retries exceeded raises error."""
        session, _ = mock_requests_session
        
        # All three calls raise error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("Network error")
        session.request.side_effect = [mock_response, mock_response, mock_response]
        
        with patch('backend.integrations.mistral_client.time.sleep'):
            with pytest.raises(Exception):
                mistral_client._request("POST", "/test", {"key": "value"})
        
    def test_request_429_rate_limit(self, mistral_client, mock_requests_session):
        """Test rate limit handling (429)."""
        session, _ = mock_requests_session
        
        # First call returns 429
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 429
        
        # Second call succeeds
        mock_response_2 = MagicMock()
        mock_response_2.json.return_value = {"test": "data"}
        mock_response_2.raise_for_status = MagicMock()
        
        session.request.side_effect = [mock_response_1, mock_response_2]
        
        with patch('backend.integrations.mistral_client.time.sleep'):
            result = mistral_client._request("POST", "/test", {"key": "value"})
        
        assert result == {"test": "data"}


# =============================================================================
# Embedding Tests
# =============================================================================

class TestEmbeddings:
    """Tests for embedding operations."""
    
    def test_create_embedding(self, mistral_client, mock_requests_session):
        """Test creation of a single embedding."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        embedding = mistral_client.create_embedding("test text")
        
        assert embedding == [0.1, 0.2, 0.3]
        
    def test_create_embedding_no_data(self, mistral_client, mock_requests_session):
        """Test error when no embedding data returned."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        with pytest.raises(ValueError) as exc_info:
            mistral_client.create_embedding("test text")
        
        assert "No embedding data" in str(exc_info.value)
        
    def test_create_embedding_empty_response(self, mistral_client, mock_requests_session):
        """Test error when response is empty."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        with pytest.raises(ValueError):
            mistral_client.create_embedding("test text")
            
    def test_create_embeddings_batch(self, mistral_client, mock_requests_session):
        """Test creation of batch embeddings."""
        session, _ = mock_requests_session
        
        # Mock response for batch
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2]},
                {"embedding": [0.3, 0.4]}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        texts = ["text 1", "text 2"]
        embeddings = mistral_client.create_embeddings(texts, batch_size=2)
        
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2]
        assert embeddings[1] == [0.3, 0.4]
        
    def test_create_embeddings_batch_multiple_batches(self, mistral_client, mock_requests_session):
        """Test batching with multiple API calls."""
        session, _ = mock_requests_session
        
        # First batch
        mock_response_1 = MagicMock()
        mock_response_1.json.return_value = {
            "data": [{"embedding": [0.1]}, {"embedding": [0.2]}]
        }
        mock_response_1.raise_for_status = MagicMock()
        
        # Second batch
        mock_response_2 = MagicMock()
        mock_response_2.json.return_value = {
            "data": [{"embedding": [0.3]}, {"embedding": [0.4]}]
        }
        mock_response_2.raise_for_status = MagicMock()
        
        session.request.side_effect = [mock_response_1, mock_response_2]
        
        texts = ["text 1", "text 2", "text 3", "text 4"]
        with patch('backend.integrations.mistral_client.time.sleep'):
            embeddings = mistral_client.create_embeddings(texts, batch_size=2)
        
        assert len(embeddings) == 4
        assert session.request.call_count == 2
        
    def test_create_embeddings_rate_limit(self, mistral_client, mock_requests_session):
        """Test rate limiting between batches."""
        session, _ = mock_requests_session
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1]}]
        }
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        texts = ["text 1", "text 2"]
        
        with patch('backend.integrations.mistral_client.time.sleep') as mock_sleep:
            mistral_client._rate_limit_delay = 0.1
            mistral_client.create_embeddings(texts, batch_size=1)
            
            # Should sleep between batches
            assert mock_sleep.call_count >= 1


# =============================================================================
# Chat Completion Tests
# =============================================================================

class TestChatCompletion:
    """Tests for chat completion operations."""
    
    def test_chat_completion(self, mistral_client, mock_requests_session):
        """Test chat completion."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        messages = [{"role": "user", "content": "Hello"}]
        result = mistral_client.chat_completion(messages)
        
        assert result["choices"][0]["message"]["content"] == "Hello!"
        
    def test_chat_completion_with_params(self, mistral_client, mock_requests_session):
        """Test chat completion with custom parameters."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}]
        }
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        messages = [{"role": "user", "content": "Hello"}]
        result = mistral_client.chat_completion(
            messages,
            model="test-model",
            temperature=0.5,
            max_tokens=100
        )
        
        # Verify request was made with correct params
        call_args = session.request.call_args[1]
        data = call_args.get("json")
        assert data["model"] == "test-model"
        assert data["temperature"] == 0.5
        assert data["max_tokens"] == 100
        
    def test_chat_completion_streaming(self, mistral_client, mock_requests_session):
        """Test streaming chat completion."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = iter([b"data: ...", b"data: ..."])
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        messages = [{"role": "user", "content": "Hello"}]
        result = mistral_client.chat_completion(messages, stream=True)
        
        assert result == mock_response.iter_lines.return_value


# =============================================================================
# JSON Extraction Tests
# =============================================================================

class TestJsonExtraction:
    """Tests for JSON response extraction."""
    
    def test_extract_json_response(self, mistral_client, mock_requests_session):
        """Test JSON extraction from chat response."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"key": "value"}'}}]
        }
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        schema = {"type": "object", "properties": {"key": {"type": "string"}}}
        result = mistral_client.extract_json_response("test prompt", schema)
        
        assert result == {"key": "value"}
        
    def test_extract_json_response_with_regex_fallback(self, mistral_client, mock_requests_session):
        """Test regex fallback when JSON is wrapped in text."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": 'Some text {"key": "value"} more text'}}]
        }
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        schema = {"type": "object"}
        result = mistral_client.extract_json_response("test prompt", schema)
        
        assert result == {"key": "value"}
        
    def test_extract_json_response_fails(self, mistral_client, mock_requests_session):
        """Test failure when JSON cannot be extracted."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Not JSON at all"}}]
        }
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        schema = {"type": "object"}
        
        with pytest.raises(ValueError) as exc_info:
            mistral_client.extract_json_response("test prompt", schema)
        
        assert "Could not parse JSON" in str(exc_info.value)
        
    def test_extract_json_response_no_choices(self, mistral_client, mock_requests_session):
        """Test failure when no choices returned."""
        session, _ = mock_requests_session
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": []}
        mock_response.raise_for_status = MagicMock()
        session.request.return_value = mock_response
        
        schema = {"type": "object"}
        
        with pytest.raises(ValueError) as exc_info:
            mistral_client.extract_json_response("test prompt", schema)
        
        assert "Unexpected response format" in str(exc_info.value)


# =============================================================================
# Token Usage Tests
# =============================================================================

class TestTokenUsage:
    """Tests for token usage tracking."""
    
    def test_record_usage(self, mistral_client):
        """Test token usage recording."""
        result = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        
        mistral_client._record_usage(result)
        
        # Usage should be stored in thread-local
        usage = mistral_client.pop_last_usage()
        
        assert usage is not None
        assert usage["prompt"] == 100
        assert usage["completion"] == 50
        assert usage["total"] == 150
        
    def test_record_usage_no_usage_field(self, mistral_client):
        """Test recording usage when response has no usage field."""
        result = {"test": "data"}
        
        mistral_client._record_usage(result)
        
        # Should return None
        usage = mistral_client.pop_last_usage()
        
        assert usage is None
        
    def test_record_usage_missing_tokens(self, mistral_client):
        """Test recording usage with missing token fields."""
        result = {
            "usage": {
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None
            }
        }
        
        mistral_client._record_usage(result)
        
        usage = mistral_client.pop_last_usage()
        
        assert usage is not None
        assert usage["prompt"] == 0
        assert usage["completion"] == 0
        assert usage["total"] == 0
        
    def test_pop_last_usage_clears(self, mistral_client):
        """Test that pop_last_usage clears the stored usage."""
        result = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        
        mistral_client._record_usage(result)
        usage1 = mistral_client.pop_last_usage()
        usage2 = mistral_client.pop_last_usage()
        
        assert usage1 is not None
        assert usage2 is None  # Should be cleared
        
    def test_pop_last_usage_thread_isolated(self, mistral_client):
        """Test that token usage is thread-local."""
        result = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        
        mistral_client._record_usage(result)
        usage = mistral_client.pop_last_usage()
        
        # Usage should be isolated to this thread
        assert usage is not None
