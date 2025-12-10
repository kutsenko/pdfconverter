import asyncio
import logging
import tempfile
from pathlib import Path

import ocrmypdf
import pikepdf

logger = logging.getLogger(__name__)


def _is_pdf_tagged(pdf_path: Path) -> bool:
    """Check if PDF is already tagged (has structural tags).

    Tagged PDFs already have text layer and don't need OCR.

    Args:
        pdf_path: Path to PDF file

    Returns:
        True if PDF is tagged, False otherwise
    """
    try:
        with pikepdf.open(pdf_path) as pdf:
            # Check if PDF has StructTreeRoot (indicates tagged PDF)
            if "/StructTreeRoot" in pdf.Root:
                return True

            # Alternative check: if any page has marked content
            for page in pdf.pages:
                if "/StructParents" in page:
                    return True

        return False
    except Exception as e:
        logger.warning("Failed to check PDF tags: %s", e)
        return False


async def convert_pdf_to_pdfa(pdf_bytes: bytes, is_health_check: bool = False) -> bytes:
    """Convert PDF to PDF/A format using OCRmyPDF directly.

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
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("Not a valid PDF file")

    # Log conversion start
    log_level = logging.DEBUG if is_health_check else logging.INFO
    logger.log(log_level, "Starting PDF conversion, size=%d bytes", len(pdf_bytes))

    try:
        # Create temporary directory for conversion
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.pdf"
            output_path = Path(tmpdir) / "output.pdf"

            # Write input PDF
            input_path.write_bytes(pdf_bytes)

            # Check if PDF is already tagged (skip OCR if true)
            skip_ocr = _is_pdf_tagged(input_path)
            if skip_ocr:
                logger.log(log_level, "PDF is tagged, skipping OCR")

            logger.log(log_level, "Executing OCRmyPDF conversion")

            # Run conversion in thread pool to avoid blocking the event loop
            # OCRmyPDF is a synchronous function
            await asyncio.to_thread(
                ocrmypdf.ocr,
                input_file=input_path,
                output_file=output_path,
                language="deu+eng",  # German + English
                output_type="pdfa-2",  # PDF/A-2 standard
                skip_text=skip_ocr,  # Skip OCR on tagged PDFs
                optimize=0,  # No optimization (faster)
                jobs=1,  # Single thread (sufficient for single-document API)
                progress_bar=False,  # No progress bar (not needed in API)
                use_threads=True,  # Enable threading within OCRmyPDF
            )

            # Check if output file was created
            if not output_path.exists():
                raise RuntimeError("Conversion failed: output file not created")

            # Read output PDF
            output_bytes = output_path.read_bytes()

            if not output_bytes:
                raise RuntimeError("Conversion failed: output file is empty")

            logger.log(
                log_level,
                "Conversion completed, output size=%d bytes",
                len(output_bytes),
            )

            return output_bytes

    except Exception as e:
        logger.error("Conversion failed: %s", e, exc_info=True)
        raise RuntimeError(f"PDF conversion failed: {str(e)}")
