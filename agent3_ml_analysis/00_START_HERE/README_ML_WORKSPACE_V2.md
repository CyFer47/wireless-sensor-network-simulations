# ML Workspace V2 - Start Here

Welcome to the ML Workspace V2 - Fresh Windows Training setup.

## Quick Start

This directory contains a complete machine learning training pipeline for WSN (Wireless Sensor Network) modeling with three trained models.

## Workspace Structure

```
00_START_HERE/          <- You are here
01_DATA_INPUT/DATA/     <- Official datasets (verified)
02_DATA_VERIFICATION/   <- Data integrity reports
03_PREPROCESSING/       <- Preprocessing documentation
04_TRAINING_SCRIPTS/    <- Model training code
05_MODELS/              <- Saved trained models
06_RESULTS/             <- Model results (JSON/CSV)
07_FIGURES/             <- Visualizations (empty)
08_REPORTS/             <- Final reports
09_FEATURE_IMPORTANCE/  <- Feature importance analysis
10_SUPERVISOR_DEMO/     <- Demo script for supervisor review
11_GITHUB_READY/        <- Safe files for upload (not yet pushed)
```

## Models Trained

### Model A: Recovery Time Regression
- **Target**: `traffic_recovery_delay_s` (time to recover network traffic)
- **Dataset**: 520 samples (456 train, 32 val, 32 test)
- **Best Model**: Decision Tree
- **Test Metrics**:
  - MAE: 0.0
  - RMSE: 0.0
  - R²: 1.0
- **Note**: Perfect fit suggests possible overfitting to the specific domain

### Model B: Run Outcomes Regression
- **Targets**: 
  - `final_agg_delivery_ratio` (network delivery ratio)
  - `final_consumed_j` (energy consumed)
  - `final_recovered_clusters` (clusters recovered)
- **Dataset**: 1148 samples (1012 train, 68 val, 68 test)
- **Best Models**: Decision Tree for all targets
- **Key Finding**: Energy prediction (final_consumed_j) shows poor generalization (test R²=-1.94) - **NOT RELIABLE**

### Model C: Pairwise Active-Healing vs H0 Classifier
- **Target**: `active_healing_beats_H0` (binary: does active healing beat baseline H0?)
- **Dataset**: 1150 candidate samples (1012 train, 68 val, 68 test)
- **Class Distribution**: 78% H0-best, 22% active-healing-best
- **Best Model**: Decision Tree
- **Test Metrics**: Predicts majority class on test set (F1=0.0 for minority class)
- **Note**: Severe class imbalance limits minority class prediction

## Important Scope Notes

**Model C is NOT a full 5-way best-healing selector.**
- Model C specifically compares: **Active Healing vs H0 (baseline) only**
- This is a pairwise binary classifier, not a multi-class selector

**Data Split Strategy**
- Train: S1–S9 (1012 scenarios)
- Validation: S10 (68 scenarios)
- Test: S11 (68 scenarios)
- **No random split used** - official split maintained

**Official Split Source**
- Defined in: `01_DATA_INPUT/DATA/01_official_ml_dataset/dataset_split_manifest.csv`
- All models use this official split, never S11 for training

## Safe Claims (Safe to Report)

✅ **Model A**: Predicts recovery delay within tested simulation domain (S1–S9)  
✅ **Model B Delivery/Clusters**: Can estimate delivery ratio and recovered clusters  
❌ **Model B Energy**: NOT reliable - poor generalization (test R² = -1.94)  
✅ **Model C**: Pairwise comparison valid - Active Healing vs H0 only  
❌ **Model C**: NOT a full best-healing selector (no H1/H2/H3/H4 comparison)  

## Files to Review

- **DATA_VERIFICATION_REPORT.md** - Data integrity verification
- **ML_V2_LEAKAGE_AUDIT.md** - Data leakage prevention details
- **ML_V2_TRAINING_REPORT.md** - Detailed training log
- **ML_V2_SAFE_AND_UNSAFE_CLAIMS.md** - Complete safe/unsafe claims list
- **MODEL_A_RESULTS.json** - Model A results
- **MODEL_B_RESULTS.json** - Model B results  
- **MODEL_C_RESULTS.json** - Model C results
- **FINAL_ML_V2_METRICS_TABLE.csv** - Summary metrics table

## Running the Demo

```bash
cd 10_SUPERVISOR_DEMO
python run_supervisor_demo_v2.py
```

This will print:
- Dataset row counts
- Split verification
- All model metrics
- Safe and unsafe claims

## Next Steps

1. Review data verification report
2. Review leakage audit and safe claims
3. Run supervisor demo
4. Review feature importance summaries
5. Prepare for GitHub upload (use 11_GITHUB_READY/)

## Important Restrictions

⚠️ **Do NOT:**
- Modify PostgreSQL database
- Run simulations from this workspace
- Use random train/test splits
- Use S11 for training or hyperparameter tuning
- Train full 5-way classifiers
- Overclaim energy prediction reliability

## Contact

For questions about this workspace, review the markdown documentation files in the 08_REPORTS directory.

---

**Workspace Version**: V2 (Fresh Windows Training)  
**Created**: 2026-05-15  
**Data Verified**: Yes  
**Training Complete**: Yes  
**Ready for Review**: Yes  
