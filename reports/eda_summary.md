# EDA Summary Report

## Dataset Overview
- Total records: 10300
- Clean records: 9437 (91.6%)
- Quarantined: 986
- Time range: 2024-01-01 01:15:45+00:00 to 2024-12-31 23:14:19+00:00

## Data Quality Issues
- DUPLICATE_RECORD: 288 records
- INVALID_IP: 166 records
- INVALID_TIMESTAMP: 134 records
- INVALID_PORT: 125 records
- MISSING_REQUIRED_FIELD: 123 records
- TIMESTAMP_OUT_OF_RANGE: 100 records
- NEGATIVE_BYTES: 50 records

## Target Distribution
- Benign: 8978 (95.1%)
- Malicious: 459 (4.9%)
- Imbalance: 1:20.0

## Anomaly Types
- brute_force: 5 records, 5 sources, top ports ['32702', '23077', '14980']
- data_exfil: 2 records, 2 sources, top ports ['8443', '35827']
- ddos: 5 records, 5 sources, top ports ['65073', '38170', '24008']
- port_scan: 1 records, 1 sources, top ports ['143']

## Key Findings
- Temporal, protocol, port, and byte patterns differ significantly between benign and malicious.
- Class imbalance requires handling (scale_pos_weight or resampling).
- IP-based behavioral features are strong signals.

## Recommendations
- Use temporal splits (not random) to avoid leakage.
- Engineer per-src_ip behavioral and rolling-window features.
- Test statistical baselines before deep learning.