# AuraMail Test Suite

## Running Tests

### Run all tests:
```bash
pytest
```

### Run specific test file:
```bash
pytest tests/test_rate_limiter.py
```

### Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

### Run only unit tests:
```bash
pytest -m unit
```

### Run only integration tests:
```bash
pytest -m integration
```

## Test Structure

- `test_rate_limiter.py`: Unit tests for Redis-based rate limiter
- `test_retry_mechanism.py`: Unit tests for tenacity retry mechanism
- `test_api_endpoints.py`: Integration tests for Flask API endpoints
- `test_database.py`: Integration tests for database operations

## Test Coverage

Current coverage focuses on:
- Rate limiting logic
- Retry mechanisms
- API endpoints
- Database operations

## Adding New Tests

1. Create test file in `tests/` directory
2. Use fixtures from `conftest.py` for common setup
3. Mark tests with `@pytest.mark.unit` or `@pytest.mark.integration`
4. Follow naming convention: `test_*.py` for files, `test_*` for functions

