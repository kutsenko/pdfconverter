import pytest
from fastapi.testclient import TestClient


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
    return b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj xref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\ntrailer<</Size 3/Root 1 0 R>>startxref\n110\n%%EOF'


@pytest.fixture
def invalid_pdf():
    """
    Return invalid PDF data for testing.
    """
    return b'This is not a PDF file'


@pytest.fixture
def large_pdf():
    """
    Return a PDF that exceeds size limit (mock).
    """
    # Create a PDF header followed by lots of data
    # This is > 50MB
    header = b'%PDF-1.4\n'
    body = b'0' * (51 * 1024 * 1024)  # 51MB
    return header + body


@pytest.fixture
def empty_pdf():
    """
    Return empty PDF data.
    """
    return b''
