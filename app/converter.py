import logging
import os
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


async def convert_pdf_to_pdfa(
    pdf_bytes: bytes,
    is_health_check: bool = False
) -> bytes:
    """
    Convert PDF to PDF/A format using pdfa-cli.

    Args:
        pdf_bytes: Input PDF as bytes
        is_health_check: Whether this is a health check request

    Returns:
        Converted PDF/A as bytes

    Raises:
        ValueError: If PDF is invalid or empty
        subprocess.CalledProcessError: If conversion fails
        RuntimeError: If conversion fails for other reasons
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
        # Create temporary directory for conversion
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.pdf")
            output_path = os.path.join(tmpdir, "output.pdf")

            # Write input PDF
            with open(input_path, 'wb') as f:
                f.write(pdf_bytes)

            # Call pdfa-cli
            # Note: Using default settings for maximum compatibility
            # The tool will automatically detect if text exists and handle appropriately
            cmd = [
                "pdfa-cli",
                input_path,
                output_path,
                "--pdfa-level", "2"
            ]

            logger.log(log_level, "Executing pdfa-cli command")

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            # Log subprocess output at DEBUG level
            if result.stdout:
                logger.debug("pdfa-cli stdout: %s", result.stdout)

            # Check if output file was created
            if not os.path.exists(output_path):
                raise RuntimeError("Conversion failed: output file not created")

            # Read output PDF
            with open(output_path, 'rb') as f:
                output_bytes = f.read()

            if not output_bytes:
                raise RuntimeError("Conversion failed: output file is empty")

            logger.log(log_level, "Conversion completed, output size=%d bytes", len(output_bytes))

            return output_bytes

    except subprocess.CalledProcessError as e:
        error_msg = f"pdfa-cli failed with exit code {e.returncode}"
        if e.stderr:
            error_msg += f": {e.stderr}"
        logger.error(error_msg)
        raise subprocess.CalledProcessError(
            e.returncode,
            e.cmd,
            e.output,
            e.stderr
        )
    except Exception as e:
        logger.error("Unexpected error during conversion: %s", e, exc_info=True)
        raise
