# PDF Converter Service

FastAPI-basierte REST-Schnittstelle für die Konvertierung von PDF zu PDF/A Format.

Basiert auf dem Docker Image `kutsenko/pdfa-service:latest-minimal` und nutzt das pdfa Python-Modul für optimale Performance.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen.svg)](https://pytest.org)

## Inhaltsverzeichnis

- [Features](#features)
- [Quick Start](#quick-start)
- [API Endpunkte](#api-endpunkte)
- [Build & Deployment](#build--deployment)
- [Verwendung](#verwendung)
- [Technische Details](#technische-details)
  - [Architektur](#architektur)
  - [Konfiguration](#konfiguration)
  - [Logging](#logging)
  - [Prometheus Metriken](#prometheus-metriken)
- [Entwicklung](#entwicklung)
  - [Lokale Entwicklung](#lokale-entwicklung)
  - [Projektstruktur](#projektstruktur)
- [Testing](#testing)
- [Performance](#performance)
- [Referenzen](#referenzen)

## Features

- ⚡ **Schnelle Konvertierung:** Durchschnittlich ~0.5s pro PDF (Python-Modul statt CLI)
- 🔧 **Konfigurierbare Endpunkte:** Alle URLs über Umgebungsvariablen anpassbar
- 📊 **Prometheus Metriken:** Vollständiges Monitoring mit Duration, Size, Error Tracking
- 🏥 **Health Check Support:** Dedizierter Header (`X-Health-Check`) für Monitoring
- 📝 **Strukturiertes Logging:** DEBUG für Health Checks, INFO für reguläre Requests
- 🐳 **Docker-Ready:** Vollständig containerisiert mit Docker Support
- ✅ **Production-Ready:** 87% Test Coverage, umfassende Error Handling

## Quick Start

```bash
# 1. Image bauen
docker build -t pdfconverter .

# 2. Container starten
docker run -p 8080:8080 pdfconverter

# 3. PDF konvertieren
curl -X POST http://localhost:8080/api/pdfconverter \
  -H "Content-Type: application/pdf" \
  --data-binary @input.pdf \
  -o output.pdf

# 4. Metriken prüfen
curl http://localhost:8080/metrics/
```

**Oder mit benutzerdefinierten Endpunkten:**

```bash
docker run -p 8080:8080 \
  -e CONVERTER_PATH=/convert \
  -e HEALTH_PATH=/status \
  -e METRICS_PATH=/monitoring \
  pdfconverter
```

## API Endpunkte

> **Hinweis:** Alle Endpunkt-Pfade sind über Umgebungsvariablen konfigurierbar (siehe [Konfiguration](#konfiguration)).

### POST /api/pdfconverter (oder ${CONVERTER_PATH})

Konvertiert ein PDF zu PDF/A Format.

**Request:**
- Content-Type: `application/pdf`
- Body: PDF-Datei als raw bytes
- Header (optional): `X-Health-Check: true` für Health Check Requests

**Response:**
- Content-Type: `application/pdf`
- Body: Konvertiertes PDF/A als raw bytes

**Fehler-Codes:**
- `400 Bad Request`: Leeres oder ungültiges PDF
- `413 Payload Too Large`: PDF größer als 50MB
- `415 Unsupported Media Type`: Falscher Content-Type
- `422 Unprocessable Entity`: PDF kann nicht konvertiert werden
- `500 Internal Server Error`: Unerwarteter Fehler

### GET /health (oder ${HEALTH_PATH})

Einfacher Health Check Endpunkt.

**Response:**
```json
{
  "status": "healthy"
}
```

### GET /metrics (oder ${METRICS_PATH})

Prometheus Metriken Endpunkt.

**Metriken:**
- `pdf_conversions_total`: Anzahl der Konvertierungen (nach Status)
- `pdf_conversion_duration_seconds`: Konvertierungsdauer
- `pdf_input_size_bytes`: Größe der Input PDFs
- `pdf_output_size_bytes`: Größe der Output PDFs
- `pdf_conversion_errors_total`: Anzahl der Fehler (nach Typ)

**Hinweis:** Health Check Requests werden NICHT in den Metriken erfasst.

## Build & Deployment

### Docker Image bauen

```bash
docker build -t pdfconverter .
```

### Container starten

```bash
docker run -p 8080:8080 pdfconverter
```

**Mit benutzerdefinierten Endpunkt-URLs:**

```bash
docker run -p 8080:8080 \
  -e HEALTH_PATH=/status \
  -e METRICS_PATH=/monitoring/metrics \
  -e CONVERTER_PATH=/convert \
  pdfconverter
```

### Mit docker-compose

Das Projekt enthält eine vorkonfigurierte `docker-compose.yml` mit Umgebungsvariablen-Platzhaltern.

**Starten mit Default-Werten:**
```bash
# Service starten
docker-compose up -d

# Logs anzeigen
docker-compose logs -f

# Status prüfen
docker-compose ps

# Service stoppen
docker-compose down
```

**Mit eigenen Umgebungsvariablen (.env Datei):**
```bash
# .env Datei erstellen
cat > .env << EOF
HEALTH_PATH=/status
METRICS_PATH=/monitoring
CONVERTER_PATH=/convert
EOF

# Starten mit .env Konfiguration
docker-compose up -d
```

Die `docker-compose.yml` verwendet das Format `${VARIABLE:-default}` um sowohl .env Dateien als auch inline Umgebungsvariablen zu unterstützen.

**docker-compose.yml Features:**

✅ **Health Checks** - Automatische Überwachung des Service-Status
✅ **Resource Limits** - CPU und Memory Limits (2 CPU, 2GB RAM)
✅ **Restart Policy** - Automatischer Neustart bei Fehlern
✅ **Logging Configuration** - Log Rotation (3x 10MB)
✅ **Environment Variables** - Flexible Konfiguration mit Platzhaltern
✅ **Network Isolation** - Dediziertes Bridge Network
✅ **Labels** - Service Metadata für Organisation

#### Konfigurationsoptionen

**Umgebungsvariablen (.env Datei):**
```env
HEALTH_PATH=/health
METRICS_PATH=/metrics
CONVERTER_PATH=/api/pdfconverter
```

**Port Mapping anpassen:**
```yaml
ports:
  - "8090:8080"  # Host:Container
```

**Resource Limits anpassen:**
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 4G
```

**Volumes für Persistenz:**
```yaml
volumes:
  - ./logs:/app/logs
  - /tmp/pdfconverter:/tmp
```

## Verwendung

### cURL Beispiele

**Reguläre PDF Konvertierung:**
```bash
curl -X POST http://localhost:8080/api/pdfconverter \
  -H "Content-Type: application/pdf" \
  --data-binary @input.pdf \
  -o output.pdf
```

**Health Check:**
```bash
curl -X POST http://localhost:8080/api/pdfconverter \
  -H "Content-Type: application/pdf" \
  -H "X-Health-Check: true" \
  --data-binary @input.pdf \
  -o output.pdf
```

**Metriken abrufen:**
```bash
curl http://localhost:8080/metrics
```

### Python Beispiel

```python
import requests

# PDF laden
with open('input.pdf', 'rb') as f:
    pdf_bytes = f.read()

# Konvertieren
response = requests.post(
    'http://localhost:8080/api/pdfconverter',
    headers={'Content-Type': 'application/pdf'},
    data=pdf_bytes
)

# Speichern
if response.status_code == 200:
    with open('output.pdf', 'wb') as f:
        f.write(response.content)
else:
    print(f"Error: {response.status_code} - {response.text}")
```

## Technische Details

### Architektur

- **Framework:** FastAPI 0.109.0
- **Base Image:** kutsenko/pdfa-service:latest-minimal
- **Conversion:** pdfa Python module (via asyncio.to_thread)
- **Metriken:** prometheus-client
- **Port:** 8080

### Konfiguration

#### Umgebungsvariablen

##### Endpunkt-Pfade (vollständig konfigurierbar)

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `HEALTH_PATH` | `/health` | Health Check Endpunkt |
| `METRICS_PATH` | `/metrics` | Prometheus Metriken Endpunkt |
| `CONVERTER_PATH` | `/api/pdfconverter` | PDF Konvertierungs-Endpunkt |

**Beispiel:**
```bash
docker run -p 8080:8080 \
  -e HEALTH_PATH=/status \
  -e METRICS_PATH=/monitoring/metrics \
  -e CONVERTER_PATH=/api/v1/convert \
  pdfconverter
```

##### Weitere Konfiguration

| Parameter | Wert | Anpassbar | Beschreibung |
|-----------|------|-----------|--------------|
| **MAX_PDF_SIZE** | 50MB | Nein* | Maximale PDF-Größe |
| **PDF/A Level** | 2 | Nein* | PDF/A Konformitätsstufe |
| **OCR Mode** | `skip_ocr_on_tagged_pdfs=True` | Nein* | OCR nur für PDFs ohne Text |
| **Port** | 8080 | Ja (Docker) | HTTP Server Port |

\* *Diese Werte sind im Code definiert und können durch Rebuild mit angepasstem Code geändert werden.*

### Logging

Das Logging unterscheidet zwischen regulären Requests und Health Checks:

- **Reguläre Requests:** INFO Level
  - "begin conversion"
  - "completed conversion success/error"

- **Health Checks:** DEBUG Level
  - "begin HEALTHCHECK"
  - "completed HEALTHCHECK success/error"

### Prometheus Metriken

Metriken werden nur für Nicht-Health-Check Requests aufgezeichnet.

**Histogram Buckets:**
- Duration: 0.1s bis 120s
- Size: 1KB bis 50MB

## Entwicklung

### Lokale Entwicklung

```bash
# Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt

# Development Server starten
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

**Hinweis:** Die Tests nutzen Mocks für das pdfa-Modul und können ohne Docker-Container ausgeführt werden.

### Projektstruktur

```
pdfconverter/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI Application
│   ├── converter.py     # PDF Conversion Logic
│   └── metrics.py       # Prometheus Metrics
├── tests/
│   ├── __init__.py
│   ├── conftest.py      # Test Fixtures
│   ├── test_api.py      # API Integration Tests
│   ├── test_converter.py # Converter Unit Tests
│   ├── test_metrics.py  # Metrics Tests
│   └── README.md        # Test Dokumentation
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt # Development Dependencies
├── pyproject.toml       # Tool-Konfiguration (Black, Ruff, Pytest, MyPy)
└── README.md
```

## Testing

### Test Installation

```bash
# Installiere Test-Dependencies
pip install -r requirements-dev.txt
```

### Tests ausführen

```bash
# Alle Tests
pytest

# Mit Coverage Report
pytest --cov=app --cov-report=html

# Einzelne Test-Dateien
pytest tests/test_api.py
pytest tests/test_converter.py
pytest tests/test_metrics.py

# Verbose Output
pytest -vv

# Stop bei erstem Fehler
pytest -x
```

### Direkte Befehle

```bash
# Tests
pytest                                    # Alle Tests
pytest --cov=app --cov-report=html        # Mit Coverage
pytest -x                                 # Stop bei erstem Fehler
pytest tests/test_api.py -v               # Nur API Tests
pytest tests/test_converter.py -v         # Nur Converter Tests
pytest tests/test_metrics.py -v           # Nur Metrics Tests

# Code Quality (nutzt pyproject.toml Konfiguration)
ruff check app tests                      # Linting mit Ruff
black app tests                           # Code Formatierung mit Black
mypy app                                  # Type Checking

# Coverage Report anzeigen
pytest --cov=app --cov-report=html
xdg-open htmlcov/index.html  # oder open auf macOS
```

### Test-Kategorien

**API Integration Tests (30+ Tests)**
- Health und Metrics Endpunkte
- PDF Converter Endpunkt Funktionalität
- Content-Type Validierung
- Fehlerbehandlung (400, 413, 415, 422, 500)
- Health Check Header Verarbeitung
- Response Headers
- Prometheus Metriken Integration

**Converter Unit Tests (15 Tests)**
- PDF Validierung (Header-Checks)
- Erfolgreiche Konvertierung mit Python-Modul
- Error Handling (ImportError, RuntimeError)
- Logging (INFO/DEBUG Level)
- pdfa Module Call Structure
- Temporary Files Cleanup
- asyncio.to_thread Integration

**Metrics Tests (25+ Tests)**
- Metric Definitionen
- Histogram Buckets
- Metric Labels
- Prometheus Naming Conventions
- Integration mit App

### Coverage

Ziel: **> 80% Code Coverage**

```bash
# Coverage Report in Terminal
pytest --cov=app --cov-report=term-missing

# HTML Coverage Report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Continuous Integration

Für CI/CD Pipelines:

```bash
pytest --cov=app --cov-report=xml --junitxml=junit.xml --cov-fail-under=80
```

Mehr Details in [tests/README.md](tests/README.md).

## Performance

### Konvertierungszeiten

Das System nutzt das pdfa Python-Modul direkt via `asyncio.to_thread()` für optimale Performance:

| Metrik | Wert |
|--------|------|
| Durchschnittliche Konvertierungszeit | ~0.525s |
| Median | ~0.527s |
| Min | ~0.507s |
| Max | ~0.546s |

**Optimierungen:**
- ✅ Python-Modul statt CLI-Subprocess (32% schneller)
- ✅ `asyncio.to_thread()` für Non-Blocking Execution
- ✅ `skip_ocr_on_tagged_pdfs=True` für PDFs mit Text
- ✅ Effizientes Temporary File Management

### Vergleich CLI vs. Python Module

| Methode | Durchschnitt | Overhead |
|---------|-------------|----------|
| CLI (subprocess) | ~0.77s | Subprocess-Spawning |
| Python Module | ~0.525s | Minimaler Thread-Overhead |
| **Verbesserung** | **-32%** | **Deutlich reduziert** |

### Performance-Tipps

**Für hohen Durchsatz:**
```yaml
# docker-compose.yml
services:
  pdfconverter:
    build: .
    deploy:
      replicas: 3  # Mehrere Instanzen für Load Balancing
    environment:
      - WORKERS=4  # Falls uvicorn mit mehreren Workern gestartet wird
```

**Monitoring:**
Nutzen Sie die Prometheus-Metriken um Performance zu überwachen:
```promql
# 95th Percentile Konvertierungszeit
histogram_quantile(0.95, pdf_conversion_duration_seconds_bucket)

# Requests pro Sekunde
rate(pdf_conversions_total[5m])

# Durchschnittliche PDF-Größe
rate(pdf_input_size_bytes_sum[5m]) / rate(pdf_input_size_bytes_count[5m])
```

## Production Deployment

### Docker Best Practices

**Health Checks im Docker Container:**
```dockerfile
# Dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

**Resource Limits:**
```yaml
# docker-compose.yml
services:
  pdfconverter:
    image: pdfconverter
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Kubernetes Deployment

**Basic Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pdfconverter
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pdfconverter
  template:
    metadata:
      labels:
        app: pdfconverter
    spec:
      containers:
      - name: pdfconverter
        image: pdfconverter:latest
        ports:
        - containerPort: 8080
        env:
        - name: HEALTH_PATH
          value: "/health"
        - name: METRICS_PATH
          value: "/metrics"
        - name: CONVERTER_PATH
          value: "/api/pdfconverter"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: pdfconverter
spec:
  selector:
    app: pdfconverter
  ports:
  - port: 8080
    targetPort: 8080
  type: ClusterIP
```

### Monitoring Setup

**Prometheus ServiceMonitor:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: pdfconverter
spec:
  selector:
    matchLabels:
      app: pdfconverter
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

**Grafana Dashboard Metriken:**
- `rate(pdf_conversions_total[5m])` - Requests pro Sekunde
- `histogram_quantile(0.95, pdf_conversion_duration_seconds_bucket)` - 95th Percentile Latenz
- `pdf_conversion_errors_total` - Error Rate
- `rate(pdf_input_size_bytes_sum[5m])` - Durchsatz in Bytes/s

### Sicherheit

**Empfohlene Maßnahmen:**
- Laufen als Non-Root User im Container
- Read-Only Root Filesystem wo möglich
- Network Policies für eingeschränkten Zugriff
- Regelmäßige Updates des Base Images
- Secret Management für sensitive Konfiguration

## Troubleshooting

### Häufige Probleme

**Problem: Conversion fails with "pdfa module not available"**
```bash
# Lösung: Base Image verwenden
docker build -t pdfconverter .
# Nicht: pip install in anderem Image
```

**Problem: Out of Memory Errors**
```bash
# Lösung: Memory Limit erhöhen
docker run -m 2g pdfconverter
```

**Problem: Slow conversion times**
```bash
# Prüfen: Metriken analysieren
curl http://localhost:8080/metrics/ | grep duration

# Lösung: Mehrere Replicas starten
docker-compose up --scale pdfconverter=3
```

## Changelog

### v1.2.0 (2025-12-09)
- ✅ Externalisierte Endpunkt-URLs via Umgebungsvariablen
- ✅ Konfigurierbare Pfade für Health, Metrics und Converter Endpunkte
- 📝 Erweiterte README-Dokumentation

### v1.1.0 (2025-12-09)
- ⚡ Optimierung: Python-Modul statt CLI (32% schneller)
- ✅ Umstellung auf `asyncio.to_thread()` für Non-Blocking Execution
- 🔧 Verbesserte OCR-Einstellungen (`skip_ocr_on_tagged_pdfs=True`)
- ✅ Tests auf 87% Coverage erhöht

### v1.0.0 (Initial Release)
- 🎉 Initiale Implementierung mit FastAPI
- 📊 Prometheus Metriken Integration
- 🏥 Health Check Support
- 🐳 Docker-basierte Deployment
- ✅ Umfassende Test-Suite (63 Tests)

## Referenzen

- [pdfa-service GitHub](https://github.com/kutsenko/pdfa-service)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prometheus Client Python](https://github.com/prometheus/client_python)
- [OCRmyPDF Documentation](https://ocrmypdf.readthedocs.io/)

## Lizenz

Dieses Projekt nutzt das `kutsenko/pdfa-service` Base Image. Bitte beachten Sie die Lizenzbedingungen des Base Images.
