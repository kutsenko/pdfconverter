# PDF Converter Service

FastAPI-based REST interface for converting PDF to PDF/A format.

Uses OCRmyPDF for direct PDF to PDF/A conversion with OCR support.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen.svg)](https://pytest.org)

**[Deutsche Version](README.de.md)** | English

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Build & Deployment](#build--deployment)
- [Usage](#usage)
- [Technical Details](#technical-details)
  - [Architecture](#architecture)
  - [Configuration](#configuration)
  - [Logging](#logging)
  - [Prometheus Metrics](#prometheus-metrics)
- [Development](#development)
  - [Local Development](#local-development)
  - [Project Structure](#project-structure)
- [Testing](#testing)
- [Performance](#performance)
- [References](#references)

## Features

- ⚡ **Fast Conversion:** Average ~0.5s per PDF (Python module instead of CLI)
- 🎯 **Content-Aware Optimization:** Automatic PDF type detection with optimized compression
- 🔧 **Configurable Endpoints:** All URLs customizable via environment variables
- 📊 **Prometheus Metrics:** Complete monitoring with duration, size, error tracking
- 🏥 **Health Check Support:** Dedicated header (`X-Health-Check`) for monitoring
- 📝 **Structured Logging:** DEBUG for health checks, INFO for regular requests
- 🐳 **Docker-Ready:** Fully containerized with Docker support
- ✅ **Production-Ready:** 88% test coverage (139 tests), comprehensive error handling

## Quick Start

```bash
# 1. Build image
docker build -t pdfconverter .

# 2. Start container
docker run -p 8080:8080 pdfconverter

# 3. Convert PDF
curl -X POST http://localhost:8080/api/pdfconverter \
  -H "Content-Type: application/pdf" \
  --data-binary @input.pdf \
  -o output.pdf

# 4. Check metrics
curl http://localhost:8080/metrics/
```

**Or with custom endpoints:**

```bash
docker run -p 8080:8080 \
  -e CONVERTER_PATH=/convert \
  -e HEALTH_PATH=/status \
  -e METRICS_PATH=/monitoring \
  pdfconverter
```

## API Endpoints

> **Note:** All endpoint paths are configurable via environment variables (see [Configuration](#configuration)).

### POST /api/pdfconverter (or ${CONVERTER_PATH})

Converts a PDF to PDF/A format.

**Request:**
- Content-Type: `application/pdf`
- Body: PDF file as raw bytes
- Header (optional): `X-Health-Check: true` for health check requests

**Response:**
- Content-Type: `application/pdf`
- Body: Converted PDF/A as raw bytes

**Error Codes:**
- `400 Bad Request`: Empty or invalid PDF
- `413 Payload Too Large`: PDF larger than 50MB
- `415 Unsupported Media Type`: Wrong Content-Type
- `422 Unprocessable Entity`: PDF cannot be converted
- `500 Internal Server Error`: Unexpected error

### GET /health (or ${HEALTH_PATH})

Simple health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

### GET /metrics (or ${METRICS_PATH})

Prometheus metrics endpoint.

**Metrics:**
- `pdf_conversions_total`: Number of conversions (by status)
- `pdf_conversion_duration_seconds`: Conversion duration
- `pdf_input_size_bytes`: Size of input PDFs
- `pdf_output_size_bytes`: Size of output PDFs
- `pdf_conversion_errors_total`: Number of errors (by type)

**Note:** Health check requests are NOT tracked in metrics.

## Build & Deployment

### Build Docker Image

```bash
docker build -t pdfconverter .
```

### Start Container

```bash
docker run -p 8080:8080 pdfconverter
```

**With custom endpoint URLs:**

```bash
docker run -p 8080:8080 \
  -e HEALTH_PATH=/status \
  -e METRICS_PATH=/monitoring/metrics \
  -e CONVERTER_PATH=/convert \
  pdfconverter
```

### With docker-compose

The project includes a pre-configured `docker-compose.yml` with environment variable placeholders:

```bash
# Start with default values
docker-compose up -d

# Or customize via .env file
cat > .env << EOF
HEALTH_PATH=/status
METRICS_PATH=/monitoring
CONVERTER_PATH=/convert
EOF

docker-compose up -d
```

The `docker-compose.yml` uses the format `${VARIABLE:-default}` to support both .env files and inline environment variables.

## Usage

### cURL Examples

**Regular PDF Conversion:**
```bash
curl -X POST http://localhost:8080/api/pdfconverter \
  -H "Content-Type: application/pdf" \
  --data-binary @input.pdf \
  -o output.pdf
```

**Health Check:**
```bash
curl -X POST http://localhost:8080/api/pdfconverter \
  -H "Content-Type: application/pdf" \
  -H "X-Health-Check: true" \
  --data-binary @input.pdf \
  -o output.pdf
```

**Get Metrics:**
```bash
curl http://localhost:8080/metrics
```

### Python Example

```python
import requests

# Load PDF
with open('input.pdf', 'rb') as f:
    pdf_bytes = f.read()

# Convert
response = requests.post(
    'http://localhost:8080/api/pdfconverter',
    headers={'Content-Type': 'application/pdf'},
    data=pdf_bytes
)

# Save
if response.status_code == 200:
    with open('output.pdf', 'wb') as f:
        f.write(response.content)
else:
    print(f"Error: {response.status_code} - {response.text}")
```

## Technical Details

### Architecture

- **Framework:** FastAPI 0.109.0
- **Base Image:** python:3.12-slim
- **Conversion:** OCRmyPDF (via asyncio.to_thread)
- **OCR Engine:** Tesseract 5.x (German + English)
- **Metrics:** prometheus-client
- **Port:** 8080

### Configuration

**Environment Variables:**

- **HEALTH_PATH:** Health check endpoint (Default: `/health`)
- **METRICS_PATH:** Prometheus metrics endpoint (Default: `/metrics`)
- **CONVERTER_PATH:** PDF conversion endpoint (Default: `/api/pdfconverter`)

**Additional Parameters:**

- **MAX_PDF_SIZE:** 50MB (52428800 bytes)
- **PDF/A Level:** 2
- **OCR:** Enabled with `skip_ocr_on_tagged_pdfs=True` (optimal performance)

**PDF Optimization (Content-Aware):**

The service automatically detects PDF content type and applies appropriate optimization:

- **Text-only PDFs**: Lossless compression (optimize=1)
- **Scanned PDFs**: Lossless compression (optimize=1)
- **Mixed PDFs**: Lossless compression (optimize=1)
- **Unknown PDFs**: No optimization (optimize=0, safe fallback)

**PDF Optimization Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `PDF_TEXT_OPTIMIZE` | `1` | Optimization level for text-only PDFs (0-3) |
| `PDF_SCANNED_OPTIMIZE` | `1` | Optimization level for scanned PDFs (0-3) |
| `PDF_MIXED_OPTIMIZE` | `1` | Optimization level for mixed content PDFs (0-3) |
| `PDF_UNKNOWN_OPTIMIZE` | `0` | Fallback optimization level (0-3) |

**Optimization Levels:**
- `0`: No optimization (fastest conversion, largest files)
- `1`: Lossless compression (recommended, 50-80% size reduction for text PDFs)
- `2`: Lossy image compression (smaller files, minimal quality loss)
- `3`: Aggressive compression (smallest files, visible quality loss possible)

**Example with custom optimization:**

```bash
docker run -p 8080:8080 \
  -e PDF_TEXT_OPTIMIZE=1 \
  -e PDF_SCANNED_OPTIMIZE=1 \
  pdfconverter
```

### Logging

Logging distinguishes between regular requests and health checks:

- **Regular Requests:** INFO Level
  - "begin conversion"
  - "completed conversion success/error"

- **Health Checks:** DEBUG Level
  - "begin HEALTHCHECK"
  - "completed HEALTHCHECK success/error"

### Prometheus Metrics

Metrics are only recorded for non-health-check requests.

**Histogram Buckets:**
- Duration: 0.1s to 120s
- Size: 1KB to 50MB

## Development

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

**Note:** For local development, install system dependencies:
- **Ubuntu/Debian:** `apt-get install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng ghostscript qpdf pngquant unpaper`
- **macOS:** `brew install tesseract tesseract-lang ghostscript qpdf pngquant unpaper`

### Project Structure

```
pdfconverter/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI Application
│   ├── converter.py     # PDF Conversion Logic
│   └── metrics.py       # Prometheus Metrics
├── tests/
│   ├── __init__.py
│   ├── conftest.py      # Test Fixtures
│   ├── test_api.py      # API Integration Tests
│   ├── test_converter.py # Converter Unit Tests
│   ├── test_metrics.py  # Metrics Tests
│   └── README.md        # Test Documentation
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt # Development Dependencies
├── pyproject.toml       # Tool Configuration (Black, Ruff, Pytest, MyPy)
└── README.md
```

## Testing

### Test Installation

```bash
# Install test dependencies
pip install -r requirements-dev.txt
```

### Run Tests

```bash
# All tests
pytest

# With coverage report
pytest --cov=app --cov-report=html

# Individual test files
pytest tests/test_api.py
pytest tests/test_converter.py
pytest tests/test_metrics.py

# Verbose output
pytest -vv

# Stop on first failure
pytest -x
```

### Direct Commands

```bash
# Tests
pytest                                    # All tests
pytest --cov=app --cov-report=html        # With coverage
pytest -x                                 # Stop on first failure
pytest tests/test_api.py -v               # Only API tests
pytest tests/test_converter.py -v         # Only converter tests
pytest tests/test_metrics.py -v           # Only metrics tests

# Code quality (using pyproject.toml configuration)
ruff check app tests                      # Lint with Ruff
black app tests                           # Format code with Black
mypy app                                  # Type checking

# Coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html  # or xdg-open on Linux
```

### Test Categories

**API Integration Tests (30+ Tests)**
- Health and metrics endpoints
- PDF converter endpoint functionality
- Content-Type validation
- Error handling (400, 413, 415, 422, 500)
- Health check header processing
- Response headers
- Prometheus metrics integration

**Converter Unit Tests (15+ Tests)**
- PDF validation
- Successful conversion
- Error handling
- Logging (INFO/DEBUG)
- Temporary file cleanup

**Metrics Tests (25+ Tests)**
- Metric definitions
- Histogram buckets
- Metric labels
- Prometheus naming conventions
- Integration with app

### Coverage

Target: **> 80% Code Coverage**

```bash
# Coverage report in terminal
pytest --cov=app --cov-report=term-missing

# HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Continuous Integration

For CI/CD pipelines:

```bash
pytest --cov=app --cov-report=xml --junitxml=junit.xml --cov-fail-under=80
```

## Performance

### Conversion Performance

Based on Python module implementation:

| Test | Average Time |
|------|-------------|
| Small PDF (< 1KB) | ~0.52s |
| Medium PDF (100KB) | ~0.75s |
| Large PDF (1MB) | ~1.2s |

**Performance Improvements:**
- Python module: ~0.52s average
- CLI subprocess: ~0.77s average
- **32% faster** with Python module

## References

- [OCRmyPDF Documentation](https://ocrmypdf.readthedocs.io/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [pikepdf Documentation](https://pikepdf.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prometheus Client Python](https://github.com/prometheus/client_python)
