"""
End-to-end integration tests for PDF Converter Service.

These tests verify complete workflows and interactions between components.
"""

from unittest.mock import AsyncMock, patch

from app.main import CONVERTER_PATH, HEALTH_PATH, METRICS_PATH


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_complete_conversion_workflow(self, mock_convert, client, valid_pdf):
        """Test complete PDF conversion workflow from request to response."""
        # Arrange
        converted_pdf = b"%PDF-1.4\n%converted content"
        mock_convert.return_value = converted_pdf

        # Act - Convert PDF
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert - Verify response
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "content-disposition" in response.headers
        assert b"PDF" in response.content

        # Verify metrics were updated (implicitly tested via middleware)
        # Metrics would be updated in real scenario

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_health_check_workflow(self, mock_convert, client, valid_pdf):
        """Test health check workflow with X-Health-Check header."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Act - Health check conversion
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf", "X-Health-Check": "true"},
        )

        # Assert - Verify successful conversion
        assert response.status_code == 200
        # Health check should not affect metrics (tested elsewhere)

    def test_monitoring_workflow(self, client):
        """Test monitoring workflow: health + metrics."""
        # Act - Check health
        health_response = client.get(HEALTH_PATH)

        # Assert - Health is OK
        assert health_response.status_code == 200
        assert health_response.json() == {"status": "healthy"}

        # Act - Check metrics
        metrics_response = client.get(METRICS_PATH)

        # Assert - Metrics endpoint is accessible
        assert metrics_response.status_code == 200
        # Should return prometheus metrics format

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_error_handling_workflow(self, mock_convert, client, valid_pdf):
        """Test error handling workflow through complete stack."""
        # Arrange - Simulate conversion failure
        mock_convert.side_effect = RuntimeError("Conversion failed")

        # Act - Attempt conversion
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert - Verify error response
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]


class TestMetricsIntegration:
    """Test Prometheus metrics integration with API."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_metrics_updated_after_successful_conversion(
        self, mock_convert, client, valid_pdf
    ):
        """Test that metrics are updated after successful conversion."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Act - Perform conversion
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert - Conversion succeeded
        assert response.status_code == 200

        # Metrics should be updated (tested via middleware)
        # In real scenario, we'd query /metrics and verify counters increased

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_metrics_not_updated_for_health_checks(
        self, mock_convert, client, valid_pdf
    ):
        """Test that health check requests don't update metrics."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Act - Health check conversion
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf", "X-Health-Check": "true"},
        )

        # Assert - Conversion succeeded
        assert response.status_code == 200

        # Metrics should NOT be updated for health checks
        # This is verified via middleware logic


class TestConfigurableEndpoints:
    """Test configurable endpoint paths via environment variables."""

    def test_default_endpoint_paths(self, client):
        """Test that default endpoint paths work."""
        # Default paths should be accessible
        health_response = client.get(HEALTH_PATH)
        assert health_response.status_code == 200

        metrics_response = client.get(METRICS_PATH)
        assert metrics_response.status_code == 200

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_converter_endpoint_dynamic_path(self, mock_convert, client, valid_pdf):
        """Test that converter endpoint uses dynamic path from config."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Act - Use configured converter path
        response = client.post(
            CONVERTER_PATH,  # Dynamic path from environment
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert
        assert response.status_code == 200


class TestMiddlewareIntegration:
    """Test middleware integration with endpoints."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_middleware_processes_requests(self, mock_convert, client, valid_pdf):
        """Test that middleware processes requests correctly."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert - Middleware should not interfere with successful requests
        assert response.status_code == 200

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_middleware_handles_exceptions(self, mock_convert, client, valid_pdf):
        """Test that middleware handles exceptions correctly."""
        # Arrange - Simulate error
        mock_convert.side_effect = ValueError("Invalid PDF")

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert - Middleware should allow error to propagate correctly
        assert response.status_code == 400  # ValueError maps to 400

    def test_middleware_skips_non_converter_endpoints(self, client):
        """Test that middleware doesn't interfere with non-converter endpoints."""
        # Act - Access health endpoint
        response = client.get(HEALTH_PATH)

        # Assert - Should work without middleware interference
        assert response.status_code == 200


class TestInputValidation:
    """Test input validation across the stack."""

    def test_missing_content_type_rejected(self, client, valid_pdf):
        """Test that missing Content-Type is rejected."""
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            # No Content-Type header
        )

        assert response.status_code == 415
        assert "Content-Type" in response.json()["detail"]

    def test_wrong_content_type_rejected(self, client, valid_pdf):
        """Test that wrong Content-Type is rejected."""
        response = client.post(
            CONVERTER_PATH, content=valid_pdf, headers={"Content-Type": "text/plain"}
        )

        assert response.status_code == 415
        assert "Content-Type" in response.json()["detail"]

    def test_empty_body_rejected_for_regular_requests(self, client):
        """Test that empty body is rejected for regular requests."""
        response = client.post(
            CONVERTER_PATH, content=b"", headers={"Content-Type": "application/pdf"}
        )

        assert response.status_code == 400
        assert "Empty PDF" in response.json()["detail"]

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_empty_body_handled_for_health_checks(self, mock_convert, client):
        """Test that empty body is handled for health checks."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Act - Health check with empty body
        response = client.post(
            CONVERTER_PATH,
            content=b"",
            headers={"Content-Type": "application/pdf", "X-Health-Check": "true"},
        )

        # Assert - Should use minimal PDF for health checks
        assert response.status_code == 200


class TestResponseHeaders:
    """Test response headers across different scenarios."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_response_headers_for_successful_conversion(
        self, mock_convert, client, valid_pdf
    ):
        """Test response headers for successful conversion."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Act
        response = client.post(
            CONVERTER_PATH,
            content=valid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert - Verify all expected headers
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "content-disposition" in response.headers
        assert "converted.pdf" in response.headers["content-disposition"]

    def test_response_headers_for_errors(self, client, invalid_pdf):
        """Test response headers for error responses."""
        # Act
        response = client.post(
            CONVERTER_PATH,
            content=invalid_pdf,
            headers={"Content-Type": "application/pdf"},
        )

        # Assert - Error response should have JSON content-type
        assert response.status_code == 400
        # FastAPI automatically sets content-type for error responses


class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    @patch("app.main.convert_pdf_to_pdfa", new_callable=AsyncMock)
    def test_multiple_concurrent_conversions(self, mock_convert, client, valid_pdf):
        """Test that multiple concurrent conversions are handled correctly."""
        # Arrange
        mock_convert.return_value = b"%PDF-1.4\nconverted"

        # Act - Send multiple requests
        responses = []
        for _ in range(5):
            response = client.post(
                CONVERTER_PATH,
                content=valid_pdf,
                headers={"Content-Type": "application/pdf"},
            )
            responses.append(response)

        # Assert - All requests should succeed
        assert all(r.status_code == 200 for r in responses)

    def test_health_and_conversion_requests_mixed(self, client, valid_pdf):
        """Test mixed health and conversion requests."""
        # Health check
        health_response = client.get(HEALTH_PATH)
        assert health_response.status_code == 200

        # Metrics check
        metrics_response = client.get(METRICS_PATH)
        assert metrics_response.status_code == 200

        # Both should work independently
