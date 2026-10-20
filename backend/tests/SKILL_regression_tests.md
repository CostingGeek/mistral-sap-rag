---
name: sap-rag-regression-tests
description: Run and manage regression tests for the SAP RAG chat application backend with comprehensive mocking to prevent false positives.
title: SAP RAG Regression Tests
user-invocable: true
---

# Regression Test Skill for SAP RAG Application

## Overview

This skill provides the ability to run regression tests for the SAP RAG chat application backend. It includes comprehensive test suites with proper mocking to prevent false positives.

## Quick Start

### Using the Test Runner Script

The easiest way to run tests is using the provided runner script:

```bash
# From project root
uv run python backend/tests/run_regression_tests.py

# Run specific test groups
uv run python backend/tests/run_regression_tests.py --group api
uv run python backend/tests/run_regression_tests.py --group integrations
uv run python backend/tests/run_regression_tests.py --group services

# With verbose output
uv run python backend/tests/run_regression_tests.py --verbose

# With coverage
uv run python backend/tests/run_regression_tests.py --coverage
```

### Using pytest Directly

```bash
# All tests
uv run python -m pytest backend/tests/ -v

# Specific groups
uv run python -m pytest backend/tests/api/ -v
uv run python -m pytest backend/tests/integrations/ -v
uv run python -m pytest backend/tests/services/ -v
```

## Test Structure

The backend tests are organized into:
- **API Tests** (`backend/tests/api/`): FastAPI endpoint tests
- **Integration Tests** (`backend/tests/integrations/`): BigQuery and Mistral client tests
- **Service Tests** (`backend/tests/services/`): Chat service and other service tests

## Test Data Factories

The conftest.py provides factory functions for creating proper test data structures:

- `make_bq_row()`: Creates mock BigQuery row dictionaries
- `make_chunk_info()`: Creates ChunkInfo model instances
- `make_chat_response()`: Creates ChatResponse model instances (JSON-serializable)
- `make_bq_ref_row()`: Creates reference row dictionaries
- `make_bq_object_row()`: Creates object info row dictionaries

## Fixtures

### Mock Clients

- `mock_bigquery_client`: Mocked BigQuery client with proper data structures
- `mock_mistral_client`: Mocked Mistral client with JSON-serializable responses
- `mock_chat_service`: Mocked chat service returning proper ChatResponse objects

### Settings

- `mock_settings`: Mock settings with test values (no hardcoded GCP identifiers)
- `patch_global_settings`: Auto-used fixture that patches global settings for all tests

## Running Tests

### Run All Tests

```bash
cd /c/Dev/mistral-sap-rag/sap-rag-app
uv run python -m pytest backend/tests/ -v
```

### Run Specific Test Groups

```bash
# API tests only
uv run python -m pytest backend/tests/api/ -v

# Integration tests only
uv run python -m pytest backend/tests/integrations/ -v

# Service tests only
uv run python -m pytest backend/tests/services/ -v
```

### Run with Coverage

```bash
uv run python -m pytest backend/tests/ --cov=backend --cov-report=term
```

### Run with Verbose Output

```bash
uv run python -m pytest backend/tests/ -v -s
```

## Test Results

Current status (as of implementation):
- **Total Tests**: 103
- **Passing**: 99
- **Skipped**: 1 (test_get_related_objects - requires complex nested query mocking)
- **Failing**: 3 (API error handling tests - module-level instance patching issues)
- **Pass Rate**: 96.1%

## Known Issues

### API Error Handling Tests (3 failing)

The following tests currently fail due to module-level instance patching challenges:

1. `backend/tests/api/test_chat.py::TestErrorHandling::test_chat_endpoint_service_error`
2. `backend/tests/api/test_objects.py::TestObjectErrorHandling::test_object_endpoint_service_error`
3. `backend/tests/api/test_objects.py::TestObjectErrorHandling::test_graph_endpoint_service_error`

**Root Cause**: The TestClient fixture imports the app at module level, which already has service instances (bq_client, mistral_client, chat_service) created. Patching these instances after import doesn't affect the already-created instances.

**Workaround**: These tests can be skipped or the application architecture can be refactored to use dependency injection instead of module-level instances.

### Complex Graph Test (1 skipped)

- `backend/tests/integrations/test_bigquery_client.py::TestGraph::test_get_related_objects`

**Root Cause**: This test requires mocking multiple nested queries that are triggered by get_related_objects(), which calls query() twice and then calls get_object_info() for each node, triggering additional queries.

**Workaround**: Currently skipped with pytest.skip(). Can be implemented with more complex mocking if needed.

## Best Practices for Adding New Tests

1. **Use Factory Functions**: Always use the factory functions from conftest.py (make_bq_row, make_chunk_info, etc.) to ensure consistent test data structures.

2. **Avoid MagicMock with __getitem__**: When mocking BigQuery results, use actual dictionaries instead of MagicMock objects with __getitem__ side_effects. The query method calls dict(row) on each row, which doesn't work with MagicMock.

3. **Preserve Exception Classes**: When patching modules like requests, preserve the exceptions module:
   ```python
   with patch('module.requests') as mock_requests:
       import requests as real_requests
       mock_requests.exceptions = real_requests.exceptions
   ```

4. **Use Proper Data Structures**: Ensure all mocked data matches the actual return types. For example:
   - BigQuery rows should be dictionaries with all required fields
   - ChatResponse should use the Pydantic model, not MagicMock
   - Embedding vectors should be lists of floats

5. **Session ID Handling**: When testing chat_service.chat() directly (not through the endpoint), remember that the endpoint sets response.session_id. Either:
   - Set it explicitly in tests: `response.session_id = "test-session"`
   - Or update the ChatResponse creation in chat_service.chat() to include session_id

## Performance Notes

The test suite runs in approximately 2-3 seconds with 100+ tests. For faster feedback during development:

```bash
# Run only the most recent failing tests
uv run python -m pytest backend/tests/ -v --last-failed

# Run with parallel execution (requires pytest-xdist)
uv run python -m pytest backend/tests/ -v -n auto
```

## Continuous Integration

For CI/CD pipelines, run:

```bash
cd /c/Dev/mistral-sap-rag/sap-rag-app
uv run python -m pytest backend/tests/ -v --tb=short -q
```

This will:
- Run all backend tests
- Show verbose output
- Use short tracebacks
- Be quiet about passing tests

## Maintenance

### Adding New Endpoints

When adding new endpoints:
1. Add corresponding tests in `backend/tests/api/`
2. Use the mock fixtures (mock_bigquery_client, mock_mistral_client, etc.)
3. Ensure all return types match the actual endpoint responses

### Updating Schemas

When updating Pydantic schemas:
1. Update the factory functions in conftest.py to match
2. Run all tests to ensure no breakage
3. Update any hardcoded test data to match new schema fields

## Troubleshooting

### Test Fails with KeyError

**Cause**: Mock data is missing required fields.

**Solution**: Use the factory functions from conftest.py or ensure all dictionary keys match the expected schema.

### Test Fails with TypeError: catching classes that do not inherit from BaseException

**Cause**: Mocked module's exception classes have been replaced with MagicMock objects.

**Solution**: Preserve the original exception classes when patching:
```python
with patch('module.requests') as mock_requests:
    import requests as real_requests
    mock_requests.exceptions = real_requests.exceptions
```

### Test Fails with AssertionError on session_id

**Cause**: The chat_service.chat() method doesn't set session_id on the ChatResponse. The main.py endpoint does this.

**Solution**: Either set it explicitly in tests or update the chat_service.chat() method.
