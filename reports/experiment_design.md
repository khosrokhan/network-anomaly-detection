# Experiment Design Document

## Hypothesis
- H0: XGBoost does not improve detection rate vs rule-based
- H1: XGBoost improves detection rate by >= 5% relative

## Primary Metric
- Baseline: 0.6
- Target: 0.63
- MDE relative: 0.05
- MDE absolute: 0.03

## Randomization Unit
- Source IP
- Available IPs: 1548

## Sample Size
- Effect size (Cohen h): 0.061664282118138125
- Alpha: 0.05, Power: 0.80
- Required per arm: 4129
- Total: 8258
- Duration: 163 days

## Feasibility
- Achievable per arm: 774
- Required per arm: 4129
- Feasible: False

## Guardrails
Latency p99 < 50ms, alert volume +50%, complaints < 5/day, ECE < 0.1, PSI < 0.2

## Simulation Results
- Mean recall lift: 0.27086263065580585
- P(recall_lift > 5%): 0.861
- Mean FPR increase: 0.010103185693892413

## Implementation
1. 50/50 IP split
2. Deploy XGBoost to treatment
3. Minimum 163 days
4. Daily guardrail review
5. Interim at 33% / 66%