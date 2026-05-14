# PHASE 05 STAGE C - Final ML Result Summary and Report Packaging Check

**Status:** Complete

## Scope
This summary packages the verified Stage B1 and Stage B2 results for final report use. It does not train new models, run simulations, or modify the official train, validation, or test split.

## Verified dataset and split
- Total rows: 1148
- Train: S1-S9 = 1012
- Validation: S10 = 68
- Test: S11 = 68
- Random split used: No
- S11 used in training or tuning: No

## Model C clarification
The Model C inconsistency is resolved by separating two different saved artifacts:

### Stage B1 saved results
From [model_c_pairwise_healing_results.json](../05_results/model_c_pairwise_healing_results.json):
- Accuracy: 1.0000
- Precision: 1.0000
- Recall: 1.0000
- F1-score: 1.0000
- Balanced accuracy: 1.0000
- Confusion matrix: [[24, 0], [0, 8]]

### Stage B2 safe results
From [PHASE05_STAGEB2_SAFE_MODEL_RESULTS.json](../05_results/PHASE05_STAGEB2_SAFE_MODEL_RESULTS.json):
- Accuracy: 1.0000
- F1-score: 0.0000
- Confusion matrix: [[32]]
- Validation F1-score: 0.0000

### Why F1 was shown as 0.00
The Stage B2 safe pairwise classifier was evaluated on a degenerate single-class test split in which the test labels contained only class 0. Accuracy stayed at 1.0000 because every test sample belonged to the same class and was predicted correctly. F1-score was 0.0000 because the positive class was absent, so the positive-class F1 was undefined in practice and was recorded as zero by the metric implementation.

## Healing strategy count
Verified healing identifiers:
- Unique healing_id values in the verified dataset: H0, H1, H2, H3, H4
- Unique candidate_healing_id values in the raw Phase 04 export: H0, H1, H2, H3, H4
- Unique active healing methods used in Model C: H1, H2, H3, H4

The H1-H7 wording is not supported by the verified dataset and should not be used.

## Final ML result table
| Model | Dataset used | Target | Feature type | Best algorithm | Validation metric | Test metric | Safe for report? | Interpretation |
|---|---|---|---|---|---|---|---|---|
| Model A - Recovery-time regression | Official Phase 04 verified dataset with official S1-S11 split | traffic_recovery_delay_s | Pre-recovery features only | DecisionTreeRegressor | R2 = 1.0000 | R2 = 1.0000 | Yes, with limitations | Recovery delay is deterministic in the tested domain; leakage removal did not reduce performance. |
| Model B1 - Delivery ratio prediction | Official Phase 04 verified dataset with official S1-S11 split | final_agg_delivery_ratio | Pre-recovery features only | DecisionTreeRegressor | R2 = 1.0000 | R2 = 1.0000 | Yes, with limitations | Delivery outcome is deterministic in the tested domain. |
| Model B2 - Energy consumed prediction | Official Phase 04 verified dataset with official S1-S11 split | final_consumed_j | Pre-recovery features only | DecisionTreeRegressor | R2 = 0.1200 | R2 = -1.9995 | No | Energy consumption is not reliably predictable from pre-recovery features. |
| Model B3 - Recovered clusters prediction | Official Phase 04 verified dataset with official S1-S11 split | final_recovered_clusters | Pre-recovery features only | DecisionTreeRegressor | R2 = 1.0000 | R2 = 1.0000 | Yes, with limitations | Cluster recovery is deterministic in the tested domain. |
| Model C - Pairwise healing classifier | Raw Phase 04 export and verified pairwise labels | active_healing_beats_H0 | Pre-recovery features only | DecisionTreeClassifier | B1: F1 = 1.0000; B2 safe check: F1 = 0.0000 | B1: Accuracy = 1.0000; B2 safe check: Accuracy = 1.0000 | Yes, with limitations | The classifier is deterministic on the verified B1 artifact, but the safe B2 recheck used a single-class test split. |

## Safe and unsafe claims
### Safe claims
- Recovery delay can be predicted within the tested simulation domain using pre-recovery network features.
- Pairwise active-healing benefit over H0 can be identified within comparable tested scenarios.
- Delivery and cluster recovery outcomes show deterministic behavior in this dataset.
- Leakage-free models reproduce the same conclusions for recovery delay, delivery ratio, and cluster recovery.

### Unsafe claims
- The ML model globally chooses the best healing method among H0, H1, H2, H3, and H4.
- The ML model reliably predicts energy consumption.
- The ML model generalizes to all real wireless sensor network deployments.
- The current results prove universal superiority of the healing strategies outside the tested domain.

## Final feature importance summary
### Model A safe
Top features:
- low_nodes: 0.878556
- scale_S2: 0.087597
- scale_S5: 0.023242
- scale_S7: 0.005026
- scale_S4: 0.004184

### Model B safe - delivery ratio
Top features are all zero importance, which indicates a deterministic split rather than a feature-graded relationship.

### Model B safe - energy consumed
Top features:
- low_nodes: 0.843772
- cluster_count: 0.097816
- load_L2: 0.034107
- scale_S6: 0.020282
- node_count: 0.003187

### Model B safe - recovered clusters
Top feature:
- variant_V3: 1.000000

### Model C safe
All reported feature importances are zero in the saved summary, which means the safe recheck did not produce a useful feature ranking.

## Why the energy model failed
The energy target remained poor after leakage removal. The best safe decision tree achieved R2 = -1.9995, which is worse than a baseline mean predictor. This indicates that pre-recovery features alone do not capture the main drivers of energy consumption during recovery, or that the energy target is highly variable across runs.

## Final report-ready explanation
### ML dataset source
The ML results were produced from the official Phase 04 verified export. The dataset was reconciled to 1148 rows after removing two extra database rows, and the official split was fixed as S1-S9 for training, S10 for validation, and S11 for testing.

### ML split strategy
The split was not random. It was based on the official run manifest, and S11 was reserved as the final test set. No test data was used for training or tuning.

### Model types
Three model families were evaluated: recovery-time regression, run-outcome regression, and pairwise healing classification.

### Leakage audit
Stage B2 found 56 unsafe features in Stage B1, mostly post-simulation outcomes and recovery timing variables. These were removed before training the safe models.

### Safe model results
The safe models preserved the key conclusions for recovery delay, delivery ratio, and cluster recovery. Energy consumption remained difficult to predict and produced negative R2.

### Limitations
The results are limited to the tested wireless sensor network domain and the verified seed-based split. Perfect scores do not prove generalization to other deployments.

### Final ML contribution
The final ML contribution is a leakage-audited, pre-recovery analysis of healing performance that identifies deterministic recovery behavior for several targets and highlights energy prediction as an unresolved problem.

## Viva explanation
See [PHASE05_STAGEC_VIVA_EXPLANATION.md](PHASE05_STAGEC_VIVA_EXPLANATION.md) for a short viva-ready script.
