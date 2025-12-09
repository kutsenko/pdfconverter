import logging
import os
import subprocess
import time
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import Response as FastAPIResponse
from prometheus_client import make_asgi_app

from .converter import convert_pdf_to_pdfa
from .metrics import (
    REQUEST_COUNT,
    CONVERSION_DURATION,
    INPUT_SIZE,
    OUTPUT_SIZE,
    CONVERSION_ERRORS
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB
MINIMAL_PDF = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj xref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\ntrailer<</Size 3/Root 1 0 R>>startxref\n110\n%%EOF'

# Configurable endpoint paths via environment variables
HEALTH_PATH = os.getenv("HEALTH_PATH", "/health")
METRICS_PATH = os.getenv("METRICS_PATH", "/metrics")
CONVERTER_PATH = os.getenv("CONVERTER_PATH", "/api/pdfconverter")

# Create FastAPI app
app = FastAPI(
    title="PDF Converter Service",
    version="1.0.0",
    description="REST API for converting PDF to PDF/A format"
)


def is_health_check(request: Request) -> bool:
    """
    Check if request is a health check based on X-Health-Check header.

    Args:
        request: FastAPI Request object

    Returns:
        True if this is a health check request, False otherwise
    """
    header_value = request.headers.get("x-health-check", "").lower()
    return header_value in ("true", "1", "yes")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """
    Middleware to collect Prometheus metrics.

    Only records metrics for non-health-check requests.
    """
    # Check if this is a health check
    is_hc = is_health_check(request)

    # Only track metrics for conversion endpoint
    if request.url.path == CONVERTER_PATH:
        start_time = time.time()

        # Store request size for metrics
        request_size = 0

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Record metrics ONLY for non-health-check requests
            if not is_hc:
                REQUEST_COUNT.labels(status=response.status_code).inc()
                CONVERSION_DURATION.observe(duration)

                # Get request and response sizes from state if available
                if hasattr(request.state, 'input_size'):
                    INPUT_SIZE.observe(request.state.input_size)
                if hasattr(request.state, 'output_size'):
                    OUTPUT_SIZE.observe(request.state.output_size)

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Record error metrics ONLY for non-health-check requests
            if not is_hc:
                error_type = type(e).__name__
                CONVERSION_ERRORS.labels(error_type=error_type).inc()

                # Determine status code
                status_code = 500
                if isinstance(e, HTTPException):
                    status_code = e.status_code

                REQUEST_COUNT.labels(status=status_code).inc()

            raise
    else:
        # For non-conversion endpoints, just pass through
        response = await call_next(request)
        return response


async def health():
    """
    Basic health check endpoint.

    Returns:
        Simple status message
    """
    return {"status": "healthy"}


async def convert_pdf_endpoint(request: Request):
    """
    Convert PDF to PDF/A format.

    This endpoint accepts a PDF file as raw bytes in the request body
    and returns the converted PDF/A file.

    Headers:
        Content-Type: application/pdf (required)
        X-Health-Check: true/false (optional) - If true, logs at DEBUG level

    Returns:
        Converted PDF/A file as application/pdf

    Raises:
        HTTPException: Various HTTP errors for different failure scenarios
    """
    # Parse health check header
    is_hc = is_health_check(request)

    # Set logging level based on health check
    log_level = logging.DEBUG if is_hc else logging.INFO
    log_type = "HEALTHCHECK" if is_hc else "conversion"

    logger.log(log_level, "begin %s", log_type)

    try:
        # Validate Content-Type
        content_type = request.headers.get("content-type", "")
        if not content_type.startswith("application/pdf"):
            logger.warning("Invalid Content-Type: %s", content_type)
            raise HTTPException(
                status_code=415,
                detail="Content-Type must be application/pdf"
            )

        # Read request body
        try:
            pdf_bytes = await request.body()
        except Exception as e:
            logger.error("Failed to read request body: %s", e)
            raise HTTPException(
                status_code=400,
                detail="Failed to read request body"
            )

        # Handle empty body for health checks
        if len(pdf_bytes) == 0:
            if is_hc:
                # Use minimal PDF for health checks
                logger.debug("Using minimal PDF for health check")
                pdf_bytes = MINIMAL_PDF
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Empty PDF file"
                )

        # Validate size
        if len(pdf_bytes) > MAX_PDF_SIZE:
            logger.warning("PDF too large: %d bytes", len(pdf_bytes))
            raise HTTPException(
                status_code=413,
                detail=f"PDF file too large (max {MAX_PDF_SIZE} bytes)"
            )

        # Store input size in request state for metrics
        request.state.input_size = len(pdf_bytes)

        logger.log(log_level, "Converting PDF, input size: %d bytes", len(pdf_bytes))

        # Convert PDF
        try:
            output_bytes = await convert_pdf_to_pdfa(pdf_bytes, is_health_check=is_hc)
        except ValueError as e:
            # Invalid PDF format
            logger.warning("Invalid PDF: %s", e)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid PDF: {str(e)}"
            )
        except subprocess.CalledProcessError as e:
            # Conversion failed
            logger.error("Conversion failed: %s", e)
            raise HTTPException(
                status_code=422,
                detail="PDF conversion failed"
            )
        except Exception as e:
            # Unexpected error
            logger.exception("Unexpected error during conversion")
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )

        # Store output size in request state for metrics
        request.state.output_size = len(output_bytes)

        logger.log(log_level, "completed %s success", log_type)

        # Return PDF
        return Response(
            content=output_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'inline; filename="converted.pdf"'
            }
        )

    except HTTPException:
        # Re-raise HTTPExceptions
        logger.log(log_level, "completed %s error", log_type)
        raise
    except Exception as e:
        # Catch any other exceptions
        logger.log(log_level, "completed %s error", log_type)
        logger.exception("Unexpected error in endpoint")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


# Register routes with configurable paths
app.add_api_route(HEALTH_PATH, health, methods=["GET"], tags=["health"])
app.add_api_route(CONVERTER_PATH, convert_pdf_endpoint, methods=["POST"], tags=["converter"])

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount(METRICS_PATH, metrics_app)

# Log configured paths
logger.info("Configured endpoints:")
logger.info(f"  Health Check: {HEALTH_PATH}")
logger.info(f"  PDF Converter: {CONVERTER_PATH}")
logger.info(f"  Metrics: {METRICS_PATH}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
