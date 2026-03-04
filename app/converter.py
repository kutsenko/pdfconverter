import asyncio
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import ocrmypdf
import pikepdf

from .converter_config import _config
from .metrics import ACTIVE_CONVERSIONS

logger = logging.getLogger(__name__)

# Bounded Thread Pool (reuses threads, limits concurrency)
_executor = ThreadPoolExecutor(
    max_workers=_config.max_workers, thread_name_prefix="ocr-worker"
)


class PdfType(Enum):
    """PDF content type classification."""

    TEXT_ONLY = "text_only"
    SCANNED_IMAGE = "scanned_image"
    MIXED_CONTENT = "mixed_content"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PdfAnalysis:
    """Result of PDF analysis (type + tagged status)."""

    pdf_type: PdfType
    is_tagged: bool


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


def _count_pdf_images(pdf_path: Path) -> int:
    """Count embedded images in PDF using pikepdf.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Number of images found, or -1 if counting fails
    """
    try:
        with pikepdf.open(pdf_path) as pdf:
            image_count = 0
            for page in pdf.pages:
                if "/Resources" in page and "/XObject" in page.Resources:
                    xobjects = page.Resources.XObject
                    for obj_name in xobjects:  # type: ignore[attr-defined]
                        xobject = xobjects[obj_name]
                        if "/Subtype" in xobject and xobject.Subtype == "/Image":
                            image_count += 1
            return image_count
    except Exception as e:
        logger.warning("Failed to count PDF images: %s", e)
        return -1


def _is_full_page_image_pdf(pdf_path: Path) -> bool:
    """Check if PDF is primarily full-page images (scanned document).

    Heuristic: If >80% of pages have exactly one image, classify as scanned.

    Args:
        pdf_path: Path to PDF file

    Returns:
        True if PDF appears to be a scanned document, False otherwise
    """
    try:
        with pikepdf.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                return False

            full_page_count = 0
            for page in pdf.pages:
                if "/Resources" not in page or "/XObject" not in page.Resources:
                    continue

                xobjects = page.Resources.XObject
                images = [
                    xobjects[n]
                    for n in xobjects  # type: ignore[attr-defined]
                    if "/Subtype" in xobjects[n] and xobjects[n].Subtype == "/Image"
                ]

                if len(images) == 1:
                    full_page_count += 1

            return (full_page_count / len(pdf.pages)) > 0.8
    except Exception as e:
        logger.warning("Failed to analyze PDF pages: %s", e)
        return False


def _detect_pdf_type(pdf_path: Path) -> PdfType:
    """Detect PDF content type for optimization strategy.

    Args:
        pdf_path: Path to PDF file

    Returns:
        PdfType enum indicating the detected content type
    """
    try:
        image_count = _count_pdf_images(pdf_path)

        if image_count < 0:
            return PdfType.UNKNOWN

        if image_count == 0:
            return PdfType.TEXT_ONLY

        if _is_full_page_image_pdf(pdf_path):
            return PdfType.SCANNED_IMAGE
        else:
            return PdfType.MIXED_CONTENT
    except Exception as e:
        logger.warning("PDF type detection failed: %s", e)
        return PdfType.UNKNOWN


def _analyze_pdf(pdf_path: Path) -> PdfAnalysis:
    """Analyze PDF in a single pass: detect type and tagged status.

    Opens the PDF once with pikepdf and extracts all needed information
    (tagged status, image counts, full-page detection) in one traversal.

    Args:
        pdf_path: Path to PDF file

    Returns:
        PdfAnalysis with pdf_type and is_tagged
    """
    try:
        with pikepdf.open(pdf_path) as pdf:
            # Check tagged status
            is_tagged = "/StructTreeRoot" in pdf.Root
            if not is_tagged:
                for page in pdf.pages:
                    if "/StructParents" in page:
                        is_tagged = True
                        break

            # Count images and full-page images in one pass
            num_pages = len(pdf.pages)
            if num_pages == 0:
                return PdfAnalysis(pdf_type=PdfType.UNKNOWN, is_tagged=is_tagged)

            image_count = 0
            full_page_count = 0
            for page in pdf.pages:
                if "/Resources" not in page or "/XObject" not in page.Resources:
                    continue
                xobjects = page.Resources.XObject
                page_image_count = 0
                for obj_name in xobjects:  # type: ignore[attr-defined]
                    xobject = xobjects[obj_name]
                    if "/Subtype" in xobject and xobject.Subtype == "/Image":
                        image_count += 1
                        page_image_count += 1
                if page_image_count == 1:
                    full_page_count += 1

            # Classify PDF type
            if image_count == 0:
                pdf_type = PdfType.TEXT_ONLY
            elif (full_page_count / num_pages) > 0.8:
                pdf_type = PdfType.SCANNED_IMAGE
            else:
                pdf_type = PdfType.MIXED_CONTENT

            return PdfAnalysis(pdf_type=pdf_type, is_tagged=is_tagged)
    except Exception as e:
        logger.warning("PDF analysis failed: %s", e)
        return PdfAnalysis(pdf_type=PdfType.UNKNOWN, is_tagged=False)


def _downgrade_to_pdfa1b(pdf_path: Path) -> None:
    """Downgrade a PDF/A-2 file to PDF/A-1b in place.

    Removes PDF/A-2 only features (transparency groups), sets PDF version
    to 1.4, and updates XMP metadata to declare PDF/A-1b conformance.

    Args:
        pdf_path: Path to PDF/A-2 file (modified in place)
    """
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        for page in pdf.pages:
            if "/Group" in page:
                del page["/Group"]  # type: ignore[operator]

        with pdf.open_metadata() as meta:
            meta["pdfaid:part"] = "1"
            meta["pdfaid:conformance"] = "B"

        pdf.save(pdf_path, min_version="1.4", force_version="1.4")


def _convert_sync(pdf_bytes: bytes, log_level: int) -> bytes:
    """Run the entire conversion pipeline synchronously.

    Designed to run in a thread pool executor so the async event loop
    stays free for new requests. Handles file I/O, PDF analysis,
    OCRmyPDF conversion, and result reading in one call.

    Args:
        pdf_bytes: Input PDF as bytes
        log_level: Logging level (DEBUG for health checks, INFO otherwise)

    Returns:
        Converted PDF/A as bytes

    Raises:
        RuntimeError: If conversion fails
    """
    input_size = len(pdf_bytes)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.pdf"
        output_path = Path(tmpdir) / "output.pdf"

        # Write input PDF and release buffer
        input_path.write_bytes(pdf_bytes)
        del pdf_bytes

        # Analyze PDF: detect type and tagged status (single pikepdf open)
        analysis = _analyze_pdf(input_path)
        pdf_type = analysis.pdf_type
        skip_ocr = analysis.is_tagged
        logger.log(log_level, "Detected PDF type: %s", pdf_type.value)
        if skip_ocr:
            logger.log(log_level, "PDF is tagged, skipping OCR")

        # Get optimization level based on PDF type
        optimize_level = {
            PdfType.TEXT_ONLY: _config.text_only_optimize,
            PdfType.SCANNED_IMAGE: _config.scanned_optimize,
            PdfType.MIXED_CONTENT: _config.mixed_optimize,
            PdfType.UNKNOWN: _config.unknown_optimize,
        }[pdf_type]

        logger.log(
            log_level,
            "Using optimization level %d for %s PDF",
            optimize_level,
            pdf_type.value,
        )

        logger.log(log_level, "Executing OCRmyPDF conversion")

        # Always convert via PDF/A-2 first (Ghostscript rasterizes pages
        # into huge bitmaps when targeting PDF/A-1 directly, causing massive
        # file size inflation and slow conversion times)
        ocrmypdf.ocr(
            input_path,
            output_path,
            language=["deu", "eng"],  # German + English
            output_type="pdfa-2",  # PDF/A-2 standard
            skip_text=skip_ocr,  # Skip OCR on tagged PDFs
            optimize=optimize_level,  # Dynamic optimization based on PDF type
            jobs=_config.ocrmypdf_jobs,  # Parallel page processing
            progress_bar=False,  # No progress bar (not needed in API)
            use_threads=True,  # Enable threading within OCRmyPDF
        )

        # Check if output file was created
        if not output_path.exists():
            raise RuntimeError("Conversion failed: output file not created")

        # Downgrade to PDF/A-1b if requested
        if _config.pdfa_version == 1:
            logger.log(log_level, "Downgrading to PDF/A-1b")
            _downgrade_to_pdfa1b(output_path)

        # Read output PDF
        output_bytes = output_path.read_bytes()

        if not output_bytes:
            raise RuntimeError("Conversion failed: output file is empty")

        # Calculate and log size change
        size_change = len(output_bytes) - input_size
        size_change_pct = (size_change / input_size) * 100

        logger.log(
            log_level,
            "Conversion completed, output=%d bytes (change: %+d bytes, %+.1f%%)",
            len(output_bytes),
            size_change,
            size_change_pct,
        )

        return output_bytes


async def convert_pdf_to_pdfa(pdf_bytes: bytes, is_health_check: bool = False) -> bytes:
    """Convert PDF to PDF/A format using OCRmyPDF directly.

    Validates input, then offloads the entire synchronous pipeline
    (file I/O, PDF analysis, OCRmyPDF conversion) to a thread pool
    executor so the async event loop stays free.

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

    # Track active conversions (skip for health checks to avoid metric noise)
    if not is_health_check:
        ACTIVE_CONVERSIONS.inc()

    try:
        # Run entire conversion pipeline in thread pool
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: _convert_sync(pdf_bytes, log_level),
        )
    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        logger.error("Conversion failed: %s", e, exc_info=True)
        raise RuntimeError(f"PDF conversion failed: {str(e)}") from e
    finally:
        # Decrement active conversions counter (skip for health checks)
        if not is_health_check:
            ACTIVE_CONVERSIONS.dec()
