# Backend Tests

This directory contains pytest-based tests for the SAP RAG Chat Application backend.

## Structure

```
backend/tests/
├── __init__.py              # Test package init
├── conftest.py             # Shared fixtures and configuration
├── README.md               # This file
│
├── api/
│   ├── __init__.py
│   ├── test_chat.py        # Chat endpoint tests
│   └── test_objects.py     # Object endpoint tests
│
├── integrations/
│   ├── __init__.py
│   ├── test_bigquery_client.py  # BigQuery client tests
│   └── test_mistral_client.py   # Mistral client tests
│
└── services/
    ├── __init__.py
    └── test_chat_service.py      # Chat service tests
```

## Test Coverage

### Services Layer (`services/`)
- **test_chat_service.py**: Comprehensive tests for ChatService
  - Intent classification (simple, multi-intent, follow-up)
  - Chunk retrieval with various scopes and filters
  - Graph expansion with reference traversal
  - Answer synthesis with citation extraction
  - Full chat flow with performance instrumentation
  - Error handling and edge cases

### Integrations Layer (`integrations/`)
- **test_bigquery_client.py**: Tests for BigQueryClient
  - Initialization with credentials and ADC
  - Dataset and table operations
  - Similarity retrieval with ML.DISTANCE
  - Object information retrieval
  - Graph traversal (related objects)
  - Batch operations
  - Scope filtering (standard, nova, both)

- **test_mistral_client.py**: Tests for MistralClient
  - Initialization and configuration
  - Request handling with retries
  - Embedding creation (single and batch)
  - Chat completion (standard and streaming)
  - JSON response extraction with fallback
  - Token usage tracking (thread-local)
  - Error handling (timeouts, rate limits, network errors)

### API Layer (`api/`)
- **test_chat.py**: Tests for chat endpoints
  - POST /api/chat
  - POST /api/chat/stream
  - Request validation
  - Error handling
  - Scope and session management

- **test_objects.py**: Tests for object endpoints
  - GET /api/object/{object_id}
  - GET /api/object/{object_id}/graph
  - URL encoding for IDs with slashes
  - Scope parameter handling
  - Error states (not found, service errors)

## Running Tests

### Install dependencies
```bash
# Install backend and dev dependencies
make install-dev

# Or using uv directly
uv sync --dev
```

### Run all backend tests
```bash
# Using make
make test-backend

# Using pytest directly
uv run python -m pytest backend/tests/ -v

# With coverage
uv run python -m pytest backend/tests/ --cov=backend --cov-report=term-missing -v
```

### Run specific test modules
```bash
# Run only chat service tests
uv run python -m pytest backend/tests/services/test_chat_service.py -v

# Run only API tests
uv run python -m pytest backend/tests/api/ -v

# Run only integration tests
uv run python -m pytest backend/tests/integrations/ -v
```

### Run with markers
```bash
# Run only unit tests (if marked)
pytest -m unit

# Run only integration tests (if marked)
pytest -m integration

# Run regression tests
pytest -m regression
```

## Fixtures

The `conftest.py` file provides shared fixtures:

- `mock_settings`: Mocked application settings
- `mock_bigquery_client`: Mock BigQuery client with canned responses
- `mock_mistral_client`: Mock Mistral client with canned responses
- `chat_service`: ChatService instance with mocked clients
- `sample_chat_request`: Sample chat request for testing
- `sample_chunk_info`: Sample chunk information
- `sample_chunks`: List of sample chunks

## Mocking Strategy

All external services (BigQuery, Mistral API) are mocked using `unittest.mock.MagicMock`:

- BigQuery responses return canned data structures
- Mistral API responses return predictable chat completions and embeddings
- Token usage is tracked via the client's thread-local storage
- Network errors and timeouts are simulated for error handling tests

## Key Test Scenarios Covered

### Regression Testing Focus Areas

1. **Citation Integrity**
   - `[Source N]` extraction from answers
   - Corpus labeling (SAP standard vs Company standard)
   - Graph-expanded chunk handling

2. **Markdown Rendering** (tested via API responses)
   - List rendering (numbered + nested bullets)
   - Code blocks
   - Tables
   - Headers
   - Inline styles (bold, italic, code)

3. **Scope Isolation**
   - Standard corpus queries
   - Nova corpus queries
   - Combined scope queries
   - Valid scope validation

4. **Error Resilience**
   - API failures
   - Empty results
   - Malformed responses
   - Network timeouts
   - Rate limiting (429)

5. **Performance Instrumentation**
   - Timing metrics for each pipeline step
   - Token usage tracking
   - Trace completeness

6. **Graph Expansion**
   - Reference traversal logic
   - Deduplication of chunks
   - Hops limitation
   - Batch operations

## Adding New Tests

1. Create a new test file in the appropriate directory
2. Import necessary fixtures from conftest.py
3. Use `unittest.mock.MagicMock` for external dependencies
4. Follow the existing pattern of test classes and methods
5. Add custom fixtures if needed in conftest.py

## Best Practices

- **Isolate tests**: Each test should be independent
- **Mock external services**: Never call real BigQuery or Mistral APIs
- **Test edge cases**: Empty results, errors, validation failures
- **Verify instrumentation**: Check that timing and token metrics are captured
- **Test both success and failure paths**
