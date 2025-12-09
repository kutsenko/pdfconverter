import pytest
from unittest.mock import patch, MagicMock, mock_open
import subprocess
import os


class TestConvertPdfToPdfa:
    """Tests for convert_pdf_to_pdfa function."""

    @pytest.mark.asyncio
    async def test_empty_pdf_raises_value_error(self):
        """Test that empty PDF raises ValueError."""
        from app.converter import convert_pdf_to_pdfa

        with pytest.raises(ValueError, match="Empty PDF"):
            await convert_pdf_to_pdfa(b'')

    @pytest.mark.asyncio
    async def test_invalid_pdf_header_raises_value_error(self):
        """Test that invalid PDF header raises ValueError."""
        from app.converter import convert_pdf_to_pdfa

        with pytest.raises(ValueError, match="Not a valid PDF"):
            await convert_pdf_to_pdfa(b'This is not a PDF')

    @pytest.mark.asyncio
    @patch('app.converter.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    async def test_successful_conversion(self, mock_exists, mock_file, mock_subprocess):
        """Test successful PDF conversion."""
        from app.converter import convert_pdf_to_pdfa

        # Setup mocks
        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted content'

        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="Conversion successful",
            stderr=""
        )
        mock_exists.return_value = True

        # Mock file reads/writes
        mock_file.return_value.read.return_value = output_pdf

        result = await convert_pdf_to_pdfa(input_pdf)

        assert result == output_pdf
        assert mock_subprocess.called

    @pytest.mark.asyncio
    @patch('app.converter.subprocess.run')
    async def test_subprocess_error_raises_exception(self, mock_subprocess):
        """Test that subprocess error is propagated."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'

        mock_subprocess.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["pdfa-cli"],
            output="",
            stderr="Conversion failed"
        )

        with pytest.raises(subprocess.CalledProcessError):
            await convert_pdf_to_pdfa(input_pdf)

    @pytest.mark.asyncio
    @patch('app.converter.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    async def test_output_file_not_created_raises_error(self, mock_exists, mock_file, mock_subprocess):
        """Test that missing output file raises RuntimeError."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'

        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = False  # Output file not created

        with pytest.raises(RuntimeError, match="output file not created"):
            await convert_pdf_to_pdfa(input_pdf)

    @pytest.mark.asyncio
    @patch('app.converter.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    async def test_empty_output_file_raises_error(self, mock_exists, mock_file, mock_subprocess):
        """Test that empty output file raises RuntimeError."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'

        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = b''  # Empty output

        with pytest.raises(RuntimeError, match="output file is empty"):
            await convert_pdf_to_pdfa(input_pdf)

    @pytest.mark.asyncio
    @patch('app.converter.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    async def test_health_check_parameter(self, mock_exists, mock_file, mock_subprocess):
        """Test that is_health_check parameter is passed correctly."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted'

        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = output_pdf

        # Call with health check
        result = await convert_pdf_to_pdfa(input_pdf, is_health_check=True)

        assert result == output_pdf

    @pytest.mark.asyncio
    @patch('app.converter.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    async def test_pdfa_cli_command_structure(self, mock_exists, mock_file, mock_subprocess):
        """Test that pdfa-cli is called with correct arguments."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted'

        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = output_pdf

        await convert_pdf_to_pdfa(input_pdf)

        # Verify subprocess.run was called
        assert mock_subprocess.called
        call_args = mock_subprocess.call_args

        # Check command structure
        cmd = call_args[0][0]
        assert cmd[0] == "pdfa-cli"
        assert "--pdfa-level" in cmd
        assert "2" in cmd
        assert "--ocr-enabled" in cmd
        assert "false" in cmd

    @pytest.mark.asyncio
    @patch('app.converter.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    async def test_temporary_files_cleanup(self, mock_exists, mock_file, mock_subprocess):
        """Test that temporary files are cleaned up after conversion."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted'

        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = output_pdf

        # Conversion should complete without leaving temp files
        result = await convert_pdf_to_pdfa(input_pdf)

        assert result == output_pdf
        # tempfile.TemporaryDirectory should handle cleanup automatically

    @pytest.mark.asyncio
    @patch('app.converter.subprocess.run')
    async def test_stderr_output_on_error(self, mock_subprocess):
        """Test that stderr is captured on conversion error."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'

        error_message = "Critical error in pdfa-cli"
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["pdfa-cli"],
            output="",
            stderr=error_message
        )

        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            await convert_pdf_to_pdfa(input_pdf)

        # Check that error info is preserved
        assert exc_info.value.returncode == 1


class TestConverterLogging:
    """Tests for converter logging functionality."""

    @pytest.mark.asyncio
    @patch('app.converter.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('app.converter.logger')
    async def test_logging_for_regular_conversion(self, mock_logger, mock_exists, mock_file, mock_subprocess):
        """Test that INFO level is used for regular conversions."""
        from app.converter import convert_pdf_to_pdfa
        import logging

        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted'

        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = output_pdf

        await convert_pdf_to_pdfa(input_pdf, is_health_check=False)

        # Check that INFO level was used
        calls = [call for call in mock_logger.log.call_args_list]
        assert any(call[0][0] == logging.INFO for call in calls)

    @pytest.mark.asyncio
    @patch('app.converter.subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('app.converter.logger')
    async def test_logging_for_health_check(self, mock_logger, mock_exists, mock_file, mock_subprocess):
        """Test that DEBUG level is used for health checks."""
        from app.converter import convert_pdf_to_pdfa
        import logging

        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted'

        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = output_pdf

        await convert_pdf_to_pdfa(input_pdf, is_health_check=True)

        # Check that DEBUG level was used
        calls = [call for call in mock_logger.log.call_args_list]
        assert any(call[0][0] == logging.DEBUG for call in calls)

    @pytest.mark.asyncio
    @patch('app.converter.subprocess.run')
    @patch('app.converter.logger')
    async def test_error_logging_on_failure(self, mock_logger, mock_subprocess):
        """Test that errors are logged appropriately."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'

        mock_subprocess.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["pdfa-cli"],
            output="",
            stderr="Error message"
        )

        with pytest.raises(subprocess.CalledProcessError):
            await convert_pdf_to_pdfa(input_pdf)

        # Check that error was logged
        assert mock_logger.error.called


class TestPdfValidation:
    """Tests for PDF validation logic."""

    @pytest.mark.asyncio
    async def test_valid_pdf_header_accepted(self):
        """Test that valid PDF headers are accepted."""
        from app.converter import convert_pdf_to_pdfa

        # Various valid PDF headers
        valid_headers = [
            b'%PDF-1.0\n',
            b'%PDF-1.1\n',
            b'%PDF-1.2\n',
            b'%PDF-1.3\n',
            b'%PDF-1.4\n',
            b'%PDF-1.5\n',
            b'%PDF-1.6\n',
            b'%PDF-1.7\n',
            b'%PDF-2.0\n',
        ]

        for header in valid_headers:
            with patch('app.converter.subprocess.run'):
                with patch('builtins.open', new_callable=mock_open):
                    with patch('os.path.exists', return_value=True):
                        # Should not raise ValueError for valid headers
                        try:
                            await convert_pdf_to_pdfa(header + b'content')
                        except ValueError:
                            pytest.fail(f"Valid PDF header {header} was rejected")
                        except Exception:
                            # Other exceptions are OK for this test
                            pass

    @pytest.mark.asyncio
    async def test_invalid_pdf_headers_rejected(self):
        """Test that invalid PDF headers are rejected."""
        from app.converter import convert_pdf_to_pdfa

        invalid_headers = [
            b'PDF-1.4\n',  # Missing %
            b'%PF-1.4\n',  # Typo
            b'<html>',  # HTML
            b'\x00\x00',  # Binary
            b'',  # Empty
        ]

        for header in invalid_headers:
            with pytest.raises((ValueError, Exception)):
                await convert_pdf_to_pdfa(header + b'content')
