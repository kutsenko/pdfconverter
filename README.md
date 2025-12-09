# PDF Converter Service

FastAPI-basierte REST-Schnittstelle für die Konvertierung von PDF zu PDF/A Format.

Basiert auf dem Docker Image `kutsenko/pdfa-service:latest-minimal` und delegiert die PDF-Konvertierung an pdfa-cli.

## Features

- REST API Endpunkt für PDF zu PDF/A Konvertierung
- Prometheus Metriken für Monitoring
- Health Check Support mit dediziertem Header
- Strukturiertes Logging (DEBUG für Health Checks, INFO für reguläre Requests)
- Docker-basierte Deployment

## API Endpunkte

### POST /api/pdfconverter

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

### GET /health

Einfacher Health Check Endpunkt.

**Response:**
```json
{
  "status": "healthy"
}
```

### GET /metrics

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
docker run -p 8000:8000 pdfconverter
```

### Mit docker-compose

```yaml
version: '3.8'
services:
  pdfconverter:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
```

## Verwendung

### cURL Beispiele

**Reguläre PDF Konvertierung:**
```bash
curl -X POST http://localhost:8000/api/pdfconverter \
  -H "Content-Type: application/pdf" \
  --data-binary @input.pdf \
  -o output.pdf
```

**Health Check:**
```bash
curl -X POST http://localhost:8000/api/pdfconverter \
  -H "Content-Type: application/pdf" \
  -H "X-Health-Check: true" \
  --data-binary @input.pdf \
  -o output.pdf
```

**Metriken abrufen:**
```bash
curl http://localhost:8000/metrics
```

### Python Beispiel

```python
import requests

# PDF laden
with open('input.pdf', 'rb') as f:
    pdf_bytes = f.read()

# Konvertieren
response = requests.post(
    'http://localhost:8000/api/pdfconverter',
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
- **Conversion Tool:** pdfa-cli (via subprocess)
- **Metriken:** prometheus-client
- **Port:** 8000

### Konfiguration

- **MAX_PDF_SIZE:** 50MB (52428800 bytes)
- **PDF/A Level:** 2
- **OCR:** Deaktiviert (für bessere Performance)

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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Hinweis:** Für lokale Entwicklung muss pdfa-cli installiert sein.

### Projektstruktur

```
pdfconverter/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI Application
│   ├── converter.py     # PDF Conversion Logic
│   └── metrics.py       # Prometheus Metrics
├── Dockerfile
├── requirements.txt
└── README.md
```

## Optimierung

### Phase 2: Python Module Import (optional)

Aktuell verwendet die Implementierung pdfa-cli via subprocess. Für bessere Performance kann dies auf direkten Python Import umgestellt werden:

1. Inspiziere pdfa Package im Container:
   ```bash
   docker run -it pdfconverter python -c "import pdfa; help(pdfa)"
   ```

2. Aktualisiere `converter.py` um pdfa Module direkt zu nutzen

3. Performance-Tests durchführen

## Referenzen

- [pdfa-service GitHub](https://github.com/kutsenko/pdfa-service)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prometheus Client Python](https://github.com/prometheus/client_python)
