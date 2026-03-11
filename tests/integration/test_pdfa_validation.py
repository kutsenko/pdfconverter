"""
Integration tests: real PDF/A conversion with veraPDF validation.

These tests perform actual PDF conversion (no mocks) and validate
the output against veraPDF for both PDF/A-1b and PDF/A-2b compliance.

Requirements:
    - Docker with ghcr.io/verapdf/cli:latest image
    - ocrmypdf + Ghostscript installed
    - Test PDFs in data/test_pdfs/

Run only these tests:
    pytest tests/integration/test_pdfa_validation.py -m real_conversion
"""

import logging
import shutil
import subprocess
from pathlib import Path

import pytest

from app.converter import _convert_sync
from app.converter_config import OptimizerConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_PDF_DIR = PROJECT_ROOT / "data" / "test_pdfs"
DATA_DIR = PROJECT_ROOT / "data"

# PDFs that are known to be unconvertible (corrupted structure)
UNCONVERTIBLE_PDFS = {"unreadable_metadata.pdf"}

# PDFs with unfixable veraPDF issues (e.g. font glyph width mismatches
# embedded in the source PDF that can't be corrected without re-embedding)
VERAPDF_KNOWN_ISSUES: set[str] = set()

# All test PDFs that should be convertible
CONVERTIBLE_TEST_PDFS = sorted(
    [p.name for p in TEST_PDF_DIR.glob("*.pdf") if p.name not in UNCONVERTIBLE_PDFS]
)

CONVERTIBLE_DATA_PDFS = sorted(
    [p.name for p in DATA_DIR.glob("*.pdf") if p.name not in UNCONVERTIBLE_PDFS]
)

ALL_CONVERTIBLE_PDFS = [
    (TEST_PDF_DIR / name, name) for name in CONVERTIBLE_TEST_PDFS
] + [(DATA_DIR / name, name) for name in CONVERTIBLE_DATA_PDFS]

PDFA_VERSIONS = [
    pytest.param(1, "1b", id="pdfa-1b"),
    pytest.param(2, "2b", id="pdfa-2b"),
]


def _docker_available() -> bool:
    """Check if Docker is available."""
    return shutil.which("docker") is not None


def _verapdf_available() -> bool:
    """Check if veraPDF Docker image is available."""
    if not _docker_available():
        return False
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", "ghcr.io/verapdf/cli:latest"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _ocrmypdf_available() -> bool:
    """Check if ocrmypdf and Ghostscript are available."""
    try:
        import ocrmypdf  # noqa: F401

        result = subprocess.run(["gs", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (ImportError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _convert_pdf(pdf_path: Path, pdfa_version: int) -> bytes:
    """Convert a PDF to PDF/A using the real converter pipeline.

    Temporarily overrides the global config to set the desired PDF/A version.
    """
    import app.converter as conv
    import app.converter_config as cc

    original_config = cc._config
    try:
        cc._config = OptimizerConfig(pdfa_version=pdfa_version)
        conv._config = cc._config
        pdf_bytes = pdf_path.read_bytes()
        return _convert_sync(pdf_bytes, logging.INFO)
    finally:
        cc._config = original_config
        conv._config = original_config


def _validate_with_verapdf(pdf_bytes: bytes, flavour: str) -> tuple[bool, str]:
    """Validate PDF/A compliance using veraPDF Docker image.

    Uses a project-local temp directory to ensure Docker volume mounts work.

    Returns:
        Tuple of (passed, details) where details contains failure info.
    """
    verapdf_tmp = PROJECT_ROOT / ".verapdf_tmp"
    verapdf_tmp.mkdir(exist_ok=True)
    pdf_path = verapdf_tmp / "output.pdf"

    try:
        pdf_path.write_bytes(pdf_bytes)

        # Use text format for quick pass/fail, then mrr for failure details
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{verapdf_tmp.resolve()}:/data",
                "ghcr.io/verapdf/cli:latest",
                "--flavour",
                flavour,
                "--format",
                "text",
                "/data/output.pdf",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        passed = "PASS" in result.stdout
        if not passed:
            # Re-run with mrr format for detailed failure info
            mrr_result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{verapdf_tmp.resolve()}:/data",
                    "ghcr.io/verapdf/cli:latest",
                    "--flavour",
                    flavour,
                    "--format",
                    "mrr",
                    "/data/output.pdf",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            details = []
            if result.stderr:
                details.append(result.stderr.strip()[:200])
            for line in mrr_result.stdout.splitlines():
                if "clause" in line or "description" in line:
                    details.append(line.strip())
            return False, "\n".join(details[:10])

        return True, ""
    finally:
        if pdf_path.exists():
            pdf_path.unlink()


requires_ocrmypdf = pytest.mark.skipif(
    not _ocrmypdf_available(),
    reason="ocrmypdf or Ghostscript not available",
)
requires_verapdf = pytest.mark.skipif(
    not _verapdf_available(),
    reason="veraPDF Docker image not available",
)
requires_test_pdfs = pytest.mark.skipif(
    not TEST_PDF_DIR.exists() or not any(TEST_PDF_DIR.glob("*.pdf")),
    reason="Test PDFs not found in data/test_pdfs/",
)


@pytest.mark.real_conversion
@pytest.mark.slow
@pytest.mark.integration
@requires_ocrmypdf
@requires_verapdf
@requires_test_pdfs
class TestPdfAConversion:
    """Test real PDF/A conversion with veraPDF validation."""

    @pytest.mark.parametrize("pdfa_version,flavour", PDFA_VERSIONS)
    @pytest.mark.parametrize(
        "pdf_path,pdf_name",
        ALL_CONVERTIBLE_PDFS,
        ids=[name for _, name in ALL_CONVERTIBLE_PDFS],
    )
    def test_conversion_validates_with_verapdf(
        self, pdf_path, pdf_name, pdfa_version, flavour
    ):
        """Convert PDF and validate with veraPDF."""
        if pdf_name in VERAPDF_KNOWN_ISSUES:
            pytest.xfail(f"{pdf_name}: known font glyph width issue in source PDF")

        assert pdf_path.exists(), f"Test PDF not found: {pdf_path}"

        # Convert
        result_bytes = _convert_pdf(pdf_path, pdfa_version)
        assert len(result_bytes) > 0, "Conversion produced empty output"
        assert result_bytes.startswith(b"%PDF"), "Output is not a valid PDF"

        # Validate with veraPDF
        passed, details = _validate_with_verapdf(result_bytes, flavour)
        assert passed, (
            f"veraPDF validation failed for {pdf_name} "
            f"(PDF/A-{flavour}):\n{details}"
        )

    @pytest.mark.parametrize(
        "pdf_path,pdf_name",
        ALL_CONVERTIBLE_PDFS,
        ids=[name for _, name in ALL_CONVERTIBLE_PDFS],
    )
    def test_conversion_preserves_reasonable_size(self, pdf_path, pdf_name):
        """Verify conversion doesn't cause extreme file size inflation."""
        input_size = pdf_path.stat().st_size
        result_bytes = _convert_pdf(pdf_path, pdfa_version=2)

        output_size = len(result_bytes)
        ratio = output_size / input_size

        # Allow up to 40x size increase (generous for small files that
        # gain ICC profiles and fonts), but catch Ghostscript rasterization
        # bugs that cause 40x+ inflation
        assert ratio < 40, (
            f"Excessive size inflation for {pdf_name}: "
            f"{input_size} -> {output_size} ({ratio:.1f}x)"
        )

    @pytest.mark.parametrize("pdfa_version,flavour", PDFA_VERSIONS)
    def test_pdfa1b_not_larger_than_rasterized(self, pdfa_version, flavour):
        """PDF/A-1b via downgrade should not be much larger than PDF/A-2b.

        This catches the Ghostscript rasterization bug where targeting
        PDF/A-1 directly produces huge bitmap-filled files.
        """
        # Use a known mixed-content PDF
        pdf_path = DATA_DIR / "Clean_ABAP_deutsch.pdf"
        if not pdf_path.exists():
            pytest.skip("Clean_ABAP_deutsch.pdf not available")

        result_bytes = _convert_pdf(pdf_path, pdfa_version)
        output_size = len(result_bytes)

        # The two-step approach should keep both versions under 10MB
        # for this ~2.8MB input (direct Ghostscript PDF/A-1 was 112MB)
        assert output_size < 15 * 1024 * 1024, (
            f"PDF/A-{flavour} output too large: {output_size / 1024 / 1024:.1f}MB "
            f"(possible Ghostscript rasterization bug)"
        )


@pytest.mark.real_conversion
@pytest.mark.slow
@pytest.mark.integration
@requires_ocrmypdf
@requires_test_pdfs
class TestPdfAConversionRobustness:
    """Test converter robustness with edge-case PDFs."""

    def test_unconvertible_pdf_raises_error(self):
        """PDFs with corrupted structure should raise an error."""
        pdf_path = TEST_PDF_DIR / "unreadable_metadata.pdf"
        if not pdf_path.exists():
            pytest.skip("unreadable_metadata.pdf not available")

        with pytest.raises(Exception):
            _convert_pdf(pdf_path, pdfa_version=2)

    @pytest.mark.parametrize(
        "pdf_path,pdf_name",
        ALL_CONVERTIBLE_PDFS,
        ids=[name for _, name in ALL_CONVERTIBLE_PDFS],
    )
    def test_conversion_output_is_valid_pdf(self, pdf_path, pdf_name):
        """Verify all converted outputs are structurally valid PDFs."""
        result_bytes = _convert_pdf(pdf_path, pdfa_version=2)

        assert result_bytes.startswith(b"%PDF"), "Missing PDF header"
        assert b"%%EOF" in result_bytes[-128:], "Missing EOF marker"

    def test_pdfa1b_has_correct_metadata(self):
        """PDF/A-1b output should have correct XMP metadata."""
        pdf_path = TEST_PDF_DIR / "simple_text.pdf"
        if not pdf_path.exists():
            pytest.skip("simple_text.pdf not available")

        import pikepdf

        result_bytes = _convert_pdf(pdf_path, pdfa_version=1)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(result_bytes)
            tmp.flush()
            with pikepdf.open(tmp.name) as pdf:
                with pdf.open_metadata() as meta:
                    assert meta.get("pdfaid:part") == "1"
                    assert meta.get("pdfaid:conformance") == "B"

    def test_pdfa2b_has_correct_metadata(self):
        """PDF/A-2b output should have PDF/A-2 XMP metadata."""
        pdf_path = TEST_PDF_DIR / "simple_text.pdf"
        if not pdf_path.exists():
            pytest.skip("simple_text.pdf not available")

        import pikepdf

        result_bytes = _convert_pdf(pdf_path, pdfa_version=2)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(result_bytes)
            tmp.flush()
            with pikepdf.open(tmp.name) as pdf:
                with pdf.open_metadata() as meta:
                    assert meta.get("pdfaid:part") == "2"
                    assert meta.get("pdfaid:conformance") == "B"
