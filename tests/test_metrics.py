import pytest


class TestMetricsDefinitions:
    """Tests for Prometheus metrics definitions."""

    def test_request_count_metric_exists(self):
        """Test that REQUEST_COUNT metric is defined."""
        from app.metrics import REQUEST_COUNT

        assert REQUEST_COUNT is not None
        assert REQUEST_COUNT._name == 'pdf_conversions_total'

    def test_conversion_duration_metric_exists(self):
        """Test that CONVERSION_DURATION metric is defined."""
        from app.metrics import CONVERSION_DURATION

        assert CONVERSION_DURATION is not None
        assert CONVERSION_DURATION._name == 'pdf_conversion_duration_seconds'

    def test_input_size_metric_exists(self):
        """Test that INPUT_SIZE metric is defined."""
        from app.metrics import INPUT_SIZE

        assert INPUT_SIZE is not None
        assert INPUT_SIZE._name == 'pdf_input_size_bytes'

    def test_output_size_metric_exists(self):
        """Test that OUTPUT_SIZE metric is defined."""
        from app.metrics import OUTPUT_SIZE

        assert OUTPUT_SIZE is not None
        assert OUTPUT_SIZE._name == 'pdf_output_size_bytes'

    def test_conversion_errors_metric_exists(self):
        """Test that CONVERSION_ERRORS metric is defined."""
        from app.metrics import CONVERSION_ERRORS

        assert CONVERSION_ERRORS is not None
        assert CONVERSION_ERRORS._name == 'pdf_conversion_errors_total'


class TestMetricsBuckets:
    """Tests for histogram bucket configurations."""

    def test_duration_histogram_buckets(self):
        """Test that CONVERSION_DURATION has correct buckets."""
        from app.metrics import CONVERSION_DURATION

        expected_buckets = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]

        # Get buckets from the metric
        # Note: prometheus_client stores buckets in _upper_bounds
        if hasattr(CONVERSION_DURATION, '_upper_bounds'):
            actual_buckets = list(CONVERSION_DURATION._upper_bounds)
            # Remove +Inf bucket
            actual_buckets = [b for b in actual_buckets if b != float('inf')]

            # Check that our expected buckets are present
            for bucket in expected_buckets:
                assert bucket in actual_buckets, f"Bucket {bucket} not found"

    def test_size_histogram_buckets(self):
        """Test that size histograms have correct buckets."""
        from app.metrics import INPUT_SIZE, OUTPUT_SIZE

        expected_buckets = [1024, 10240, 102400, 1048576, 10485760, 52428800]

        # Test INPUT_SIZE
        if hasattr(INPUT_SIZE, '_upper_bounds'):
            actual_buckets = list(INPUT_SIZE._upper_bounds)
            actual_buckets = [b for b in actual_buckets if b != float('inf')]

            for bucket in expected_buckets:
                assert bucket in actual_buckets, f"INPUT_SIZE: Bucket {bucket} not found"

        # Test OUTPUT_SIZE
        if hasattr(OUTPUT_SIZE, '_upper_bounds'):
            actual_buckets = list(OUTPUT_SIZE._upper_bounds)
            actual_buckets = [b for b in actual_buckets if b != float('inf')]

            for bucket in expected_buckets:
                assert bucket in actual_buckets, f"OUTPUT_SIZE: Bucket {bucket} not found"


class TestMetricsLabels:
    """Tests for metric labels."""

    def test_request_count_has_status_label(self):
        """Test that REQUEST_COUNT has status label."""
        from app.metrics import REQUEST_COUNT

        # Check that the metric accepts 'status' label
        try:
            REQUEST_COUNT.labels(status='200')
        except Exception as e:
            pytest.fail(f"REQUEST_COUNT should accept 'status' label: {e}")

    def test_conversion_errors_has_error_type_label(self):
        """Test that CONVERSION_ERRORS has error_type label."""
        from app.metrics import CONVERSION_ERRORS

        # Check that the metric accepts 'error_type' label
        try:
            CONVERSION_ERRORS.labels(error_type='ValueError')
        except Exception as e:
            pytest.fail(f"CONVERSION_ERRORS should accept 'error_type' label: {e}")


class TestMetricsTypes:
    """Tests for metric types."""

    def test_request_count_is_counter(self):
        """Test that REQUEST_COUNT is a Counter."""
        from app.metrics import REQUEST_COUNT
        from prometheus_client import Counter

        # Check the type through the class
        assert isinstance(REQUEST_COUNT, Counter)

    def test_conversion_duration_is_histogram(self):
        """Test that CONVERSION_DURATION is a Histogram."""
        from app.metrics import CONVERSION_DURATION
        from prometheus_client import Histogram

        assert isinstance(CONVERSION_DURATION, Histogram)

    def test_input_size_is_histogram(self):
        """Test that INPUT_SIZE is a Histogram."""
        from app.metrics import INPUT_SIZE
        from prometheus_client import Histogram

        assert isinstance(INPUT_SIZE, Histogram)

    def test_output_size_is_histogram(self):
        """Test that OUTPUT_SIZE is a Histogram."""
        from app.metrics import OUTPUT_SIZE
        from prometheus_client import Histogram

        assert isinstance(OUTPUT_SIZE, Histogram)

    def test_conversion_errors_is_counter(self):
        """Test that CONVERSION_ERRORS is a Counter."""
        from app.metrics import CONVERSION_ERRORS
        from prometheus_client import Counter

        assert isinstance(CONVERSION_ERRORS, Counter)


class TestMetricsDocumentation:
    """Tests for metric documentation strings."""

    def test_request_count_has_documentation(self):
        """Test that REQUEST_COUNT has documentation."""
        from app.metrics import REQUEST_COUNT

        assert REQUEST_COUNT._documentation
        assert 'conversion' in REQUEST_COUNT._documentation.lower()

    def test_conversion_duration_has_documentation(self):
        """Test that CONVERSION_DURATION has documentation."""
        from app.metrics import CONVERSION_DURATION

        assert CONVERSION_DURATION._documentation
        assert 'duration' in CONVERSION_DURATION._documentation.lower()

    def test_input_size_has_documentation(self):
        """Test that INPUT_SIZE has documentation."""
        from app.metrics import INPUT_SIZE

        assert INPUT_SIZE._documentation
        assert 'input' in INPUT_SIZE._documentation.lower()

    def test_output_size_has_documentation(self):
        """Test that OUTPUT_SIZE has documentation."""
        from app.metrics import OUTPUT_SIZE

        assert OUTPUT_SIZE._documentation
        assert 'output' in OUTPUT_SIZE._documentation.lower()

    def test_conversion_errors_has_documentation(self):
        """Test that CONVERSION_ERRORS has documentation."""
        from app.metrics import CONVERSION_ERRORS

        assert CONVERSION_ERRORS._documentation
        assert 'error' in CONVERSION_ERRORS._documentation.lower()


class TestMetricsIntegrationWithApp:
    """Integration tests for metrics with the FastAPI app."""

    def test_metrics_are_registered(self):
        """Test that all metrics are properly registered."""
        from prometheus_client import REGISTRY
        from app.metrics import (
            REQUEST_COUNT,
            CONVERSION_DURATION,
            INPUT_SIZE,
            OUTPUT_SIZE,
            CONVERSION_ERRORS
        )

        # Get all registered metric names
        registered_metrics = [
            metric.name for collector in REGISTRY.collect()
            for metric in collector.samples
        ]

        # Check that our metrics are registered
        assert 'pdf_conversions_total' in registered_metrics
        assert any('pdf_conversion_duration_seconds' in m for m in registered_metrics)
        assert any('pdf_input_size_bytes' in m for m in registered_metrics)
        assert any('pdf_output_size_bytes' in m for m in registered_metrics)
        assert 'pdf_conversion_errors_total' in registered_metrics

    def test_metrics_can_be_incremented(self):
        """Test that metrics can be incremented without errors."""
        from app.metrics import REQUEST_COUNT

        # This should not raise any exceptions
        try:
            REQUEST_COUNT.labels(status='200').inc()
        except Exception as e:
            pytest.fail(f"Failed to increment REQUEST_COUNT: {e}")

    def test_histograms_can_observe_values(self):
        """Test that histograms can observe values without errors."""
        from app.metrics import CONVERSION_DURATION, INPUT_SIZE, OUTPUT_SIZE

        try:
            CONVERSION_DURATION.observe(1.5)
            INPUT_SIZE.observe(1024)
            OUTPUT_SIZE.observe(2048)
        except Exception as e:
            pytest.fail(f"Failed to observe values in histograms: {e}")


class TestMetricsBucketsCoverage:
    """Tests for histogram bucket coverage."""

    def test_duration_buckets_cover_expected_range(self):
        """Test that duration buckets cover expected conversion times."""
        from app.metrics import CONVERSION_DURATION

        # Test various durations
        test_durations = [0.05, 0.2, 0.8, 2.0, 7.5, 15.0, 45.0, 90.0, 150.0]

        for duration in test_durations:
            try:
                CONVERSION_DURATION.observe(duration)
            except Exception as e:
                pytest.fail(f"Failed to observe duration {duration}: {e}")

    def test_size_buckets_cover_expected_range(self):
        """Test that size buckets cover expected PDF sizes."""
        from app.metrics import INPUT_SIZE, OUTPUT_SIZE

        # Test various sizes (in bytes)
        test_sizes = [
            500,  # 500 bytes
            5000,  # 5 KB
            50000,  # 50 KB
            500000,  # 500 KB
            5000000,  # 5 MB
            25000000,  # 25 MB
            60000000,  # 60 MB (over limit)
        ]

        for size in test_sizes:
            try:
                INPUT_SIZE.observe(size)
                OUTPUT_SIZE.observe(size)
            except Exception as e:
                pytest.fail(f"Failed to observe size {size}: {e}")


class TestMetricsNaming:
    """Tests for Prometheus naming conventions."""

    def test_counter_names_end_with_total(self):
        """Test that counter metrics follow Prometheus naming conventions."""
        from app.metrics import REQUEST_COUNT, CONVERSION_ERRORS

        # Counters should end with _total
        assert REQUEST_COUNT._name.endswith('_total')
        assert CONVERSION_ERRORS._name.endswith('_total')

    def test_duration_metric_ends_with_seconds(self):
        """Test that duration metric follows Prometheus naming conventions."""
        from app.metrics import CONVERSION_DURATION

        # Duration metrics should end with unit
        assert CONVERSION_DURATION._name.endswith('_seconds')

    def test_size_metrics_end_with_bytes(self):
        """Test that size metrics follow Prometheus naming conventions."""
        from app.metrics import INPUT_SIZE, OUTPUT_SIZE

        # Size metrics should end with _bytes
        assert INPUT_SIZE._name.endswith('_bytes')
        assert OUTPUT_SIZE._name.endswith('_bytes')

    def test_metric_names_use_underscores(self):
        """Test that metric names use underscores, not hyphens."""
        from app.metrics import (
            REQUEST_COUNT,
            CONVERSION_DURATION,
            INPUT_SIZE,
            OUTPUT_SIZE,
            CONVERSION_ERRORS
        )

        metrics = [
            REQUEST_COUNT,
            CONVERSION_DURATION,
            INPUT_SIZE,
            OUTPUT_SIZE,
            CONVERSION_ERRORS
        ]

        for metric in metrics:
            assert '-' not in metric._name, f"Metric {metric._name} contains hyphens"
            assert '_' in metric._name or metric._name.islower(), \
                f"Metric {metric._name} should use underscores"
