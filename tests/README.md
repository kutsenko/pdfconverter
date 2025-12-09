# PDF Converter Tests

Comprehensive test suite for the PDF Converter Service with unit tests, integration tests, edge-case tests, and metrics tests.

**Target Coverage: >90%** (Currently: 87%, improving with new tests)

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── test_api.py              # API integration tests (20 tests)
├── test_converter.py        # Converter unit tests (15 tests)
├── test_metrics.py          # Prometheus metrics tests (28 tests)
├── test_edge_cases.py       # Edge case and boundary tests (40+ tests)
├── integration/
│   ├── __init__.py
│   └── test_end_to_end.py  # End-to-end workflow tests (30+ tests)
└── README.md                # This file
```

## Test Categories

### Unit Tests (Majority - Fast)

**test_api.py (20 tests)**
- Health and metrics endpoints
- PDF converter endpoint functionality
- Content-Type validation
- Error handling (400, 413, 415, 422, 500)
- Health check header processing
- Response headers

**test_converter.py (15 tests)**
- PDF validation
- Successful conversion
- Error handling
- Logging (INFO/DEBUG levels)
- Temporary file cleanup
- Python module integration

**test_metrics.py (28 tests)**
- Metric definitions
- Histogram bucket configurations
- Metric labels
- Prometheus naming conventions
- Integration with application

### Integration Tests (Selective - Medium Speed)

**integration/test_end_to_end.py (30+ tests)**
- Complete conversion workflows
- Health check workflows
- Monitoring workflows
- Error handling through complete stack
- Metrics integration
- Configurable endpoints
- Middleware integration
- Input validation end-to-end
- Concurrent request handling

### Edge Case Tests (Comprehensive - Fast)

**test_edge_cases.py (40+ tests)**
- Content-Type edge cases
- Health check header variations
- PDF size boundary conditions
- Error response formats
- Request body handling
- HTTP method handling
- Unknown endpoints
- Conversion error types
- Response size handling

## Installation

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

### All Tests

```bash
pytest
```

### With Coverage Report

```bash
pytest --cov=app --cov-report=html
```

Coverage report is generated in `htmlcov/index.html`.

### Specific Test Files

```bash
# Only API tests
pytest tests/test_api.py

# Only converter tests
pytest tests/test_converter.py

# Only metrics tests
pytest tests/test_metrics.py

# Only edge case tests
pytest tests/test_edge_cases.py

# Only integration tests
pytest tests/integration/
```

### Specific Test Classes

```bash
# Run specific test class
pytest tests/test_api.py::TestHealthEndpoint

# Run specific test method
pytest tests/test_api.py::TestHealthEndpoint::test_health_check_returns_200
```

### Verbose Output

```bash
pytest -vv
```

### Stop on First Failure

```bash
pytest -x
```

### Run Only Failed Tests

```bash
# Run tests, then run only failed ones
pytest
pytest --lf  # Last failed
```

## Coverage Goals

- **Minimum:** 80% (baseline)
- **Target:** 90% (current goal)
- **Ideal:** 95%+ (excellence)

### Check Coverage

```bash
# Terminal report
pytest --cov=app --cov-report=term-missing

# HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml
```

### Coverage Report Details

```bash
# Show missing lines
pytest --cov=app --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov=app --cov-fail-under=90
```

## Test-Driven Development (TDD)

**All new features must follow TDD workflow.**

See [TDD.md](../TDD.md) for complete TDD workflow documentation.

### Quick TDD Cycle

1. **RED**: Write failing test
   ```bash
   pytest tests/test_new_feature.py -v  # Should FAIL
   ```

2. **GREEN**: Write minimal code to pass test
   ```bash
   pytest tests/test_new_feature.py -v  # Should PASS
   ```

3. **REFACTOR**: Improve code while keeping tests green
   ```bash
   pytest tests/test_new_feature.py -v  # Should still PASS
   ```

4. **REPEAT**: Move to next feature

## Test Fixtures

Shared fixtures are defined in `conftest.py`:

### Available Fixtures

- `client`: FastAPI TestClient for API testing
- `valid_pdf`: Minimal valid PDF for successful conversion tests
- `invalid_pdf`: Invalid PDF data for error testing
- `large_pdf`: PDF exceeding size limit for 413 testing
- `empty_pdf`: Empty bytes for empty PDF testing

### Mocking

The `pdfa` Python module is mocked in `conftest.py` using `sys.modules` to enable tests to run without Docker dependencies.

## Continuous Integration

### Pre-Commit Checks

Before committing:

```bash
# 1. Run tests
pytest

# 2. Check coverage
pytest --cov=app --cov-fail-under=90

# 3. Format code
black app tests

# 4. Lint code
ruff check app tests --fix

# 5. Type check
mypy app --ignore-missing-imports
```

### GitHub Actions

Automated testing runs on:
- Push to main/master/develop
- Pull requests
- Weekly schedule (Monday 00:00 UTC)

See `.github/workflows/security.yml` for CI/CD configuration.

## Test Quality Requirements

Per AGENTS.md guidelines:

✅ **All tests must pass** - Zero tolerance for failing tests
✅ **No disabled tests** - Don't skip or comment out failing tests
✅ **Fix or remove** - If test fails, fix it or remove it
✅ **Tests first** - Write tests before production code (TDD)
✅ **High coverage** - Target >90% code coverage

## Makefile Commands

```bash
# Tests
make test              # Run all tests
make test-cov          # Run with coverage
make test-fast         # Stop on first failure
make test-api          # Only API tests
make test-converter    # Only converter tests
make test-metrics      # Only metrics tests

# Coverage
make coverage-html     # Generate HTML coverage report
```

## Test Documentation

Each test file includes:

- **Class docstrings**: Describe test category
- **Method docstrings**: Describe specific test case
- **Inline comments**: Explain non-obvious test logic

### Example Test Structure

```python
class TestFeature:
    """Tests for specific feature."""

    def test_success_case(self, client):
        """Test that feature works under normal conditions."""
        # Arrange
        input_data = prepare_test_data()

        # Act
        response = client.post("/endpoint", data=input_data)

        # Assert
        assert response.status_code == 200
        assert response.json() == expected_output

    def test_error_case(self, client):
        """Test that feature handles errors correctly."""
        # Arrange
        invalid_data = prepare_invalid_data()

        # Act
        response = client.post("/endpoint", data=invalid_data)

        # Assert
        assert response.status_code == 400
        assert "error message" in response.json()["detail"]
```

## Debugging Tests

### Run with Print Statements

```bash
pytest -s  # Show print() output
```

### Run with PDB (Python Debugger)

```bash
pytest --pdb  # Drop into debugger on failure
```

### Show Locals on Failure

```bash
pytest --showlocals  # Show local variables on failure
```

### Verbose Assertion Details

```bash
pytest -vv  # Very verbose, show assertion details
```

## Performance

Test suite should be fast:

- **Unit tests:** < 10 seconds total
- **Integration tests:** < 30 seconds total
- **Full suite:** < 1 minute total

Use mocking to keep tests fast.

## Resources

- [TDD.md](../TDD.md) - Test-Driven Development workflow
- [AGENTS.md](../AGENTS.md) - Development guidelines
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 130+ |
| Unit Tests | 63 |
| Integration Tests | 30+ |
| Edge Case Tests | 40+ |
| Current Coverage | 87% |
| Target Coverage | >90% |
| Test Execution Time | <1 minute |

**All tests must pass before committing. No exceptions.**
