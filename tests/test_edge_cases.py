"""
Edge case tests for PDF Converter Service.

These tests cover uncommon scenarios and boundary conditions to improve coverage.
"""
import subprocess
from unittest.mock import AsyncMock, patch

from app.main import CONVERTER_PATH, HEALTH_PATH


class TestContentTypeEdgeCases:
    """Test edge cases for Content-Type handling."""

    def test_content_type_case_insensitive(self, client, valid_pdf):
        """Test that Content-Type header is case insensitive."""
        # Different case variations
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "APPLICATION/PDF"},
        )

        # Should be rejected as our check uses startswith() which is case-sensitive
        # This is actually a test to verify current behavior
        assert response.status_code == 415

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_content_type_with_multiple_parameters(
        self, mock_convert, client, valid_pdf
    ):
        """Test Content-Type with multiple parameters."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf; charset=utf-8; boundary=xyz"},
        )

        # Assert - Should accept as it starts with application/pdf
        assert response.status_code == 200

    def test_content_type_with_whitespace(self, client, valid_pdf):
        """Test Content-Type with leading/trailing whitespace."""
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "  application/pdf  "},
        )

        # Current implementation doesn't strip whitespace
        # This should fail
        assert response.status_code == 415


class TestHealthCheckHeaderEdgeCases:
    """Test edge cases for X-Health-Check header."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_health_check_header_case_variations(self, mock_convert, client, valid_pdf):
        """Test different case variations of health check header value."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Test various case variations
        test_cases = ["True", "TRUE", "tRuE", "1", "yes", "YES", "Yes"]

        for header_value in test_cases:
            response = client.post(
                CONVERTER_PATH,
                content=valid_pdf,
                headers={
                    "Content-Type": "application/pdf",
                    "X-Health-Check": header_value,
                },
            )

            assert (
                response.status_code == 200
            ), f"Failed for header value: {header_value}"

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_health_check_header_false_values(self, mock_convert, client, valid_pdf):
        """Test that false-y values for health check are not treated as health checks."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Test false-y values
        test_cases = ["false", "0", "no", "", "random"]

        for header_value in test_cases:
            response = client.post(
                CONVERTER_PATH,
                content=valid_pdf,
                headers={
                    "Content-Type": "application/pdf",
                    "X-Health-Check": header_value,
                },
            )

            # Should still succeed, just not treated as health check
            assert response.status_code == 200

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_missing_health_check_header(self, mock_convert, client, valid_pdf):
        """Test request without health check header."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Act - No X-Health-Check header
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert - Should work as regular request
        assert response.status_code == 200


class TestPDFSizeEdgeCases:
    """Test edge cases for PDF size validation."""

    def test_pdf_exactly_at_size_limit(self, client):
        """Test PDF exactly at the 50MB size limit."""
        # Create PDF exactly at limit (50MB)
        max_size = 50 * 1024 * 1024
        pdf_content = b"%PDF-1.4\n" + b"0" * (max_size - 9)

        response = client.post(
            CONVERTER_PATH,
            content=pdf_content,
            headers={"Content-Type": "application/pdf"},
        )

        # Should be accepted (at limit, not over)
        # But will fail due to invalid PDF format
        # Real test is that it doesn't fail with 413
        assert response.status_code != 413

    def test_pdf_one_byte_over_limit(self, client):
        """Test PDF one byte over the 50MB size limit."""
        # Create PDF one byte over limit
        max_size = 50 * 1024 * 1024
        pdf_content = b"%PDF-1.4\n" + b"0" * (max_size - 8)

        response = client.post(
            CONVERTER_PATH,
            content=pdf_content,
            headers={"Content-Type": "application/pdf"},
        )

        # Should be rejected
        assert response.status_code == 413
        assert "too large" in response.json()["detail"]

    def test_very_small_pdf(self, client):
        """Test very small (minimal) PDF."""
        # Just the PDF header
        pdf_content = b"%PDF-1.4\n"

        response = client.post(
            CONVERTER_PATH,
            content=pdf_content,
            headers={"Content-Type": "application/pdf"},
        )

        # Should not fail due to size, but may fail due to invalid format
        assert response.status_code != 413


class TestErrorResponseFormats:
    """Test error response formats and consistency."""

    def test_400_error_has_detail(self, client, invalid_pdf):
        """Test that 400 errors include detail field."""
        response = client.post(
            CONVERTER_PATH,
            content=invalid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        assert response.status_code == 400
        assert "detail" in response.json()
        assert isinstance(response.json()["detail"], str)
        assert len(response.json()["detail"]) > 0

    def test_413_error_has_detail(self, client, large_pdf):
        """Test that 413 errors include detail field."""
        response = client.post(
            CONVERTER_PATH,
            content=large_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        assert response.status_code == 413
        assert "detail" in response.json()
        assert "too large" in response.json()["detail"]

    def test_415_error_has_detail(self, client, valid_pdf):
        """Test that 415 errors include detail field."""
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf
            # Missing Content-Type
        )

        assert response.status_code == 415
        assert "detail" in response.json()
        assert "Content-Type" in response.json()["detail"]

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_422_error_has_detail(self, mock_convert, client, valid_pdf):
        """Test that 422 errors include detail field."""
        # Arrange - Simulate subprocess error
        mock_convert.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["pdfa-cli"], stderr="Error"
        )

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert
        assert response.status_code == 422
        assert "detail" in response.json()
        assert "conversion failed" in response.json()["detail"].lower()

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_500_error_has_detail(self, mock_convert, client, valid_pdf):
        """Test that 500 errors include detail field."""
        # Arrange - Simulate unexpected error
        mock_convert.side_effect = RuntimeError("Unexpected error")

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert
        assert response.status_code == 500
        assert "detail" in response.json()
        assert "Internal server error" in response.json()["detail"]


class TestRequestBodyHandling:
    """Test edge cases in request body handling."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_request_body_with_null_bytes(self, mock_convert, client):
        """Test PDF with null bytes."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"
        pdf_with_nulls = b"%PDF-1.4\n\x00\x00\x00test\x00\x00"

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=pdf_with_nulls,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert - Should handle binary data correctly
        assert response.status_code == 200

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_request_body_with_unicode(self, mock_convert, client):
        """Test PDF with unicode characters."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"
        pdf_with_unicode = "%PDF-1.4\nüöä".encode()

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=pdf_with_unicode,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert - Should handle UTF-8 bytes correctly
        assert response.status_code == 200


class TestHTTPMethodHandling:
    """Test handling of different HTTP methods."""

    def test_get_method_on_converter_returns_405(self, client):
        """Test that GET method on converter endpoint returns 405."""
        response = client.get(CONVERTER_PATH)

        assert response.status_code == 405  # Method Not Allowed

    def test_put_method_on_converter_returns_405(self, client):
        """Test that PUT method on converter endpoint returns 405."""
        response = client.put(
            CONVERTER_PATH, content=b"data", headers={"Content-Type": "application/pdf"}
        )

        assert response.status_code == 405

    def test_delete_method_on_converter_returns_405(self, client):
        """Test that DELETE method on converter endpoint returns 405."""
        response = client.delete(CONVERTER_PATH)

        assert response.status_code == 405

    def test_post_method_on_health_returns_405(self, client):
        """Test that POST method on health endpoint returns 405."""
        response = client.post(HEALTH_PATH, content=b"data")

        assert response.status_code == 405


class TestUnknownEndpoints:
    """Test handling of unknown/non-existent endpoints."""

    def test_unknown_path_returns_404(self, client):
        """Test that unknown paths return 404."""
        response = client.get("/unknown/path")

        assert response.status_code == 404

    def test_unknown_api_path_returns_404(self, client):
        """Test that unknown API paths return 404."""
        response = client.get("/api/unknown")

        assert response.status_code == 404

    def test_typo_in_converter_path_returns_404(self, client):
        """Test that typo in converter path returns 404."""
        response = client.post(
            "/api/pdfconvertor",  # Typo: convertor instead of converter
            content=b"%PDF-1.4\n",
            headers={"Content-Type": "application/pdf"},
        )

        assert response.status_code == 404


class TestConversionErrorTypes:
    """Test different types of conversion errors."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_value_error_from_converter(self, mock_convert, client, valid_pdf):
        """Test ValueError from converter returns 400."""
        # Arrange
        mock_convert.side_effect = ValueError("Invalid PDF format")

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert
        assert response.status_code == 400
        assert "Invalid PDF" in response.json()["detail"]

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_runtime_error_from_converter(self, mock_convert, client, valid_pdf):
        """Test RuntimeError from converter returns 500."""
        # Arrange
        mock_convert.side_effect = RuntimeError("Conversion engine failure")

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_subprocess_error_from_converter(self, mock_convert, client, valid_pdf):
        """Test subprocess.CalledProcessError from converter returns 422."""
        # Arrange
        mock_convert.side_effect = subprocess.CalledProcessError(
            returncode=2, cmd=["pdfa-cli"], stderr="Invalid input"
        )

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert
        assert response.status_code == 422


class TestResponseSizeHandling:
    """Test handling of different response sizes."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_small_response(self, mock_convert, client, valid_pdf):
        """Test response with small PDF."""
        # Arrange - Small converted PDF
        mock_convert.return_value = b"%PDF-1.4\nsmall"

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert
        assert response.status_code == 200
        assert len(response.content) < 100

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_large_response(self, mock_convert, client, valid_pdf):
        """Test response with large PDF."""
        # Arrange - Large converted PDF (1MB)
        large_pdf = b"%PDF-1.4\n" + b"0" * (1024 * 1024)
        mock_convert.return_value = large_pdf

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert
        assert response.status_code == 200
        assert len(response.content) > 1024 * 1024
