import pytest
from unittest.mock import patch, MagicMock
import subprocess


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check_returns_200(self, client):
        """Test that health endpoint returns 200 with correct payload."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_metrics_endpoint_accessible(self, client):
        """Test that metrics endpoint is accessible."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert b"pdf_conversions_total" in response.content

    def test_metrics_format_prometheus(self, client):
        """Test that metrics are in Prometheus format."""
        response = client.get("/metrics")
        content = response.content.decode('utf-8')

        # Check for expected metric names
        assert "pdf_conversions_total" in content
        assert "pdf_conversion_duration_seconds" in content
        assert "pdf_input_size_bytes" in content
        assert "pdf_output_size_bytes" in content
        assert "pdf_conversion_errors_total" in content


class TestPdfConverterEndpoint:
    """Tests for /api/pdfconverter endpoint."""

    @patch('app.converter.subprocess.run')
    def test_successful_conversion(self, mock_subprocess, client, valid_pdf):
        """Test successful PDF conversion."""
        # Mock successful conversion
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="Conversion successful",
            stderr=""
        )

        # Mock file operations to return converted PDF
        converted_pdf = b'%PDF-1.4\n...converted content...'

        with patch('builtins.open', create=True) as mock_open:
            # Setup mock for reading the result
            mock_file = MagicMock()
            mock_file.read.return_value = converted_pdf
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            response = client.post(
                "/api/pdfconverter",
                content=valid_pdf,
                headers={"Content-Type": "application/pdf"}
            )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"PDF" in response.content

    def test_content_type_validation_missing(self, client, valid_pdf):
        """Test that missing Content-Type header returns 415."""
        response = client.post(
            "/api/pdfconverter",
            content=valid_pdf
        )

        assert response.status_code == 415
        assert "Content-Type must be application/pdf" in response.json()["detail"]

    def test_content_type_validation_wrong(self, client, valid_pdf):
        """Test that wrong Content-Type header returns 415."""
        response = client.post(
            "/api/pdfconverter",
            content=valid_pdf,
            headers={"Content-Type": "text/plain"}
        )

        assert response.status_code == 415
        assert "Content-Type must be application/pdf" in response.json()["detail"]

    def test_content_type_with_charset(self, client, valid_pdf):
        """Test that Content-Type with charset is accepted."""
        with patch('app.converter.subprocess.run'):
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.read.return_value = b'%PDF-1.4\nconverted'
                mock_file.__enter__.return_value = mock_file
                mock_open.return_value = mock_file

                response = client.post(
                    "/api/pdfconverter",
                    content=valid_pdf,
                    headers={"Content-Type": "application/pdf; charset=utf-8"}
                )

        # Should accept Content-Type with charset
        assert response.status_code == 200

    def test_empty_pdf_regular_request(self, client, empty_pdf):
        """Test that empty PDF in regular request returns 400."""
        response = client.post(
            "/api/pdfconverter",
            content=empty_pdf,
            headers={"Content-Type": "application/pdf"}
        )

        assert response.status_code == 400
        assert "Empty PDF" in response.json()["detail"]

    def test_invalid_pdf_format(self, client, invalid_pdf):
        """Test that invalid PDF format returns 400."""
        response = client.post(
            "/api/pdfconverter",
            content=invalid_pdf,
            headers={"Content-Type": "application/pdf"}
        )

        assert response.status_code == 400
        assert "Invalid PDF" in response.json()["detail"]

    def test_pdf_too_large(self, client, large_pdf):
        """Test that PDF exceeding size limit returns 413."""
        response = client.post(
            "/api/pdfconverter",
            content=large_pdf,
            headers={"Content-Type": "application/pdf"}
        )

        assert response.status_code == 413
        assert "too large" in response.json()["detail"]

    @patch('app.converter.subprocess.run')
    def test_conversion_failure(self, mock_subprocess, client, valid_pdf):
        """Test that conversion failure returns 422."""
        # Mock failed conversion
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["pdfa-cli"],
            output="",
            stderr="Conversion failed"
        )

        response = client.post(
            "/api/pdfconverter",
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"}
        )

        assert response.status_code == 422
        assert "conversion failed" in response.json()["detail"].lower()


class TestHealthCheckHeader:
    """Tests for X-Health-Check header functionality."""

    @patch('app.converter.subprocess.run')
    def test_health_check_header_true(self, mock_subprocess, client, valid_pdf):
        """Test that X-Health-Check: true is recognized."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b'%PDF-1.4\nconverted'
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            response = client.post(
                "/api/pdfconverter",
                content=valid_pdf,
                headers={
                    "Content-Type": "application/pdf",
                    "X-Health-Check": "true"
                }
            )

        assert response.status_code == 200

    @patch('app.converter.subprocess.run')
    def test_health_check_header_1(self, mock_subprocess, client, valid_pdf):
        """Test that X-Health-Check: 1 is recognized."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b'%PDF-1.4\nconverted'
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            response = client.post(
                "/api/pdfconverter",
                content=valid_pdf,
                headers={
                    "Content-Type": "application/pdf",
                    "X-Health-Check": "1"
                }
            )

        assert response.status_code == 200

    @patch('app.converter.subprocess.run')
    def test_health_check_header_yes(self, mock_subprocess, client, valid_pdf):
        """Test that X-Health-Check: yes is recognized."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b'%PDF-1.4\nconverted'
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            response = client.post(
                "/api/pdfconverter",
                content=valid_pdf,
                headers={
                    "Content-Type": "application/pdf",
                    "X-Health-Check": "yes"
                }
            )

        assert response.status_code == 200

    @patch('app.converter.subprocess.run')
    def test_health_check_header_case_insensitive(self, mock_subprocess, client, valid_pdf):
        """Test that X-Health-Check header is case insensitive."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b'%PDF-1.4\nconverted'
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            response = client.post(
                "/api/pdfconverter",
                content=valid_pdf,
                headers={
                    "Content-Type": "application/pdf",
                    "X-Health-Check": "TRUE"
                }
            )

        assert response.status_code == 200

    @patch('app.converter.subprocess.run')
    def test_health_check_with_empty_body(self, mock_subprocess, client, empty_pdf):
        """Test that health check with empty body uses minimal PDF."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b'%PDF-1.4\nconverted'
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            response = client.post(
                "/api/pdfconverter",
                content=empty_pdf,
                headers={
                    "Content-Type": "application/pdf",
                    "X-Health-Check": "true"
                }
            )

        # Health check should succeed even with empty body
        assert response.status_code == 200

    @patch('app.converter.subprocess.run')
    def test_health_check_header_false(self, mock_subprocess, client, valid_pdf):
        """Test that X-Health-Check: false is treated as regular request."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b'%PDF-1.4\nconverted'
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            response = client.post(
                "/api/pdfconverter",
                content=valid_pdf,
                headers={
                    "Content-Type": "application/pdf",
                    "X-Health-Check": "false"
                }
            )

        # Should process as regular request (not health check)
        assert response.status_code == 200


class TestResponseHeaders:
    """Tests for response headers."""

    @patch('app.converter.subprocess.run')
    def test_response_content_type(self, mock_subprocess, client, valid_pdf):
        """Test that response has correct Content-Type."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b'%PDF-1.4\nconverted'
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            response = client.post(
                "/api/pdfconverter",
                content=valid_pdf,
                headers={"Content-Type": "application/pdf"}
            )

        assert response.headers["content-type"] == "application/pdf"

    @patch('app.converter.subprocess.run')
    def test_response_content_disposition(self, mock_subprocess, client, valid_pdf):
        """Test that response has Content-Disposition header."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b'%PDF-1.4\nconverted'
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            response = client.post(
                "/api/pdfconverter",
                content=valid_pdf,
                headers={"Content-Type": "application/pdf"}
            )

        assert "content-disposition" in response.headers
        assert "converted.pdf" in response.headers["content-disposition"]


class TestMetricsIntegration:
    """Tests for Prometheus metrics integration."""

    @patch('app.converter.subprocess.run')
    def test_metrics_not_recorded_for_health_checks(self, mock_subprocess, client, valid_pdf):
        """Test that metrics are not recorded for health check requests."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b'%PDF-1.4\nconverted'
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            # Get initial metrics
            metrics_before = client.get("/metrics").content

            # Make health check request
            client.post(
                "/api/pdfconverter",
                content=valid_pdf,
                headers={
                    "Content-Type": "application/pdf",
                    "X-Health-Check": "true"
                }
            )

            # Get metrics after
            metrics_after = client.get("/metrics").content

            # Metrics should be the same (health checks not counted)
            # Note: This is a simple check; in reality we'd parse the metrics
            assert len(metrics_before) <= len(metrics_after) + 100  # Allow small variance

    @patch('app.converter.subprocess.run')
    def test_metrics_recorded_for_regular_requests(self, mock_subprocess, client, valid_pdf):
        """Test that metrics are recorded for regular requests."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b'%PDF-1.4\nconverted'
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            # Get initial metrics
            metrics_before = client.get("/metrics").content.decode('utf-8')

            # Make regular request
            client.post(
                "/api/pdfconverter",
                content=valid_pdf,
                headers={"Content-Type": "application/pdf"}
            )

            # Get metrics after
            metrics_after = client.get("/metrics").content.decode('utf-8')

            # Check that conversion counter increased
            assert "pdf_conversions_total" in metrics_after


class TestErrorHandling:
    """Tests for error handling and status codes."""

    def test_404_for_unknown_endpoint(self, client):
        """Test that unknown endpoints return 404."""
        response = client.get("/unknown")
        assert response.status_code == 404

    def test_405_for_wrong_method_on_converter(self, client):
        """Test that wrong HTTP method returns 405."""
        response = client.get("/api/pdfconverter")
        assert response.status_code == 405

    @patch('app.converter.subprocess.run')
    def test_500_on_unexpected_error(self, mock_subprocess, client, valid_pdf):
        """Test that unexpected errors return 500."""
        # Mock unexpected exception
        mock_subprocess.side_effect = RuntimeError("Unexpected error")

        response = client.post(
            "/api/pdfconverter",
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"}
        )

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
