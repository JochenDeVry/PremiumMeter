# Backend Testing Guide

This directory contains the test suite for the PremiumMeter backend.

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_security.py         # Security validation tests
├── test_rate_calculations.py # Rate limit calculation tests
└── test_api_endpoints.py    # API endpoint integration tests
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_security.py
```

### Run tests by marker
```bash
# Run only unit tests
pytest -m unit

# Run only security tests
pytest -m security

# Run only integration tests
pytest -m integration
```

### Run with verbose output
```bash
pytest -v
```

### Run with coverage (when pytest-cov is installed)
```bash
pytest --cov=src --cov-report=html
```

## Test Markers

- `@pytest.mark.unit` - Fast unit tests for individual functions
- `@pytest.mark.integration` - Integration tests requiring database/services
- `@pytest.mark.security` - Security-focused validation tests
- `@pytest.mark.slow` - Tests that take longer to execute

## Test Fixtures

### Database Fixtures
- `db_engine` - Fresh database engine for each test
- `db_session` - Database session with automatic rollback
- `test_client` - FastAPI test client with test database

### Data Fixtures
- `sample_stock_data` - Example stock data
- `sample_premium_data` - Example option premium data

## Writing New Tests

When adding new features, create corresponding tests:

1. **Unit Tests** - Test individual functions in isolation
   ```python
   @pytest.mark.unit
   def test_my_function():
       result = my_function(input)
       assert result == expected
   ```

2. **Integration Tests** - Test API endpoints with test client
   ```python
   @pytest.mark.integration
   def test_my_endpoint(test_client):
       response = test_client.post("/api/endpoint", json={...})
       assert response.status_code == 200
   ```

3. **Security Tests** - Verify input validation
   ```python
   @pytest.mark.security
   def test_invalid_input_rejected():
       with pytest.raises(HTTPException):
           validate_input("invalid")
   ```

## Best Practices

1. **Isolation** - Each test should be independent
2. **Fast** - Use in-memory database for speed
3. **Clear Names** - Test names should describe what they verify
4. **Arrange-Act-Assert** - Structure tests clearly
5. **Mock External Services** - Don't call real APIs in tests

## Test Coverage Goals

- Security validations: 100% coverage
- Business logic: 80%+ coverage
- API endpoints: All happy paths + major error cases

## Continuous Integration

Tests run automatically on:
- Pre-commit (local hook)
- Pull request (GitHub Actions)
- Main branch commits

## Troubleshooting

### Tests fail with database errors
- Ensure test database is using in-memory SQLite
- Check that fixtures properly rollback transactions

### Import errors
- Verify PYTHONPATH includes project root
- Check that `src` module is importable

### Slow tests
- Use `pytest -m "not slow"` to skip slow tests during development
- Consider mocking external services
