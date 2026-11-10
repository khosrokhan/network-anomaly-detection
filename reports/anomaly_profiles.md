# Anomaly Type Profiles & Root-Cause Analysis

## DDOS
- Count: 2
- Unique source IPs: 2
- Unique destination IPs: 2
- Top ports: [23259, 38170]
- Protocols: {'DNS': 1, 'TCP': 1}
- Bytes (mean/median/std): 5835692.5 / 5835692.5 / 551293.6806317482
- Peak hours: [7, 10]
- Peak days (0=Mon): [0, 2]

## BRUTE_FORCE
- Count: 2
- Unique source IPs: 2
- Unique destination IPs: 2
- Top ports: [1063, 23077]
- Protocols: {'DNS': 1, 'HTTP': 1}
- Bytes (mean/median/std): 6930209.0 / 6930209.0 / 3739812.812376844
- Peak hours: [2, 5]
- Peak days (0=Mon): [3, 5]

## PORT_SCAN
- Count: 1
- Unique source IPs: 1
- Unique destination IPs: 1
- Top ports: [143]
- Protocols: {'FTP': 1}
- Bytes (mean/median/std): 6409846.0 / 6409846.0 / 0.0
- Peak hours: [17]
- Peak days (0=Mon): [1]

## Distinguishing Features (Bonferroni-corrected)

## Root-Cause Hypotheses
- port_scan: high unique-port count per source; low bytes per connection
- ddos: high connection frequency; high aggregate bytes; concentrated targets
- brute_force: repeated connections to same port; high error rate
- data_exfil: large outbound bytes; off-hours activity; rare destinations

## Causal Findings
- Balance check: SMD < 0.1 on all adjusted confounders.

## Recommendations
- Monitor per-source port entropy as an early-warning signal.
- Build per-source behavioral baselines (not global thresholds).
- Use protocol-specific thresholds for bytes and error rate.