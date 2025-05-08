# Environmental Telemetry Stream

## Sensor ID: ENV-SENSOR-01
Timestamp, Temperature (°C), Humidity (%)
---
2024-07-27T12:00:00.123Z, 25.5, 45.2
2024-07-27 12:00:05,500, 25.6, 45.1  # Ambiguous format, assumed UTC
2024-07-27T12:00:10.750+00:00, 25.4, 45.3
1722081615.999, 25.5, 45.0          # Unix timestamp (float)
2024-07-27 05:00:20,100, 26.0, 44.8  # Ambiguous format, likely local time (e.g., UTC-7)
2024-07-27T12:00:25.500Z, 28.5, 44.9  # Sudden temp jump -> ANOMALY
NOT_A_TIMESTAMP, 28.6, 45.0          # Invalid timestamp -> INCONSISTENCY
2024-07-27T12:00:35.900Z, 28.7, 55.1  # Sudden humidity jump -> ANOMALY
2024-07-27T12:00:30.800Z, 28.6, 55.0  # Timestamp out of order -> INCONSISTENCY
2024-07-27T12:00:40.200Z, 27.0, 54.5  # Temp drop 