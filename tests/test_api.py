from unittest.mock import AsyncMock, patch

from app.main import CONVERTER_PATH, HEALTH_PATH, METRICS_PATH


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check_returns_200(self, client):
        """Test that health endpoint returns 200 with correct payload."""
        response = client.get(HEALTH_PATH)
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_metrics_endpoint_accessible(self, client):
        """Test that metrics endpoint is accessible."""
        response = client.get(METRICS_PATH)
        assert response.status_code == 200
        assert b"pdf_conversions" in response.content

    def test_metrics_format_prometheus(self, client):
        """Test that metrics are in Prometheus format."""
        response = client.get(METRICS_PATH)
        content = response.content.decode("utf-8")

        # Check for expected metric names (prometheus adds _total on export)
        assert "pdf_conversions" in content
        assert "pdf_conversion_duration_seconds" in content
        assert "pdf_input_size_bytes" in content
        assert "pdf_output_size_bytes" in content
        assert "pdf_conversion_errors" in content


class TestPdfConverterEndpoint:
    """Tests for /api/pdfconverter endpoint."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_successful_conversion(self, mock_convert, client, valid_pdf):
        """Test successful PDF conversion."""
        converted_pdf = b"%PDF-1.4\n...converted content..."
        mock_convert.return_value = converted_pdf

        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"PDF" in response.content

    def test_content_type_validation_missing(self, client, valid_pdf):
        """Test that missing Content-Type header returns 415."""
        response = client.post(CONVERTER_PATH, content=valid_pdf)

        assert response.status_code == 415
        assert "Content-Type must be application/pdf" in response.json()["detail"]

    def test_content_type_validation_wrong(self, client, valid_pdf):
        """Test that wrong Content-Type header returns 415."""
        response = client.post(
            CONVERTER_PATH, content=valid_pdf, headers={"Content-Type": "text/plain"}
        )

        assert response.status_code == 415
        assert "Content-Type must be application/pdf" in response.json()["detail"]

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_content_type_with_charset(self, mock_convert, client, valid_pdf):
        """Test that Content-Type with charset is accepted."""
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf; charset=utf-8"},
        )

        assert response.status_code == 200

    def test_empty_pdf_regular_request(self, client, empty_pdf):
        """Test that empty PDF in regular request returns 400."""
        response = client.post(
            CONVERTER_PATH,
            content=empty_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        assert response.status_code == 400
        assert "Empty PDF" in response.json()["detail"]

    def test_invalid_pdf_format(self, client, invalid_pdf):
        """Test that invalid PDF format returns 400."""
        response = client.post(
            CONVERTER_PATH,
            content=invalid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        assert response.status_code == 400
        assert "Invalid PDF" in response.json()["detail"]

    def test_pdf_too_large(self, client, large_pdf):
        """Test that PDF exceeding size limit returns 413."""
        response = client.post(
            CONVERTER_PATH,
            content=large_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        assert response.status_code == 413
        assert "too large" in response.json()["detail"]

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_conversion_failure(self, mock_convert, client, valid_pdf):
        """Test that conversion failure returns 422."""
        mock_convert.side_effect = RuntimeError("PDF conversion failed: OCR error")

        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        assert response.status_code == 422
        assert "conversion failed" in response.json()["detail"].lower()


class TestHealthCheckHeader:
    """Tests for X-Health-Check header functionality."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_health_check_header_true(self, mock_convert, client, valid_pdf):
        """Test that X-Health-Check: true is recognized."""
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf", "X-Health-Check": "true"},
        )

        assert response.status_code == 200

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_health_check_header_1(self, mock_convert, client, valid_pdf):
        """Test that X-Health-Check: 1 is recognized."""
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf", "X-Health-Check": "1"},
        )

        assert response.status_code == 200

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_health_check_header_case_insensitive(
        self, mock_convert, client, valid_pdf
    ):
        """Test that X-Health-Check header is case insensitive."""
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf", "X-Health-Check": "TRUE"},
        )

        assert response.status_code == 200

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_health_check_with_empty_body(self, mock_convert, client, empty_pdf):
        """Test that health check with empty body uses minimal PDF."""
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        response = client.post(
            CONVERTER_PATH,
            content=empty_pdf,
            headers={"Content-Type": "application/pdf", "X-Health-Check": "true"},
        )

        # Health check should succeed even with empty body
        assert response.status_code == 200


class TestResponseHeaders:
    """Tests for response headers."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_response_content_type(self, mock_convert, client, valid_pdf):
        """Test that response has correct Content-Type."""
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        assert response.headers["content-type"] == "application/pdf"

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_response_content_disposition(self, mock_convert, client, valid_pdf):
        """Test that response has Content-Disposition header."""
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        assert "content-disposition" in response.headers
        assert "converted.pdf" in response.headers["content-disposition"]


class TestErrorHandling:
    """Tests for error handling and status codes."""

    def test_404_for_unknown_endpoint(self, client):
        """Test that unknown endpoints return 404."""
        response = client.get("/unknown")
        assert response.status_code == 404

    def test_405_for_wrong_method_on_converter(self, client):
        """Test that wrong HTTP method returns 405."""
        response = client.get(CONVERTER_PATH)
        assert response.status_code == 405

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_500_on_unexpected_error(self, mock_convert, client, valid_pdf):
        """Test that unexpected errors return 500."""
        # Use Exception (not RuntimeError) for unexpected errors
        mock_convert.side_effect = Exception("Unexpected error")

        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
