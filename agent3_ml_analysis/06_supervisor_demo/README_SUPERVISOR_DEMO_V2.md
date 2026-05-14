# Supervisor Demo - ML Workspace V2

This directory contains a demonstration script for supervisor review of the ML training work.

## Quick Start

```bash
cd 10_SUPERVISOR_DEMO
python run_supervisor_demo_v2.py
```

## What the Demo Shows

The `run_supervisor_demo_v2.py` script displays:

1. **Dataset Verification**
   - Row counts for all official ML datasets
   - Verification that files match expected sizes

2. **Official Split Confirmation**
   - Train set: S1–S9 (1012 scenarios)
   - Validation set: S10 (68 scenarios)
   - Test set: S11 (68 scenarios)

3. **Model A Results (Recovery Time)**
   - Training metrics for all 4 models evaluated
   - Best model selection (Decision Tree)
   - Test set performance (R² = 1.0)

4. **Model B Results (Run Outcomes)**
   - Metrics for 3 targets (delivery ratio, energy, recovered clusters)
   - 3 models per target
   - ⚠️ Highlights energy prediction failure (R² = -1.94)

5. **Model C Results (Pairwise Classifier)**
   - Binary classification metrics
   - Class distribution
   - ⚠️ Highlights class imbalance affecting minority class

6. **Safe vs Unsafe Claims**
   - Explicitly lists what CAN be reported
   - Explicitly lists what CANNOT be reported

## Expected Output

```
Dataset Verification
- ml_run_outcomes.csv: 1148 rows
- ml_healing_candidates.csv: 1148 rows
- ml_best_healing_labels.csv: 636 rows
- ml_recovery_time_regression.csv: 520 rows
- dataset_split_manifest.csv: 1148 rows

Official Split
✅ Train (S1-S9): 1012 scenarios
✅ Val (S10): 68 scenarios
✅ Test (S11): 68 scenarios
   Total: 1148 scenarios

[Model A/B/C results...]

Safe Claims
✅ Model A predicts recovery time
✅ Model B predicts delivery ratio
❌ Model B energy prediction is not usable
✅ Official split maintained

Unsafe Claims
❌ Model B energy
❌ Model C as best-heating selector
❌ Using S11 for tuning
```

## Key Points for Supervisor

### What Went Well

✅ **Model A**: Strong performance predicting recovery time (R² = 1.0)  
✅ **Model B Delivery & Clusters**: Perfect fit (R² = 1.0)  
✅ **Official Split**: Properly maintained across all training  
✅ **Data Integrity**: All datasets verified  
✅ **Leakage Prevention**: Forbidden features properly excluded  

### Issues to Discuss

⚠️ **Model B Energy**: Shows severe overfitting and poor generalization (test R² = -1.94)
- **Recommendation**: Do NOT include energy predictions in final results

⚠️ **Model C Class Imbalance**: Test set heavily skewed (76.5% class 0)
- **Recommendation**: Useful for comparative analysis, not for automated decisions

⚠️ **Perfect Fit in A & B**: May indicate:
- Strong feature engineering OR
- Overfitting to specific domain

### Compliance Notes

✅ **No random splits** - Official split from dataset_split_manifest.csv used  
✅ **S11 protected** - Only used for final testing, not training/tuning  
✅ **Data leakage prevented** - Forbidden columns explicitly removed  
✅ **No database changes** - PostgreSQL unchanged  
✅ **No simulations** - Only training on existing datasets  

## Files Referenced by Demo

- `01_DATA_INPUT/DATA/01_official_ml_dataset/` - Original datasets
- `06_RESULTS/MODEL_A_RESULTS.json` - Model A metrics
- `06_RESULTS/MODEL_B_RESULTS.json` - Model B metrics
- `06_RESULTS/MODEL_C_RESULTS.json` - Model C metrics

## Next Steps After Review

1. Discuss findings with supervisor
2. Address energy prediction issue (exclude or note as unreliable)
3. Clarify Model C scope (pairwise, not full selector)
4. Prepare GitHub upload (see 11_GITHUB_READY folder)

## Troubleshooting

**"No module named 'pandas'"**
- Ensure `.venv` is activated
- Run: `pip install pandas numpy scikit-learn`

**"Results not found"**
- Ensure scripts in `04_TRAINING_SCRIPTS/` have been run
- Check that `06_RESULTS/` contains JSON files

**"Split manifest not found"**
- Verify `01_DATA_INPUT/DATA/` structure is correct
- Ensure dataset_split_manifest.csv exists in official_ml_dataset folder

---

**Status**: Ready for supervisor review  
**Date**: 2026-05-15
