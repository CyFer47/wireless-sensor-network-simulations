# PHASE 05 STAGE C - Final Feature Importance Summary

## Model A safe - Recovery-time regression
Best algorithm: DecisionTreeRegressor

Top features:
1. low_nodes - 0.878556
2. scale_S2 - 0.087597
3. scale_S5 - 0.023242
4. scale_S7 - 0.005026
5. scale_S4 - 0.004184

Interpretation:
- Recovery delay is dominated by the low_nodes feature.
- The remaining predictors have much smaller influence.
- This supports a deterministic recovery-delay relationship in the tested domain.

## Model B safe - Delivery ratio prediction
Best algorithm: DecisionTreeRegressor

Top features:
- All reported feature importances are 0.0 in the saved summary.

Interpretation:
- The delivery ratio target behaves as a deterministic split rather than a graded feature-driven regression problem.

## Model B safe - Energy consumed prediction
Best algorithm: DecisionTreeRegressor

Top features:
1. low_nodes - 0.843772
2. cluster_count - 0.097816
3. load_L2 - 0.034107
4. scale_S6 - 0.020282
5. node_count - 0.003187

Interpretation:
- Energy consumption is mostly influenced by low_nodes and network size factors.
- The test R2 is still negative, so these features are not enough to make the target reliably predictable.

## Model B safe - Recovered clusters prediction
Best algorithm: DecisionTreeRegressor

Top feature:
- variant_V3 - 1.000000

Interpretation:
- Recovered clusters are fully determined by the healing variant in the safe model summary.
- This is a deterministic rule in the tested dataset.

## Model C safe - Pairwise healing classifier
Best algorithm: DecisionTreeClassifier

Saved summary:
- test accuracy: 1.0000
- test F1: 0.0000
- test confusion matrix: [[32]]

Interpretation:
- The safe recheck used a single-class test split, so the saved feature importance summary is not useful for ranking predictors.
- The zero F1 is a metric artifact of the degenerate class distribution, not evidence of a failed accuracy score.

## Energy model final status
Energy prediction is not usable as a reliable predictive result. It should be reported as an unresolved or weak target, not as a strong ML contribution.
