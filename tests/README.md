# PDF Converter Tests

Umfassende Test-Suite für den PDF Converter Service mit Unit Tests, Integration Tests und Metrics Tests.

## Test-Struktur

```
tests/
├── __init__.py
├── conftest.py           # Pytest Fixtures und Konfiguration
├── test_api.py          # API Integration Tests
├── test_converter.py    # Converter Unit Tests
├── test_metrics.py      # Metrics Tests
└── README.md            # Diese Datei
```

## Installation

Installiere die Test-Dependencies:

```bash
pip install -r requirements-dev.txt
```

## Tests ausführen

### Alle Tests

```bash
pytest
```

### Mit Coverage Report

```bash
pytest --cov=app --cov-report=html
```

Der Coverage Report wird in `htmlcov/index.html` generiert.

### Spezifische Test-Dateien

```bash
# Nur API Tests
pytest tests/test_api.py

# Nur Converter Tests
pytest tests/test_converter.py

# Nur Metrics Tests
pytest tests/test_metrics.py
```

### Tests mit Markern

```bash
# Nur Unit Tests
pytest -m unit

# Nur Integration Tests
pytest -m integration

# Langsame Tests ausschließen
pytest -m "not slow"
```

### Verbose Output

```bash
pytest -vv
```

### Stop bei erstem Fehler

```bash
pytest -x
```

## Test-Kategorien

### 1. API Integration Tests (`test_api.py`)

Tests für die REST API Endpunkte:

- **Health Endpoint Tests**: `/health` Endpunkt
- **Metrics Endpoint Tests**: `/metrics` Prometheus Endpunkt
- **PDF Converter Endpoint Tests**: `/api/pdfconverter` Hauptfunktionalität
  - Erfolgreiche Konvertierung
  - Content-Type Validierung
  - Fehlerbehandlung (400, 413, 415, 422, 500)
- **Health Check Header Tests**: `X-Health-Check` Header Verarbeitung
- **Response Headers Tests**: Content-Type und Content-Disposition
- **Metrics Integration Tests**: Metriken-Aufzeichnung
- **Error Handling Tests**: Fehlerszenarien

**Anzahl Tests**: 30+ Test Cases

### 2. Converter Unit Tests (`test_converter.py`)

Tests für die PDF Conversion Logic:

- **Basic Validation**: PDF Header Validierung
- **Conversion Success**: Erfolgreiche Konvertierung
- **Error Handling**: Subprocess-Fehler, fehlende Output-Dateien
- **Logging**: INFO/DEBUG Level für reguläre/Health-Check Requests
- **Command Structure**: pdfa-cli Parameter
- **Temporary Files**: Cleanup nach Konvertierung

**Anzahl Tests**: 15+ Test Cases

### 3. Metrics Tests (`test_metrics.py`)

Tests für Prometheus Metriken:

- **Metric Definitions**: Alle Metriken sind definiert
- **Metric Types**: Counter, Histogram, Gauge
- **Histogram Buckets**: Korrekte Bucket-Konfiguration
- **Metric Labels**: Status, error_type Labels
- **Naming Conventions**: Prometheus Best Practices
- **Integration**: Metriken sind registriert und funktional

**Anzahl Tests**: 25+ Test Cases

## Test Fixtures

Definiert in `conftest.py`:

- **client**: FastAPI TestClient
- **valid_pdf**: Minimales gültiges PDF
- **invalid_pdf**: Ungültiges PDF (für Fehler-Tests)
- **large_pdf**: PDF über Größenlimit (> 50MB)
- **empty_pdf**: Leeres PDF

## Mocking

Tests verwenden `unittest.mock` für:

- **subprocess.run**: pdfa-cli Aufrufe
- **File I/O**: Lesen/Schreiben von PDFs
- **os.path.exists**: Dateisystem-Operationen
- **Logger**: Logging-Verhalten

## Coverage

Ziel: **> 80% Code Coverage**

Coverage Report anzeigen:

```bash
pytest --cov=app --cov-report=term-missing
```

HTML Report:

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Continuous Integration

Für CI/CD Pipelines:

```bash
# Mit Coverage und JUnit XML Report
pytest --cov=app --cov-report=xml --junitxml=junit.xml

# Mit strikter Coverage-Anforderung
pytest --cov=app --cov-fail-under=80
```

## Test-Daten

### Minimal Valid PDF

Das in den Tests verwendete minimale PDF ist ein gültiges PDF-Dokument mit:
- Korrekte PDF Header (`%PDF-1.4`)
- Catalog und Pages Objects
- Xref Table und Trailer
- EOF Marker

Größe: ~110 Bytes

### Mock Responses

Tests mocken die pdfa-cli Responses:
- Erfolgreiche Konvertierung
- Fehlerhafte Konvertierung
- Verschiedene Exit Codes

## Debugging

### Einzelnen Test mit Debugging

```bash
pytest tests/test_api.py::TestPdfConverterEndpoint::test_successful_conversion -vv -s
```

### Pytest mit Breakpoint

```python
def test_something():
    # Code...
    import pdb; pdb.set_trace()
    # More code...
```

### Logging während Tests anzeigen

```bash
pytest --log-cli-level=DEBUG
```

## Best Practices

1. **Isolation**: Jeder Test ist isoliert und verwendet Mocks
2. **Fast**: Tests laufen schnell (< 5s für alle)
3. **Deterministic**: Tests produzieren konsistente Ergebnisse
4. **Descriptive**: Test-Namen beschreiben was getestet wird
5. **Arrange-Act-Assert**: Klare Test-Struktur

## Troubleshooting

### Import Errors

Stelle sicher, dass das Projekt-Verzeichnis im Python-Path ist:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

Oder verwende pytest mit:

```bash
pytest --pythonpath=.
```

### Async Tests

Für async Tests ist `pytest-asyncio` erforderlich:

```bash
pip install pytest-asyncio
```

### Coverage nicht vollständig

Checke welche Zeilen nicht getestet sind:

```bash
pytest --cov=app --cov-report=term-missing
```

## Weitere Informationen

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
