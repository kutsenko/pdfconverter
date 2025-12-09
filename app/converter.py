import asyncio
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


async def convert_pdf_to_pdfa(
    pdf_bytes: bytes,
    is_health_check: bool = False
) -> bytes:
    """
    Convert PDF to PDF/A format using pdfa Python module directly.

    Args:
        pdf_bytes: Input PDF as bytes
        is_health_check: Whether this is a health check request

    Returns:
        Converted PDF/A as bytes

    Raises:
        ValueError: If PDF is invalid or empty
        RuntimeError: If conversion fails
    """
    if not pdf_bytes:
        raise ValueError("Empty PDF file")

    # Validate PDF header
    if not pdf_bytes.startswith(b'%PDF'):
        raise ValueError("Not a valid PDF file")

    # Log conversion start
    log_level = logging.DEBUG if is_health_check else logging.INFO
    logger.log(log_level, "Starting PDF conversion, size=%d bytes", len(pdf_bytes))

    try:
        # Import pdfa module (done inside function to handle import errors gracefully)
        from pdfa.converter import convert_to_pdfa as pdfa_convert

        # Create temporary directory for conversion
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.pdf"
            output_path = Path(tmpdir) / "output.pdf"

            # Write input PDF
            input_path.write_bytes(pdf_bytes)

            logger.log(log_level, "Executing pdfa conversion via Python module")

            # Run conversion in thread pool to avoid blocking the event loop
            # The pdfa.converter.convert_to_pdfa is a synchronous function
            await asyncio.to_thread(
                pdfa_convert,
                input_pdf=input_path,
                output_pdf=output_path,
                language="deu+eng",
                pdfa_level="2",
                ocr_enabled=True,  # Enable OCR but skip on tagged PDFs (default behavior)
                skip_ocr_on_tagged_pdfs=True  # Skip OCR if PDF already has text
            )

            # Check if output file was created
            if not output_path.exists():
                raise RuntimeError("Conversion failed: output file not created")

            # Read output PDF
            output_bytes = output_path.read_bytes()

            if not output_bytes:
                raise RuntimeError("Conversion failed: output file is empty")

            logger.log(log_level, "Conversion completed, output size=%d bytes", len(output_bytes))

            return output_bytes

    except ImportError as e:
        logger.error("Failed to import pdfa module: %s", e)
        raise RuntimeError(f"pdfa module not available: {e}")
    except Exception as e:
        logger.error("Conversion failed: %s", e, exc_info=True)
        raise RuntimeError(f"PDF conversion failed: {str(e)}")
