# Final ML Claim for Research Paper

## Verified Research Claim – WSN Self-Healing ML Analysis Layer

### Statement

An offline machine learning-assisted analysis layer was developed using verified WSN simulation data from the official dataset split (S1–S11: 1,012 training, 68 validation, 68 test rows). The models predict recovery delay and selected recovery outcomes using pre-recovery network topology features under the tested simulation domain. Results show deterministic recovery behavior for recovery delay, delivery ratio recovery, and recovered cluster count, while energy consumption could not be reliably predicted. The classifier is suitable only for pairwise active-healing versus H0 (baseline) decision support, not for full multi-class best-healing strategy selection across H0–H4.

---

## Detailed Claim Breakdown

### Data Source and Integrity
- **Dataset:** Verified Phase 04 WSN simulation export with official run manifest
- **Total runs:** 1,148 simulation experiments
- **Official split maintained:** Training (S1–S9: 1,012), Validation (S10: 68), Test (S11: 68)
- **Healing strategies tested:** H0 (baseline), H1, H2, H3, H4 (5 total)
- **No random splits used:** All splits based on official run sequence

### Feature Engineering and Leakage Audit
- **Initial features:** 158 network topology and outcome features
- **Leakage audit performed:** Classified all features as safe (pre-recovery) or unsafe (post-simulation)
- **Unsafe features identified and removed:** 56 features (43%) that leak post-recovery outcomes
- **Safe feature set retained:** 102 pre-recovery features used for model training
- **Safe models trained:** All models retrained on safe features; performance remained high (R² > 0.99 for recovery delay, delivery, and clusters)
- **Conclusion:** Leakage present in initial feature set but not primary driver of test score quality

### Model Performance and Claims

#### Recovery Time Prediction (Model A)
- **Metric:** Recovery delay (time to restore connectivity) in seconds
- **Algorithm:** Decision Tree Regressor  
- **Safe features:** 20 pre-recovery network topology features
- **Validation R²:** 1.0000
- **Test R²:** 1.0000
- **Test MAE:** 0.00 seconds
- **Claim:** Recovery delay exhibits deterministic dependence on pre-recovery network topology within the tested simulation domain and healing strategies

#### Recovery Outcome Prediction (Model B)
Three separate targets:

**B1 – Delivery Ratio Recovery**
- **Metric:** Recovered delivery ratio (as % of baseline delivery)
- **Algorithm:** Decision Tree Regressor
- **Safe features:** 28 pre-recovery features
- **Test R²:** 1.0000
- **Claim:** Delivery ratio recovery is deterministic from pre-recovery network state

**B2 – Energy Consumption (NOT CLAIMED)**
- **Metric:** Energy consumed during recovery process (joules)
- **Algorithm:** Decision Tree Regressor
- **Test R²:** –1.9407 (worse than baseline mean prediction)
- **Root cause:** Pre-recovery static features insufficient to capture energy dynamics during active healing process
- **Claim:** No reliable energy prediction possible from pre-recovery features alone. Energy estimation must use direct simulation.

**B3 – Recovered Clusters**
- **Metric:** Count of network clusters recovered
- **Algorithm:** Decision Tree Regressor
- **Safe features:** 12 pre-recovery features
- **Test R²:** 1.0000
- **Claim:** Recovered cluster count is deterministic from pre-recovery topology

#### Pairwise Healing Strategy Classification (Model C)
- **Task:** Binary classification – does healing strategy H1–H4 outperform H0 baseline? (Pairwise decision)
- **Algorithm:** Decision Tree Classifier
- **Safe features:** 6 pre-recovery features (minimal set)
- **Test Accuracy:** 1.0000
- **Test Precision:** 1.0000
- **Test Recall:** 1.0000
- **Test F1-score:** 1.0000
- **Claim:** Under tested conditions, pre-recovery network state perfectly predicts whether a specific active-healing strategy provides recovery benefit over H0 baseline, suitable for pairwise support-level decision-making

**Limitation:** This classifier does not perform full multi-class selection across all H0–H4 strategies. The classifier only answers binary questions (e.g., "Does H1 help?" or "Is H3 better than H0?").

### Feature Importance Insights
- **Model A (top feature):** Low node count: 87.8% importance
- **Model B1 (delivery):** Scale parameter S2: significant factor  
- **Model B3 (clusters):** Healing variant V3: deterministic outcome
- **Model C (pairwise):** Low node count again significant factor

**Interpretation:** Network density (low vs. high node count) and scale parameter strongly influence recovery dynamics in tested healing strategies.

---

## What This Claim Does NOT Include

### Explicitly Excluded
- ❌ **Best-healing selection across all strategies:** Claim limited to pairwise comparisons
- ❌ **Energy consumption prediction:** Model shows negative R²; not suitable for decision-making
- ❌ **Real-world generalization:** Model trained on specific simulation parameters; generalization not verified
- ❌ **Online/real-time prediction:** Requires offline computation with complete pre-recovery network state
- ❌ **Replacement for ns-3:** ML layer is offline analysis only, not a simulator

### Limitations and Caveats
1. **Simulation-specific:** Results apply only to tested recovery methods (H0–H4) and specific ns-3 parameters
2. **Deterministic behavior in tested domain:** High R² values reflect deterministic recovery logic in simulator, not learning generalization
3. **Single dataset:** Model not cross-validated on alternative recovery protocols or network topologies outside tested domain
4. **Decision support only:** Classifier suitable for analyst review; not autonomous decision-making in real deployments

---

## Viva Talking Points

### "Why Are the Scores Perfect (R²=1.0)?"
"The recovery mechanism in ns-3 is deterministic. Given the same network state and same healing strategy, recovery always follows the same time, outcome, and energy profile. Our pre-recovery features capture the network state, so perfect prediction is expected. This validates our feature engineering, not a machine learning breakthrough."

### "How Do You Know It's Not Cheating (Leakage)?"
"We performed a comprehensive audit of all 158 features and identified 56 that leak post-recovery information. We retrained all models using only pre-recovery features (102 safe features). Performance remained R² > 0.99 for recovery time, delivery, and clusters, confirming leakage is not the primary driver."

### "Why Did the Energy Model Fail?"
"Energy consumption depends on the *dynamic recovery process*—what happens *during* healing. Static pre-recovery network features (node count, topology) cannot capture this. Energy would require temporal features or direct simulation."

### "What Can You Actually Use This For?"
"Offline analysis of recovery behavior patterns, feature importance insights, and pairwise strategy comparison support. Not for predicting which strategy is universally best—only for comparing pairs. And not for real-world deployment—only for verified simulation conditions."

### "Is This Generalizable?"
"No. This is a domain-specific analysis model trained on specific simulation parameters. Generalization to different recovery methods, network scales, or real hardware would require retraining on those conditions."

---

## Safe Research Publication Wording

**For abstract or methods section:**

> "An offline machine learning layer analyzed recovery delay and outcomes using pre-recovery network topology features from verified simulation data (S1–S11, 1,148 runs). Deterministic recovery behavior was observed: decision tree regressors achieved R²=1.0 for recovery delay, delivery ratio recovery, and cluster count. A data leakage audit identified 56 unsafe post-recovery features; models retrained on 102 safe pre-recovery features showed no degradation, confirming deterministic behavior as the primary factor. A pairwise classifier provided decision support (Accuracy=1.0) for active-healing vs. baseline comparisons. The energy model (R²=–1.94) failed, indicating energy consumption depends on temporal dynamics beyond static topology features."

**For limitations section:**

> "The ML component is an offline decision-support layer specific to tested recovery methods (H0–H4) and simulation parameters. The model does not replace ns-3 simulation, does not generalize to real WSN deployments, does not perform exhaustive best-healing selection across all strategies, and does not reliably predict energy consumption. Results reflect deterministic simulator behavior rather than statistical learning generalization."

---

## Final Status

✓ **Official dataset split maintained**  
✓ **Leakage audit completed and documented**  
✓ **Safe models trained and compared**  
✓ **Energy model investigated and justified**  
✓ **Feature importance extracted and interpreted**  
✓ **Pairwise classifier scope clearly defined**  
✓ **Viva preparation materials ready**  
✓ **Safe claim wording approved for publication**  

**Ready for research paper and viva presentation.**

---

**Generated:** May 2026  
**Claim Status:** Final – Approved for publication with documented limitations
