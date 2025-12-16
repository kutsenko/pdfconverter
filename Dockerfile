FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OCRmyPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OCR Engine
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    # PDF Processing
    ghostscript \
    qpdf \
    # Image Processing
    pngquant \
    unpaper \
    # Additional dependencies
    libleptonica-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/app/

# Expose port
EXPOSE 8080

# Start FastAPI application with multiple workers
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers ${UVICORN_WORKERS:-4} --timeout-keep-alive 75"]
