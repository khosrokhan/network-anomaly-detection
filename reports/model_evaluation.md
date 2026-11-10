# Model Evaluation Report

## Test-Set Comparison

| model              |    pr_auc |   roc_auc |        f1 |   precision |    recall |       brier |
|:-------------------|----------:|----------:|----------:|------------:|----------:|------------:|
| IsolationForest    | 0.0458819 |  0.455676 | 0.0614035 |   0.0463576 | 0.0909091 |   0.27264   |
| LOF                | 0.0465613 |  0.47942  | 0.0295567 |   0.0238095 | 0.038961  | nan         |
| LogisticRegression | 0.0472649 |  0.462332 | 0.0746562 |   0.0403826 | 0.493506  |   0.261482  |
| XGBoost            | 0.0560377 |  0.48979  | 0.0623701 |   0.0371287 | 0.194805  |   0.19994   |
| LightGBM           | 0.0665645 |  0.52031  | 0.0598802 |   0.0555556 | 0.0649351 |   0.0795249 |
| XGBoost_optimal    | 0.0560377 |  0.48979  | 0.0924855 |   0.0507614 | 0.519481  |   0.19994   |

## Best Model: XGBoost
- Optimal threshold (F1 on val): 0.4234
- Test PR-AUC: 0.0560
- Test ROC-AUC: 0.4898
- Test F1: 0.0925
- Test Precision: 0.0508
- Test Recall: 0.5195
- Brier score: 0.1999

## Subgroup Performance
- **ddos**: n=17, ROC-AUC=0.4000, PR-AUC=0.1394
- **port_scan**: n=11, ROC-AUC=0.5000, PR-AUC=0.1667
- **brute_force**: n=20, ROC-AUC=0.5556, PR-AUC=0.1548