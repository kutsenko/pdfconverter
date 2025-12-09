.PHONY: help test test-cov test-fast test-verbose clean install install-dev lint format docker-build docker-run

# Default target
help:
	@echo "PDF Converter Service - Make Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install        - Install production dependencies"
	@echo "  make install-dev    - Install development dependencies"
	@echo "  make format         - Format code with black"
	@echo "  make lint           - Run linters (flake8, pylint)"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make test-fast      - Run tests, stop on first failure"
	@echo "  make test-verbose   - Run tests with verbose output"
	@echo "  make test-api       - Run only API tests"
	@echo "  make test-converter - Run only converter tests"
	@echo "  make test-metrics   - Run only metrics tests"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-run     - Run Docker container"
	@echo "  make docker-test    - Build and test in Docker"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Remove generated files"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

# Testing
test:
	pytest

test-cov:
	pytest --cov=app --cov-report=term-missing --cov-report=html

test-fast:
	pytest -x

test-verbose:
	pytest -vv

test-api:
	pytest tests/test_api.py -v

test-converter:
	pytest tests/test_converter.py -v

test-metrics:
	pytest tests/test_metrics.py -v

# Code quality
lint:
	@echo "Running flake8..."
	flake8 app tests --max-line-length=120 --exclude=__pycache__
	@echo ""
	@echo "Running pylint..."
	pylint app --disable=C0111,R0903

format:
	black app tests --line-length=120

# Docker
docker-build:
	docker build -t pdfconverter .

docker-run:
	docker run -p 8000:8000 pdfconverter

docker-test:
	docker build -t pdfconverter-test --target test .
	docker run --rm pdfconverter-test pytest

# Cleanup
clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf *.egg-info
	rm -rf dist
	rm -rf build
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete

# Development server
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Show coverage in browser
coverage-html:
	pytest --cov=app --cov-report=html
	@echo "Opening coverage report..."
	@which xdg-open > /dev/null && xdg-open htmlcov/index.html || \
	which open > /dev/null && open htmlcov/index.html || \
	echo "Please open htmlcov/index.html manually"
