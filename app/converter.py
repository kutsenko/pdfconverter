import asyncio
import io
import logging
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import ocrmypdf
import pikepdf
from fontTools.cffLib import CFFFontSet
from fontTools.ttLib import TTFont

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


_PDF14_MAX_REAL = 32767.0
_REAL_PATTERN = re.compile(r"(?<![a-zA-Z/])(-?\d+\.?\d*)")


def _clamp_real(match: re.Match[str]) -> str:
    """Clamp a real number to PDF 1.4 limits."""
    val = float(match.group(0))
    if val > _PDF14_MAX_REAL:
        return str(_PDF14_MAX_REAL)
    if val < -_PDF14_MAX_REAL:
        return str(-_PDF14_MAX_REAL)
    return match.group(0)


def _clamp_outside_strings(data: str) -> str:
    """Clamp real values to PDF 1.4 limits, skipping PDF string literals.

    PDF string literals are enclosed in parentheses and may contain
    numbers (like ISBNs) that should NOT be clamped.
    """
    result: list[str] = []
    i = 0
    length = len(data)
    while i < length:
        if data[i] == "(":
            # Find matching close paren, handling nesting and escapes
            depth = 1
            j = i + 1
            while j < length and depth > 0:
                if data[j] == "\\" and j + 1 < length:
                    j += 2
                    continue
                if data[j] == "(":
                    depth += 1
                elif data[j] == ")":
                    depth -= 1
                j += 1
            result.append(data[i:j])  # Keep string literal unchanged
            i = j
        else:
            # Find next string literal
            next_paren = data.find("(", i)
            if next_paren == -1:
                next_paren = length
            segment = data[i:next_paren]
            result.append(_REAL_PATTERN.sub(_clamp_real, segment))
            i = next_paren
    return "".join(result)


def _clamp_content_stream(pdf: pikepdf.Pdf, page: pikepdf.Page) -> None:
    """Clamp real values in a page's content stream to PDF 1.4 limits.

    PDF 1.4 (required for PDF/A-1) restricts real values to [-32767, 32767].
    Ghostscript may produce coordinates outside this range during conversion.
    Numbers inside PDF string literals (parentheses) are not clamped.

    Args:
        pdf: The owning PDF (needed to create replacement streams)
        page: The page whose content stream to clamp
    """
    contents = page.get("/Contents")
    if contents is None:
        return

    data = contents.read_bytes().decode("latin-1")
    new_data = _clamp_outside_strings(data)
    if new_data != data:
        page.Contents = pdf.make_stream(new_data.encode("latin-1"))


def _remove_cmyk_group(obj: object) -> bool:
    """Remove CMYK transparency group from a PDF dictionary object.

    Returns True if the object was modified.
    """
    if "/Group" not in obj:  # type: ignore[operator]
        return False
    group = obj.Group  # type: ignore[attr-defined]
    if "/CS" in group and str(group.CS) == "/DeviceCMYK":
        del obj["/Group"]  # type: ignore[attr-defined]
        return True
    return False


def _fix_cff_font_widths(font: pikepdf.Object) -> bool:
    """Fix width mismatches between CFF font programs and PDF font dictionaries.

    Ghostscript may copy raw charstring widths into the Widths array without
    accounting for a non-standard FontMatrix. When the CFF FontMatrix scale
    differs from the standard 0.001, all PDF Widths entries need to be
    multiplied by (FontMatrix[0] / 0.001).

    Returns True if any widths were corrected.
    """
    if str(font.get("/Subtype", "")) != "/Type1":  # type: ignore[call-overload]
        return False
    fd = font.get("/FontDescriptor")
    if not fd or "/FontFile3" not in fd:
        return False
    ff3 = fd["/FontFile3"]
    if str(ff3.get("/Subtype", "")) != "/Type1C":  # type: ignore[call-overload]
        return False
    if "/Widths" not in font:
        return False

    try:
        cff_data = ff3.read_bytes()
        cff = CFFFontSet()
        cff.decompile(io.BytesIO(cff_data), None)
        top = cff.topDictIndex[0]

        fm = getattr(top, "FontMatrix", None)
        if fm is None or abs(fm[0] - 0.001) < 1e-8:
            return False  # Standard matrix, no correction needed

        scale = fm[0] / 0.001  # e.g. 0.0004883/0.001 = 0.4883

        # Scale all widths by the FontMatrix ratio
        widths = list(font.Widths)  # type: ignore[call-overload]
        new_widths = []
        for w in widths:
            scaled = round(float(w) * scale)
            new_widths.append(pikepdf.Object.parse(str(scaled).encode()))

        font["/Widths"] = pikepdf.Array(new_widths)
        logger.debug(
            "Fixed CFF font widths: scale=%.4f, %d entries", scale, len(new_widths)
        )
        return True
    except Exception as e:
        logger.debug("CFF font width fix skipped: %s", e)
        return False


def _fix_truetype_widths(font: pikepdf.Object) -> bool:
    """Fix zero-width entries in TrueType font Widths arrays.

    Ghostscript sometimes sets Widths to 0 for glyphs that exist in
    the TrueType font program. This reads the hmtx table and fills
    in the correct widths.

    Returns True if any widths were corrected.
    """
    if str(font.get("/Subtype", "")) != "/TrueType":  # type: ignore[call-overload]
        return False
    fd = font.get("/FontDescriptor")
    if not fd or "/FontFile2" not in fd:
        return False
    if "/Widths" not in font or "/FirstChar" not in font:
        return False

    try:
        ff2_data = fd["/FontFile2"].read_bytes()
        ttf = TTFont(io.BytesIO(ff2_data))
        cmap = ttf.getBestCmap()
        hmtx = ttf["hmtx"]
        units_per_em = ttf["head"].unitsPerEm

        first_char = int(font.FirstChar)
        widths = list(font.Widths)  # type: ignore[call-overload]
        corrected = False

        for i, w in enumerate(widths):
            if int(w) != 0:
                continue
            char_code = first_char + i
            glyph_name = cmap.get(char_code)
            if glyph_name and glyph_name in hmtx.metrics:
                actual_w = round(hmtx[glyph_name][0] * 1000 / units_per_em)
                if actual_w > 0:
                    widths[i] = pikepdf.Object.parse(str(actual_w).encode())
                    corrected = True

        if corrected:
            font["/Widths"] = pikepdf.Array(widths)
            logger.debug("Fixed TrueType font zero-widths")
        ttf.close()
        return corrected
    except Exception as e:
        logger.debug("TrueType font width fix skipped: %s", e)
        return False


def _get_used_char_codes(
    page: object,
) -> dict[str, set[int]]:
    """Extract character codes used by each font on a page.

    Parses the content stream to find Tf (set font) and Tj/TJ (show text)
    operators, returning a map of font resource name to used char codes.
    """
    result: dict[str, set[int]] = {}
    try:
        commands = pikepdf.parse_content_stream(page)  # type: ignore[arg-type]
    except Exception:
        return result

    current_font = ""
    for instruction in commands:
        operands = instruction.operands
        op = str(instruction.operator)
        if op == "Tf" and operands:
            current_font = str(operands[0])
        elif op == "Tj" and current_font and operands:
            text_bytes = bytes(operands[0])
            codes = result.setdefault(current_font, set())
            codes.update(text_bytes)
        elif op == "TJ" and current_font and operands:
            codes = result.setdefault(current_font, set())
            for item in list(operands[0]):  # type: ignore[call-overload]
                try:
                    text_bytes = bytes(item)
                    if text_bytes:
                        codes.update(text_bytes)
                except (TypeError, ValueError):
                    pass
    return result


def _fix_cff_missing_glyphs(
    font: pikepdf.Object,
    used_codes: set[int],
) -> bool:
    """Add missing glyph charstrings to CFF font subsets.

    Ghostscript sometimes creates font subsets that don't include all glyphs
    referenced in the content stream. This adds minimal empty charstrings
    for missing glyphs so veraPDF doesn't flag them.

    Only processes char codes that are actually used on the page.

    Returns True if any glyphs were added.
    """
    if str(font.get("/Subtype", "")) != "/Type1":  # type: ignore[call-overload]
        return False
    fd = font.get("/FontDescriptor")
    if not fd or "/FontFile3" not in fd:
        return False
    ff3 = fd["/FontFile3"]
    if str(ff3.get("/Subtype", "")) != "/Type1C":  # type: ignore[call-overload]
        return False
    if "/Widths" not in font or "/FirstChar" not in font:
        return False

    try:
        # Build char_code -> glyph_name map from encoding
        code_to_name: dict[int, str] = {}
        encoding = font.get("/Encoding")

        if encoding is not None and str(encoding) == "/WinAnsiEncoding":
            from fontTools.agl import UV2AGL

            for cc in used_codes:
                name = UV2AGL.get(cc)
                if name:
                    code_to_name[cc] = name
        elif encoding is not None and hasattr(encoding, "keys"):
            if "/Differences" in encoding:
                differences = list(
                    encoding["/Differences"]
                )  # type: ignore[call-overload]
                ec = 0
                for entry in differences:
                    if isinstance(entry, (int, pikepdf.Object)) and not isinstance(
                        entry, pikepdf.Name
                    ):
                        ec = int(entry)
                    else:
                        if ec in used_codes:
                            code_to_name[ec] = str(entry)[1:]
                        ec += 1
        else:
            return False

        cff_data = ff3.read_bytes()
        cff = CFFFontSet()
        cff.decompile(io.BytesIO(cff_data), None)
        top = cff.topDictIndex[0]
        cs = top.CharStrings

        first_char = int(font.FirstChar)
        added = False

        for char_code in used_codes:
            idx = char_code - first_char
            if idx < 0:
                continue
            glyph_name = code_to_name.get(char_code)
            if not glyph_name or glyph_name in cs:
                continue

            from fontTools.misc.psCharStrings import T2CharString

            empty_cs = T2CharString()
            empty_cs.program = ["endchar"]
            new_idx = len(cs.charStringsIndex)
            cs.charStringsIndex.append(empty_cs)
            cs.charStrings[glyph_name] = new_idx
            top.charset.append(glyph_name)
            added = True
            logger.debug("Added missing glyph '%s' to CFF font", glyph_name)

        if added:
            from unittest.mock import Mock as _Mock

            mock_font = _Mock()
            mock_font.recalcBBoxes = False
            buf = io.BytesIO()
            cff.compile(buf, mock_font)
            ff3.write(buf.getvalue())

        return added
    except Exception as e:
        logger.debug("CFF missing glyph fix skipped: %s", e)
        return False


def _sanitize_pdfa(pdf_path: Path) -> None:
    """Fix common PDF/A compliance issues left by Ghostscript.

    - Removes CMYK transparency groups from pages and XObjects
    - Removes annotations without appearance dictionaries (required by PDF/A)
    - Fixes CFF font width mismatches caused by non-standard FontMatrix
    - Fixes TrueType font zero-width entries using hmtx data
    - Adds missing glyph charstrings to CFF font subsets

    Args:
        pdf_path: Path to PDF file (modified in place)
    """
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        modified = False
        for page in pdf.pages:
            # Remove CMYK transparency groups from page
            if _remove_cmyk_group(page):
                modified = True

            # Remove CMYK transparency groups from Form XObjects
            if "/Resources" in page and "/XObject" in page.Resources:
                xobjects = page.Resources.XObject
                for name in xobjects:  # type: ignore[attr-defined]
                    xobj = xobjects[name]
                    if _remove_cmyk_group(xobj):
                        modified = True

            # Remove annotations without appearance dictionaries
            if "/Annots" in page:
                annots = list(page.Annots)  # type: ignore[call-overload]
                clean = [a for a in annots if "/AP" in a]
                if len(clean) < len(annots):
                    modified = True
                    if clean:
                        page["/Annots"] = pikepdf.Array(clean)
                    else:
                        del page["/Annots"]  # type: ignore[operator]

            # Fix font issues (widths, missing glyphs)
            if "/Resources" in page and "/Font" in page.Resources:
                fonts = page.Resources.Font
                used_codes = _get_used_char_codes(page)
                for fname in fonts:  # type: ignore[attr-defined]
                    f = fonts[fname]
                    if _fix_cff_font_widths(f):
                        modified = True
                    if _fix_truetype_widths(f):
                        modified = True
                    font_codes = used_codes.get(fname, set())
                    if font_codes and _fix_cff_missing_glyphs(f, font_codes):
                        modified = True

        if modified:
            pdf.save(pdf_path)


def _downgrade_to_pdfa1b(pdf_path: Path) -> None:
    """Downgrade a PDF/A-2 file to PDF/A-1b in place.

    Applies all changes needed for PDF/A-1b conformance:
    - Removes transparency groups (not allowed in PDF/A-1)
    - Removes SMask entries from XObjects (soft masks not in PDF/A-1)
    - Forces alpha values to 1.0 in ExtGState (transparency not in PDF/A-1)
    - Adds CIDSet streams to CIDFont descriptors (required by PDF/A-1)
    - Clamps real values in content streams to PDF 1.4 limit (32767)
    - Sets PDF version to 1.4 and updates XMP metadata

    Args:
        pdf_path: Path to PDF/A-2 file (modified in place)
    """
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        for page in pdf.pages:
            # Remove all transparency groups (not just CMYK ones)
            if "/Group" in page:
                del page["/Group"]  # type: ignore[operator]

            # Clamp out-of-range real values in content stream
            # PDF 1.4 limits real values to [-32767, 32767]
            _clamp_content_stream(pdf, page)

            if "/Resources" not in page:
                continue
            resources = page.Resources

            # Remove SMask from XObjects (soft masks not allowed in PDF/A-1)
            if "/XObject" in resources:
                xobjects = resources.XObject
                for name in xobjects:  # type: ignore[attr-defined]
                    xobj = xobjects[name]
                    if "/SMask" in xobj:
                        del xobj["/SMask"]

            # Force alpha values to 1.0 (transparency not allowed in PDF/A-1)
            if "/ExtGState" in resources:
                ext_gstates = resources.ExtGState
                for gsname in ext_gstates:  # type: ignore[attr-defined]
                    gs = ext_gstates[gsname]
                    if "/ca" in gs:
                        gs["/ca"] = pikepdf.Object.parse(b"1.0")
                    if "/CA" in gs:
                        gs["/CA"] = pikepdf.Object.parse(b"1.0")

            # Process fonts
            if "/Font" in resources:
                fonts = resources.Font
                for fname in fonts:  # type: ignore[attr-defined]
                    font = fonts[fname]

                    # Clamp Type 3 font CharProcs (glyph content streams)
                    if "/CharProcs" in font:
                        charprocs = font.CharProcs
                        for cpname in charprocs:  # type: ignore[attr-defined]
                            stream = charprocs[cpname]
                            data = stream.read_bytes().decode("latin-1")
                            new_data = _REAL_PATTERN.sub(_clamp_real, data)
                            if new_data != data:
                                charprocs[cpname] = pdf.make_stream(
                                    new_data.encode("latin-1")
                                )

                    # Add CIDSet to CIDFont descriptors (required by PDF/A-1)
                    if "/DescendantFonts" not in font:
                        continue
                    for desc_font in font.DescendantFonts:  # type: ignore[attr-defined]
                        fd = desc_font.get("/FontDescriptor")
                        has_font = "/FontFile2" in fd or "/FontFile3" in fd
                        if fd and "/CIDSet" not in fd and has_font:
                            # Mark all CIDs as present (conservative but valid)
                            cidset_data = b"\xff" * 8192
                            fd["/CIDSet"] = pdf.make_stream(cidset_data)

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
        logger.log(log_level, "Detected PDF type: %s", pdf_type.value)
        if analysis.is_tagged:
            logger.log(log_level, "PDF is tagged")

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
            skip_text=True,  # Skip pages that already have text
            optimize=optimize_level,  # Dynamic optimization based on PDF type
            jobs=_config.ocrmypdf_jobs,  # Parallel page processing
            progress_bar=False,  # No progress bar (not needed in API)
            use_threads=True,  # Enable threading within OCRmyPDF
            color_conversion_strategy="RGB",  # Ensure PDF/A color compliance
        )

        # Check if output file was created
        if not output_path.exists():
            raise RuntimeError("Conversion failed: output file not created")

        # Fix common PDF/A compliance issues (e.g. CMYK transparency groups)
        _sanitize_pdfa(output_path)

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
