from prometheus_client import Counter, Histogram


# Counter for total conversions
REQUEST_COUNT = Counter(
    'pdf_conversions_total',
    'Total PDF conversions',
    ['status']  # HTTP Status Code
)

# Histogram for conversion duration
CONVERSION_DURATION = Histogram(
    'pdf_conversion_duration_seconds',
    'PDF conversion duration in seconds',
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
)

# Histogram for input PDF size
INPUT_SIZE = Histogram(
    'pdf_input_size_bytes',
    'Input PDF size in bytes',
    buckets=[1024, 10240, 102400, 1048576, 10485760, 52428800]  # 1KB to 50MB
)

# Histogram for output PDF size
OUTPUT_SIZE = Histogram(
    'pdf_output_size_bytes',
    'Output PDF size in bytes',
    buckets=[1024, 10240, 102400, 1048576, 10485760, 52428800]  # 1KB to 50MB
)

# Counter for conversion errors
CONVERSION_ERRORS = Counter(
    'pdf_conversion_errors_total',
    'Total conversion errors',
    ['error_type']
)
