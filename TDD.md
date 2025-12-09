# Test-Driven Development (TDD) Workflow

This document describes the Test-Driven Development workflow for the PDF Converter Service project, following AGENTS.md guidelines.

## TDD Principles

**Test-Driven Development is mandatory for all new features and bug fixes.**

### The TDD Cycle: RED → GREEN → REFACTOR

```
┌─────────────────────────────────────────────────────┐
│  1. RED: Write a failing test                      │
│     - Test should fail (feature not implemented)   │
│     - Run: pytest tests/test_feature.py -v        │
├─────────────────────────────────────────────────────┤
│  2. GREEN: Write minimal code to pass             │
│     - Implement just enough to make test pass     │
│     - Don't over-engineer                         │
│     - Run: pytest tests/test_feature.py -v        │
├─────────────────────────────────────────────────────┤
│  3. REFACTOR: Improve code while tests stay green │
│     - Clean up code                               │
│     - Improve structure                           │
│     - Tests must still pass                       │
├─────────────────────────────────────────────────────┤
│  4. REPEAT: Move to next feature/test             │
└─────────────────────────────────────────────────────┘
```

## Workflow Steps

### Phase 1: RED (Write Failing Tests)

**Goal:** Write tests that define the expected behavior.

```bash
# 1. Create or edit test file
vim tests/test_new_feature.py

# 2. Write test that describes desired behavior
# Example:
def test_pdf_size_validation():
    """Test that PDFs over 100MB are rejected."""
    large_pdf = b'%PDF-1.4\n' + b'0' * (101 * 1024 * 1024)

    response = client.post(
        CONVERTER_PATH,
        content=large_pdf,
        headers={"Content-Type": "application/pdf"}
    )

    assert response.status_code == 413
    assert "too large" in response.json()["detail"].lower()

# 3. Run test - it should FAIL
pytest tests/test_new_feature.py::test_pdf_size_validation -v

# Expected output: FAILED (test fails because feature not implemented)
```

### Phase 2: GREEN (Write Minimal Code)

**Goal:** Make the failing test pass with minimal code.

```bash
# 1. Implement feature in production code
vim app/main.py

# Example implementation:
MAX_PDF_SIZE = 100 * 1024 * 1024  # 100MB

@app.post("/api/pdfconverter")
async def convert_pdf_endpoint(request: Request):
    pdf_bytes = await request.body()

    # NEW: Size validation
    if len(pdf_bytes) > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"PDF file too large (max {MAX_PDF_SIZE} bytes)"
        )
    # ... rest of implementation

# 2. Run test again - it should PASS
pytest tests/test_new_feature.py::test_pdf_size_validation -v

# Expected output: PASSED
```

### Phase 3: REFACTOR (Improve Code)

**Goal:** Improve code quality while keeping tests green.

```bash
# 1. Refactor code for better structure
vim app/main.py

# Example refactor:
def validate_pdf_size(pdf_bytes: bytes, max_size: int = MAX_PDF_SIZE) -> None:
    """Validate PDF size against maximum allowed size."""
    if len(pdf_bytes) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"PDF file too large (max {max_size} bytes)"
        )

# 2. Update production code to use helper
@app.post("/api/pdfconverter")
async def convert_pdf_endpoint(request: Request):
    pdf_bytes = await request.body()
    validate_pdf_size(pdf_bytes)  # Use helper
    # ... rest of implementation

# 3. Run tests to ensure refactor didn't break anything
pytest tests/test_new_feature.py -v

# Expected output: PASSED (all tests still green)
```

### Phase 4: REPEAT

Move to the next test and repeat the cycle.

## Example: Adding a New Feature (Complete Workflow)

### Feature Request: Add PDF Metadata Extraction

**Step 1: Write Test First (RED)**

```python
# tests/test_metadata.py
import pytest
from app.main import CONVERTER_PATH

class TestMetadataExtraction:
    """Tests for PDF metadata extraction."""

    def test_extract_metadata_from_pdf(self, client, valid_pdf):
        """Test that metadata is extracted from PDF."""
        response = client.post(
            f"{CONVERTER_PATH}/metadata",
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"}
        )

        assert response.status_code == 200
        metadata = response.json()
        assert "title" in metadata
        assert "author" in metadata
        assert "created_date" in metadata
```

Run test:
```bash
pytest tests/test_metadata.py::TestMetadataExtraction::test_extract_metadata_from_pdf -v
# Result: FAILED (endpoint doesn't exist)
```

**Step 2: Write Minimal Code (GREEN)**

```python
# app/metadata.py (new file)
from pypdf import PdfReader
from io import BytesIO

def extract_metadata(pdf_bytes: bytes) -> dict[str, str]:
    """Extract metadata from PDF bytes."""
    reader = PdfReader(BytesIO(pdf_bytes))
    metadata = reader.metadata

    return {
        "title": metadata.get("/Title", ""),
        "author": metadata.get("/Author", ""),
        "created_date": metadata.get("/CreationDate", ""),
    }

# app/main.py (add endpoint)
from .metadata import extract_metadata

@app.post("/api/pdfconverter/metadata")
async def extract_metadata_endpoint(request: Request):
    """Extract metadata from PDF."""
    pdf_bytes = await request.body()
    metadata = extract_metadata(pdf_bytes)
    return metadata
```

Run test:
```bash
pytest tests/test_metadata.py::TestMetadataExtraction::test_extract_metadata_from_pdf -v
# Result: PASSED
```

**Step 3: Refactor (REFACTOR)**

```python
# Improve error handling
def extract_metadata(pdf_bytes: bytes) -> dict[str, str]:
    """Extract metadata from PDF bytes.

    Args:
        pdf_bytes: PDF file as bytes

    Returns:
        Dictionary with title, author, created_date

    Raises:
        ValueError: If PDF is invalid
    """
    if not pdf_bytes.startswith(b'%PDF'):
        raise ValueError("Not a valid PDF file")

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        metadata = reader.metadata or {}

        return {
            "title": metadata.get("/Title", "Unknown"),
            "author": metadata.get("/Author", "Unknown"),
            "created_date": metadata.get("/CreationDate", "Unknown"),
        }
    except Exception as e:
        raise ValueError(f"Failed to extract metadata: {e}")
```

Run test:
```bash
pytest tests/test_metadata.py -v
# Result: PASSED (tests still green after refactor)
```

**Step 4: Add More Tests**

```python
# Add edge cases
def test_extract_metadata_invalid_pdf(self, client):
    """Test that invalid PDFs return 400."""
    response = client.post(
        f"{CONVERTER_PATH}/metadata",
        content=b"not a pdf",
        headers={"Content-Type": "application/pdf"}
    )

    assert response.status_code == 400

def test_extract_metadata_empty_pdf(self, client):
    """Test that empty PDFs return 400."""
    response = client.post(
        f"{CONVERTER_PATH}/metadata",
        content=b"",
        headers={"Content-Type": "application/pdf"}
    )

    assert response.status_code == 400
```

## Best Practices

### DO ✅

1. **Write tests before code**
   - Tests define the interface and behavior
   - Prevents over-engineering

2. **Keep tests simple and focused**
   - One test per behavior
   - Clear test names

3. **Use descriptive test names**
   - `test_pdf_conversion_succeeds_with_valid_input`
   - Not: `test_1`

4. **Test behavior, not implementation**
   - Test what the code does, not how it does it
   - Allows refactoring without breaking tests

5. **Run tests frequently**
   - After every small change
   - Keep feedback loop short (minutes, not hours)

6. **Keep the bar green**
   - All tests must pass before committing
   - Fix failing tests immediately

### DON'T ❌

1. **Don't write all tests upfront**
   - Write one test, implement, move to next
   - TDD is an iterative process

2. **Don't skip the RED phase**
   - Always see the test fail first
   - Ensures test actually tests something

3. **Don't write production code without a failing test**
   - Every line of production code should have a test
   - No speculative features

4. **Don't over-engineer in GREEN phase**
   - Write just enough code to pass the test
   - Optimization comes in REFACTOR phase

5. **Don't commit with failing tests**
   - Tests must be green before commit
   - Fix or remove failing tests

6. **Don't skip tests for "simple" code**
   - Simple code can have bugs too
   - Tests document expected behavior

## Pre-Commit Checklist

Before every commit, run:

```bash
# 1. Run full test suite
pytest

# 2. Check coverage
pytest --cov=app --cov-report=term-missing

# 3. Format code
black app tests

# 4. Lint code
ruff check app tests --fix

# 5. Type check
mypy app --ignore-missing-imports

# 6. Run pre-commit hooks
pre-commit run --all-files

# 7. Verify all tests still pass
pytest
```

All steps must pass before committing.

## Test Organization

### Test File Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_api.py              # API endpoint tests
├── test_converter.py        # PDF conversion tests
├── test_metrics.py          # Prometheus metrics tests
└── integration/
    └── test_end_to_end.py   # End-to-end tests
```

### Test Categories

1. **Unit Tests** (Majority)
   - Test individual functions in isolation
   - Use mocks for external dependencies
   - Fast execution (< 1 second)

2. **Integration Tests** (Selective)
   - Test multiple components together
   - Use real dependencies where feasible
   - Slower execution (1-10 seconds)

3. **End-to-End Tests** (Minimal)
   - Test complete user workflows
   - Use real services
   - Slowest execution (10+ seconds)

## Coverage Goals

- **Minimum:** 80% coverage
- **Target:** 90% coverage
- **Ideal:** 95%+ coverage

Check coverage:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Resources

- [AGENTS.md](AGENTS.md) - Development guidelines
- [pytest Documentation](https://docs.pytest.org/)
- [Test-Driven Development by Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530) - Kent Beck
- [Growing Object-Oriented Software, Guided by Tests](https://www.amazon.com/Growing-Object-Oriented-Software-Guided-Tests/dp/0321503627)

## Summary

**TDD is not optional - it's the way we develop features in this project.**

1. ✅ Write test first (RED)
2. ✅ Write minimal code (GREEN)
3. ✅ Refactor for quality (REFACTOR)
4. ✅ Repeat for next feature

**Remember:** Tests and production code develop in parallel, one small step at a time.
