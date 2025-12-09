FROM kutsenko/pdfa-service:latest-minimal

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install additional Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/app/

# Expose port
EXPOSE 8000

# Start FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
