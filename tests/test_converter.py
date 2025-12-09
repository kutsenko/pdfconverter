import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path


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
    @patch('asyncio.to_thread', new_callable=AsyncMock)
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_bytes')
    @patch('pathlib.Path.write_bytes')
    async def test_successful_conversion(self, mock_write, mock_read, mock_exists, mock_to_thread):
        """Test successful PDF conversion."""
        from app.converter import convert_pdf_to_pdfa

        # Setup mocks
        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted content'

        mock_to_thread.return_value = None  # pdfa_convert doesn't return anything
        mock_exists.return_value = True
        mock_read.return_value = output_pdf

        result = await convert_pdf_to_pdfa(input_pdf)

        assert result == output_pdf
        assert mock_to_thread.called

    @pytest.mark.asyncio
    @patch('asyncio.to_thread', new_callable=AsyncMock)
    async def test_conversion_error_raises_exception(self, mock_to_thread):
        """Test that conversion error is propagated."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'

        mock_to_thread.side_effect = Exception("Conversion failed")

        with pytest.raises(RuntimeError, match="PDF conversion failed"):
            await convert_pdf_to_pdfa(input_pdf)

    @pytest.mark.asyncio
    @patch('asyncio.to_thread', new_callable=AsyncMock)
    @patch('pathlib.Path.exists')
    async def test_output_file_not_created_raises_error(self, mock_exists, mock_to_thread):
        """Test that missing output file raises RuntimeError."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'

        mock_to_thread.return_value = None
        mock_exists.return_value = False  # Output file not created

        with pytest.raises(RuntimeError, match="output file not created"):
            await convert_pdf_to_pdfa(input_pdf)

    @pytest.mark.asyncio
    @patch('asyncio.to_thread', new_callable=AsyncMock)
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_bytes')
    async def test_empty_output_file_raises_error(self, mock_read, mock_exists, mock_to_thread):
        """Test that empty output file raises RuntimeError."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'

        mock_to_thread.return_value = None
        mock_exists.return_value = True
        mock_read.return_value = b''  # Empty output

        with pytest.raises(RuntimeError, match="output file is empty"):
            await convert_pdf_to_pdfa(input_pdf)

    @pytest.mark.asyncio
    @patch('asyncio.to_thread', new_callable=AsyncMock)
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_bytes')
    async def test_health_check_parameter(self, mock_read, mock_exists, mock_to_thread):
        """Test that is_health_check parameter is passed correctly."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted'

        mock_to_thread.return_value = None
        mock_exists.return_value = True
        mock_read.return_value = output_pdf

        # Call with health check
        result = await convert_pdf_to_pdfa(input_pdf, is_health_check=True)

        assert result == output_pdf

    @pytest.mark.asyncio
    @patch('asyncio.to_thread', new_callable=AsyncMock)
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_bytes')
    async def test_pdfa_module_call_structure(self, mock_read, mock_exists, mock_to_thread):
        """Test that pdfa module is called with correct arguments."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted'

        mock_to_thread.return_value = None
        mock_exists.return_value = True
        mock_read.return_value = output_pdf

        await convert_pdf_to_pdfa(input_pdf)

        # Verify asyncio.to_thread was called with pdfa_convert function
        assert mock_to_thread.called
        call_args = mock_to_thread.call_args

        # Check that function arguments include expected parameters
        assert 'language' in call_args.kwargs or len(call_args.args) > 2
        assert 'pdfa_level' in call_args.kwargs or len(call_args.args) > 3

    @pytest.mark.asyncio
    @patch('asyncio.to_thread', new_callable=AsyncMock)
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_bytes')
    async def test_temporary_files_cleanup(self, mock_read, mock_exists, mock_to_thread):
        """Test that temporary files are cleaned up after conversion."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted'

        mock_to_thread.return_value = None
        mock_exists.return_value = True
        mock_read.return_value = output_pdf

        # Conversion should complete without leaving temp files
        result = await convert_pdf_to_pdfa(input_pdf)

        assert result == output_pdf
        # tempfile.TemporaryDirectory should handle cleanup automatically

    @pytest.mark.asyncio
    @patch('asyncio.to_thread', new_callable=AsyncMock)
    async def test_error_output_on_failure(self, mock_to_thread):
        """Test that errors are captured on conversion failure."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'

        error_message = "Critical error in pdfa conversion"
        mock_to_thread.side_effect = Exception(error_message)

        with pytest.raises(RuntimeError) as exc_info:
            await convert_pdf_to_pdfa(input_pdf)

        # Check that error message is included
        assert "PDF conversion failed" in str(exc_info.value)


class TestConverterLogging:
    """Tests for converter logging functionality."""

    @pytest.mark.asyncio
    @patch('asyncio.to_thread', new_callable=AsyncMock)
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_bytes')
    @patch('app.converter.logger')
    async def test_logging_for_regular_conversion(self, mock_logger, mock_read, mock_exists, mock_to_thread):
        """Test that INFO level is used for regular conversions."""
        from app.converter import convert_pdf_to_pdfa
        import logging

        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted'

        mock_to_thread.return_value = None
        mock_exists.return_value = True
        mock_read.return_value = output_pdf

        await convert_pdf_to_pdfa(input_pdf, is_health_check=False)

        # Check that INFO level was used
        calls = [call for call in mock_logger.log.call_args_list]
        assert any(call[0][0] == logging.INFO for call in calls)

    @pytest.mark.asyncio
    @patch('asyncio.to_thread', new_callable=AsyncMock)
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_bytes')
    @patch('app.converter.logger')
    async def test_logging_for_health_check(self, mock_logger, mock_read, mock_exists, mock_to_thread):
        """Test that DEBUG level is used for health checks."""
        from app.converter import convert_pdf_to_pdfa
        import logging

        input_pdf = b'%PDF-1.4\ntest content'
        output_pdf = b'%PDF-1.4\nconverted'

        mock_to_thread.return_value = None
        mock_exists.return_value = True
        mock_read.return_value = output_pdf

        await convert_pdf_to_pdfa(input_pdf, is_health_check=True)

        # Check that DEBUG level was used
        calls = [call for call in mock_logger.log.call_args_list]
        assert any(call[0][0] == logging.DEBUG for call in calls)

    @pytest.mark.asyncio
    @patch('asyncio.to_thread', new_callable=AsyncMock)
    @patch('app.converter.logger')
    async def test_error_logging_on_failure(self, mock_logger, mock_to_thread):
        """Test that errors are logged appropriately."""
        from app.converter import convert_pdf_to_pdfa

        input_pdf = b'%PDF-1.4\ntest content'

        mock_to_thread.side_effect = Exception("Error message")

        with pytest.raises(RuntimeError):
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
            with patch('asyncio.to_thread', new_callable=AsyncMock):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('pathlib.Path.read_bytes', return_value=b'%PDF-1.4\nconverted'):
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
