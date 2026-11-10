# Feature Analysis Report

## Summary
- Total features created: 36
- Feature version: 1.0.0
- Train / Val / Test: 6,275 / 1,614 / 1,548

## Top 20 Features by Composite Rank
1. **bytes**: MI=0.0025, F=4.8, rho=+0.028, mean_rank=3.2
2. **month**: MI=0.0029, F=6.3, rho=+0.031, mean_rank=3.2
3. **bytes_clean**: MI=0.0024, F=4.3, rho=+0.026, mean_rank=3.8
4. **day_of_week**: MI=0.0058, F=1.3, rho=+0.014, mean_rank=6.4
5. **src_ip_freq**: MI=0.0048, F=1.6, rho=-0.016, mean_rank=9.6
6. **hour**: MI=0.0002, F=1.6, rho=-0.016, mean_rank=10.0
7. **protocol_freq**: MI=0.0000, F=1.6, rho=+0.010, mean_rank=11.0
8. **port_freq**: MI=0.0000, F=0.2, rho=+0.002, mean_rank=11.6
9. **day_of_month**: MI=0.0000, F=0.3, rho=-0.007, mean_rank=12.0
10. **unique_ports_cum**: MI=0.0054, F=0.9, rho=-0.012, mean_rank=12.6
11. **status_clean_encoded**: MI=0.0000, F=1.2, rho=-0.012, mean_rank=13.0
12. **protocol_encoded**: MI=0.0000, F=1.2, rho=-0.014, mean_rank=13.6
13. **conn_count_cum**: MI=0.0031, F=1.1, rho=-0.013, mean_rank=14.0
14. **is_weekend**: MI=0.0000, F=1.3, rho=+0.014, mean_rank=14.8
15. **unique_dst_cum**: MI=0.0003, F=1.0, rho=-0.013, mean_rank=16.2
16. **dst_ip_freq**: MI=0.0000, F=0.6, rho=-0.010, mean_rank=18.2
17. **bytes_clean_max_1H**: MI=0.0035, F=nan, rho=+nan, mean_rank=18.3
18. **time_since_last_conn**: MI=0.0000, F=0.8, rho=-0.013, mean_rank=18.6
19. **bytes_clean_max_5min**: MI=0.0020, F=nan, rho=+nan, mean_rank=20.0
20. **bytes_clean_count_24H**: MI=0.0016, F=nan, rho=+nan, mean_rank=20.3

## Multicollinearity
- High-correlation pairs (|r| > 0.9): 4
- Max VIF: 1000799917193443.5
- Features with VIF > 10: 5

## Recommendations
- Keep top-50 by composite rank; drop high-VIF pairs.
- Rolling-window features capture per-source behavioral patterns.
- Encoded categoricals (protocol, status) add signal.