from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def mock_ocrmypdf():
    """Mock OCRmyPDF for all tests."""
    with patch("app.converter.ocrmypdf.ocr") as mock_ocr:
        mock_ocr.return_value = None  # ocrmypdf.ocr returns nothing
        yield mock_ocr


@pytest.fixture(scope="session", autouse=True)
def mock_pikepdf():
    """Mock pikepdf for all tests."""
    with patch("app.converter.pikepdf.open") as mock_open:
        # Mock PDF object (not tagged by default)
        mock_pdf = Mock()
        mock_pdf.Root = {}  # No StructTreeRoot
        mock_pdf.pages = []
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf
        yield mock_open


@pytest.fixture(autouse=True)
def mock_event_loop():
    """Mock asyncio event loop for all tests."""
    # Create a mock async function for backwards compatibility with old tests
    async_mock_func = AsyncMock(return_value=None)

    # Patch both the new (run_in_executor) and old (to_thread) patterns
    with (
        patch("asyncio.get_event_loop") as mock_get_loop,
        patch("asyncio.to_thread", async_mock_func),
    ):
        mock_loop = Mock()
        mock_loop.run_in_executor = AsyncMock(return_value=None)
        mock_get_loop.return_value = mock_loop
        yield mock_loop


@pytest.fixture
def client():
    """
    Create a FastAPI test client.
    """
    from app.main import app

    return TestClient(app)


@pytest.fixture
def valid_pdf():
    """
    Return a minimal valid PDF for testing.
    """
    # Minimal valid PDF (same as used in main.py for health checks)
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj xref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\ntrailer<</Size 3/Root 1 0 R>>startxref\n110\n%%EOF"


@pytest.fixture
def invalid_pdf():
    """
    Return invalid PDF data for testing.
    """
    return b"This is not a PDF file"


@pytest.fixture
def large_pdf():
    """
    Return a PDF that exceeds size limit (mock).
    """
    # Create a PDF header followed by lots of data
    # This is > 50MB
    header = b"%PDF-1.4\n"
    body = b"0" * (51 * 1024 * 1024)  # 51MB
    return header + body


@pytest.fixture
def empty_pdf():
    """
    Return empty PDF data.
    """
    return b""
