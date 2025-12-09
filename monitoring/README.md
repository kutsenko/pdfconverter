# Monitoring Setup für PDF Converter Service

Dieses Verzeichnis enthält die Konfigurationsdateien für das Monitoring-Setup mit Prometheus und Grafana.

## Struktur

```
monitoring/
├── prometheus.yml                      # Prometheus Hauptkonfiguration
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── prometheus.yml         # Prometheus Datasource für Grafana
│       └── dashboards/
│           └── dashboard.yml          # Dashboard Provisioning Config
└── README.md                          # Diese Datei
```

## Verwendung

### Mit docker-compose.prod.yml starten

```bash
# Kompletten Monitoring Stack starten
docker-compose -f docker-compose.prod.yml up -d

# Logs anzeigen
docker-compose -f docker-compose.prod.yml logs -f

# Stack stoppen
docker-compose -f docker-compose.prod.yml down
```

### Zugriff auf Services

Nach dem Start sind folgende Services verfügbar:

- **PDF Converter API**: http://localhost:8080
  - Health: http://localhost:8080/health
  - Metrics: http://localhost:8080/metrics/
  - API: http://localhost:8080/api/pdfconverter

- **Prometheus**: http://localhost:9090
  - Metrics Browser und Query Interface
  - Targets Status: http://localhost:9090/targets

- **Grafana**: http://localhost:3000
  - Default Login: admin / admin
  - Prometheus Datasource ist bereits konfiguriert

- **Node Exporter**: http://localhost:9100/metrics
  - System-Level Metriken

## Prometheus Konfiguration

Die Datei `prometheus.yml` definiert:

- **Scrape Interval**: 15s (global), 10s für pdfconverter
- **Jobs**:
  - `pdfconverter`: Scraped Metriken vom PDF Converter Service
  - `prometheus`: Self-Monitoring
  - `node-exporter`: System Metriken

### Wichtige Metriken

Der PDF Converter Service exportiert folgende Metriken:

```promql
# Anzahl Konvertierungen (nach Status)
pdf_conversions_total{status="200"}

# Konvertierungsdauer
pdf_conversion_duration_seconds

# PDF Größen
pdf_input_size_bytes
pdf_output_size_bytes

# Fehler
pdf_conversion_errors_total
```

## Grafana Dashboards

### Eigene Dashboards erstellen

1. Öffne Grafana: http://localhost:3000
2. Login mit: admin / admin
3. Erstelle neues Dashboard
4. Füge Panels mit folgenden Queries hinzu:

**Requests pro Sekunde:**
```promql
rate(pdf_conversions_total[5m])
```

**95th Percentile Latenz:**
```promql
histogram_quantile(0.95, rate(pdf_conversion_duration_seconds_bucket[5m]))
```

**Durchschnittliche Konvertierungszeit:**
```promql
rate(pdf_conversion_duration_seconds_sum[5m]) / rate(pdf_conversion_duration_seconds_count[5m])
```

**Error Rate:**
```promql
rate(pdf_conversion_errors_total[5m])
```

**Durchsatz (Bytes/s):**
```promql
rate(pdf_input_size_bytes_sum[5m])
```

### Dashboard exportieren/importieren

```bash
# Dashboard exportieren
curl -u admin:admin http://localhost:3000/api/dashboards/uid/YOUR_DASHBOARD_UID

# Dashboard importieren (JSON Datei)
curl -X POST -H "Content-Type: application/json" \
  -u admin:admin \
  -d @dashboard.json \
  http://localhost:3000/api/dashboards/db
```

## Alerting (Optional)

Für Production sollten Alerts konfiguriert werden:

### Beispiel Alert Rules

Erstelle `monitoring/alert.rules.yml`:

```yaml
groups:
  - name: pdfconverter_alerts
    interval: 30s
    rules:
      # Hohe Error Rate
      - alert: HighErrorRate
        expr: rate(pdf_conversion_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      # Langsame Konvertierung
      - alert: SlowConversion
        expr: histogram_quantile(0.95, rate(pdf_conversion_duration_seconds_bucket[5m])) > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow PDF conversion"
          description: "95th percentile is {{ $value }}s"

      # Service Down
      - alert: ServiceDown
        expr: up{job="pdfconverter"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PDF Converter service is down"
```

Aktiviere in `prometheus.yml`:
```yaml
rule_files:
  - "alert.rules.yml"
```

## Persistenz

Die Monitoring-Daten werden in Docker Volumes gespeichert:

- `prometheus-data`: Prometheus Metriken (30 Tage Retention)
- `grafana-data`: Grafana Dashboards und Konfiguration

```bash
# Volumes anzeigen
docker volume ls | grep pdfconverter

# Volume Daten anzeigen
docker volume inspect pdfconverter_prometheus-data

# Volumes löschen (ACHTUNG: Löscht alle Daten!)
docker-compose -f docker-compose.prod.yml down -v
```

## Troubleshooting

### Prometheus kann pdfconverter nicht erreichen

```bash
# Prüfe ob Service läuft
docker-compose -f docker-compose.prod.yml ps

# Prüfe Netzwerk
docker network inspect pdfconverter_monitoring

# Teste manuell
docker exec prometheus wget -O- http://pdfconverter:8080/metrics/
```

### Grafana zeigt keine Daten

1. Prüfe Datasource Konfiguration: http://localhost:3000/datasources
2. Teste Prometheus Connection
3. Prüfe ob Prometheus Daten hat: http://localhost:9090/graph

### Zu viel Disk Space Verwendung

```bash
# Prometheus Retention anpassen (in docker-compose.prod.yml)
- '--storage.tsdb.retention.time=7d'  # Statt 30d

# Alte Daten manuell löschen
docker exec prometheus rm -rf /prometheus/*
```

## Production Best Practices

1. **Sicherheit**:
   - Ändere Grafana Admin Passwort
   - Verwende TLS/HTTPS
   - Beschränke Port-Zugriff

2. **Persistenz**:
   - Verwende externe Volumes für Backups
   - Regelmäßige Snapshots von Grafana Dashboards

3. **Alerting**:
   - Konfiguriere Alertmanager
   - Integriere mit Slack/Email/PagerDuty

4. **Performance**:
   - Optimiere Scrape Intervals
   - Nutze Recording Rules für komplexe Queries
   - Limitiere Retention Period basierend auf Bedarf

## Weitere Ressourcen

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
