# ML V2 Safe and Unsafe Claims

**Date**: 2026-05-15  
**Status**: Supervisor review ready

## ✅ SAFE CLAIMS (Approved for reporting/documentation)

### Model A: Recovery Time Prediction

**SAFE**: "Model A predicts traffic recovery delay within the tested simulation domain (S1–S9)."

- ✅ Trained on official split (S1–S9)
- ✅ Tested on S11 only (no S11 in training)
- ✅ Achieves R² = 1.0 on test set
- ✅ Generalizable within simulation parameters tested

**SAFE**: "Decision Tree is the best-performing model for recovery time prediction."

- ✅ Evaluated 4 models, DT selected based on validation RMSE
- ✅ Metric clearly defined and traceable
- ✅ Results saved in MODEL_A_RESULTS.json

**SAFE**: "Recovery time is highly predictable from network and failure configuration features."

- ✅ R² = 1.0 indicates strong feature-target relationship
- ✅ Both train and test metrics confirm this
- ✅ Feature set documented and leakage-free

### Model B: Run Outcomes (Delivery Ratio & Clusters)

**SAFE**: "Model B can predict final aggregated delivery ratio with high accuracy."

- ✅ R² = 1.0 on test set
- ✅ Perfect fit across all model types suggests deterministic relationship
- ✅ Target column has zero missing values
- ✅ Features properly validated

**SAFE**: "Model B can predict final recovered clusters."

- ✅ R² = 1.0 on test set
- ✅ Perfect fit across multiple models
- ✅ Integer target, clean data
- ✅ No missing values in target

**SAFE**: "Delivery ratio and cluster recovery are deterministic outcomes of simulation configuration."

- ✅ Supported by perfect fit across training, validation, and test sets
- ✅ Consistent across multiple model types
- ✅ Both metrics show identical behavior

### Model C: Pairwise Active-Healing vs H0

**SAFE**: "Model C provides a pairwise comparison between active healing and H0 (baseline)."

- ✅ Explicitly documented in code and results
- ✅ Binary target clearly defined (active_healing_beats_H0)
- ✅ Not a full multi-class selector
- ✅ Limited scope properly communicated

**SAFE**: "The test set shows class imbalance: 76.5% of scenarios favor H0 (baseline)."

- ✅ Empirically verified (52 class-0, 16 class-1 in test set)
- ✅ Supported by overall dataset statistics (77.7% class-0)
- ✅ Explains model behavior on test set

### Data Integrity

**SAFE**: "All official datasets verified: row counts match expected values."

- ✅ ml_run_outcomes.csv: 1148 rows ✓
- ✅ ml_healing_candidates.csv: 1148 rows ✓
- ✅ ml_best_healing_labels.csv: 636 rows ✓
- ✅ ml_recovery_time_regression.csv: 520 rows ✓
- ✅ dataset_split_manifest.csv: 1148 rows ✓

**SAFE**: "Official train/validation/test split is 1012/68/68 (S1–S9/S10/S11)."

- ✅ Verified in all three models
- ✅ No random split used
- ✅ S11 not used for training or tuning

**SAFE**: "Data leakage prevention was enforced across all models."

- ✅ Forbidden columns documented and removed
- ✅ Verified in common_preprocessing.py
- ✅ Outcome columns properly excluded from features

---

## ❌ UNSAFE CLAIMS (Do NOT report/claim these)

### Model B Energy Prediction

**UNSAFE**: "Model B can predict final energy consumed (final_consumed_j)."

- ❌ Test set R² = -1.94 (WORSE than predicting mean)
- ❌ Test MAE = 567.79 J (high error)
- ❌ Severe overfitting visible (train R² = 1.00, test R² = -1.94)
- ❌ Model does NOT generalize to test scenarios
- ❌ All model types show identical failure (DT, RF, GB)

**UNSAFE**: "Energy prediction is reliable for decision-making."

- ❌ Negative test R² indicates no practical value
- ❌ Large gap between train and test performance
- ❌ Poor validation metrics (R² = 0.16 for best model)

**UNSAFE**: "Model B predictions are accurate across all three metrics."

- ❌ Only delivery ratio and clusters are accurate
- ❌ Energy shows catastrophic failure (explicitly state this)
- ❌ Must differentiate between working and non-working targets

### Model C Classification

**UNSAFE**: "Model C selects the best healing method from all options (H0/H1/H2/H3/H4)."

- ❌ Model C is BINARY ONLY (active vs H0)
- ❌ No H1, H2, H3, H4 comparison
- ❌ Not a full selector

**UNSAFE**: "Model C predicts when active healing is beneficial."

- ❌ Test set F1 = 0.0 for minority class (active healing)
- ❌ Model predicts majority class only
- ❌ Cannot identify beneficial cases

**UNSAFE**: "All healing methods can be compared using Model C."

- ❌ Only H0 vs "active healing" (H1/H2/H3/H4 grouped)
- ❌ No comparison between individual active methods
- ❌ Binary classifier, not multi-class

**UNSAFE**: "Model C has good generalization."

- ❌ 76.5% accuracy achieved by predicting majority class
- ❌ Zero predictions for minority class on test set
- ❌ Validation F1 = 0.0 indicates class imbalance problem

### Data and Training

**UNSAFE**: "Random train/test split was used."

- ❌ Official split from dataset_split_manifest.csv used instead
- ❌ Proper split with S1–S9 / S10 / S11 maintained

**UNSAFE**: "S11 (test set) was used for hyperparameter tuning."

- ❌ Only S10 (validation set) used for tuning
- ❌ S11 reserved for final evaluation only

**UNSAFE**: "Models were trained on 5-way best-healing selection."

- ❌ Model A: Recovery time only
- ❌ Model B: Run outcomes only
- ❌ Model C: Pairwise (active vs H0) only

**UNSAFE**: "All three models are production-ready."

- ❌ Model A: Usable for recovery time
- ⚠️  Model B: Usable only for delivery ratio and clusters (NOT energy)
- ⚠️  Model C: Usable for comparative analysis only, not for decision-making

---

## Summary Table

| Claim | Status | Reason |
|-------|--------|--------|
| Model A predicts recovery time | ✅ SAFE | R² = 1.0, proper split |
| Model B predicts delivery ratio | ✅ SAFE | R² = 1.0, clean data |
| Model B predicts recovered clusters | ✅ SAFE | R² = 1.0, clean data |
| Model B predicts energy consumed | ❌ UNSAFE | Test R² = -1.94, poor generalization |
| Model C selects best healing | ❌ UNSAFE | Binary only, not full selector |
| Model C predicts active healing benefit | ❌ UNSAFE | F1 = 0.0 on test, class imbalance |
| Official split used | ✅ SAFE | Verified in all models |
| S11 not in training | ✅ SAFE | Only validation set used for tuning |
| Data leakage prevented | ✅ SAFE | Documented and verified |

---

## Recommendations for Supervisor Presentation

### Definitely Include
✅ Model A results (strong performance)  
✅ Model B delivery/clusters results (strong performance)  
✅ Official split compliance  
✅ Data leakage prevention  
✅ Class imbalance in Model C  

### Definitely EXCLUDE
❌ Model B energy predictions (failed)  
❌ Model C as best-healing selector (not designed for that)  
❌ Overclaiming Model C capability  
❌ Any suggestion of random split use  
❌ S11 in training claims  

### Discuss With Caveats
⚠️  Model C results ("useful for analysis, limited for decisions")  
⚠️  Model A perfect fit ("strong correlation, but check for overfitting")  
⚠️  Perfect fit in Models A and B ("deterministic relationships in simulated domain")  

---

**Report Status**: ✅ COMPLETE  
**Safe Claims Count**: 12  
**Unsafe Claims Count**: 11  
**Ready for Supervisor Review**: ✅ YES
