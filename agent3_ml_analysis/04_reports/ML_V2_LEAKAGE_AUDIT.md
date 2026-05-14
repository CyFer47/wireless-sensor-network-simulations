# ML Workspace V2 - Leakage Audit Report

## Overview
This report documents the data leakage prevention strategy for ML Workspace V2. All three models are trained with strict leakage prevention rules to ensure valid, generalizable results.

## Forbidden Columns (All Models)

The following columns are explicitly forbidden as features in all models:

### Metadata & Administrative
- `run_id` - Simulation run identifier (not predictive)
- `experiment_version` - Experiment version (not predictive)
- `map_signature` - Map identifier (not predictive)
- `base_condition_key` - Base scenario identifier (not predictive)

### Split & Test Information
- `split` - Train/validation/test indicator (CRITICAL: would leak information)

### Healing Performance (Past/Derived)
- `best_healing_id` - Best healing method (from simulation - not from features)
- `best_healing_id_derived` - Derived best healing ID
- `score_v1` - Previous scoring
- `best_score_v1` - Previous best score
- `candidate_is_best` - Target leakage
- `is_best_candidate` - Target leakage
- `is_best_candidate_derived` - Target leakage

### Model-Specific Target Columns (as Features)
- `active_healing_beats_H0` - Model C target (not a feature)
- `traffic_recovery_delay_s` - Model A target (not a feature)
- `final_agg_delivery_ratio` - Model B target (not a feature)
- `final_consumed_j` - Model B target (not a feature)
- `final_recovered_clusters` - Model B target (not a feature)

## Model A: Recovery Time Regression

### Dataset
`DATA/01_official_ml_dataset/ml_recovery_time_regression.csv`

### Target Variable
- `traffic_recovery_delay_s` - Time to recover network traffic after failure

### Leakage Prevention
- Does NOT use `traffic_recovery_delay_s` as a feature (it's the target)
- Removes all forbidden columns before feature engineering
- Uses official split from `split` column (train=1012, validation=68, test=68)
- Does NOT use S11 (test set) for training or hyperparameter tuning

### Valid Features
Only features derived from network conditions, simulation parameters, and physical properties. Examples:
- Network topology features
- Node properties
- Initial failure configuration
- Recovery mechanism parameters (NOT including outcomes)

## Model B: Run Outcomes Regression

### Dataset
`DATA/01_official_ml_dataset/ml_run_outcomes.csv`

### Target Variables
- `final_agg_delivery_ratio` - Delivery ratio achieved after healing
- `final_consumed_j` - Energy consumed during run
- `final_recovered_clusters` - Number of clusters recovered

### Leakage Prevention
- Does NOT use any of the three target columns as features
- Removes all forbidden columns before feature engineering
- Uses official split from `split` column
- Previous energy prediction was weak/unusable - re-checking without overclaiming

### Valid Features
Network and recovery configuration features, not including outcome measurements.

### Note on Energy Prediction
Energy prediction showed poor R² previously. This model re-checks the relationship but does not overclaim reliability if R² remains low.

## Model C: Pairwise Active-Healing vs H0 Classifier

### Dataset
`DATA/02_derived_labels/ml_best_healing_labels_derived_from_db_v1.csv`

### Target Variable
- `active_healing_beats_H0` - Binary: Does active healing outperform baseline (H0)?

### Important Scope
**Model C is NOT a full 5-way best-healing selector.**
**Model C is specifically: Active healing vs H0 (baseline) only.**
Other healing methods (H1, H2, H3, H4) are not part of this model.

### Leakage Prevention
- Does NOT use `active_healing_beats_H0` as a feature (it's the target)
- Removes all best-healing identifiers
- Removes all healing method indicators
- Uses only network condition and failure features

### Valid Features
Configuration and condition features that influence whether active healing helps.

## Data Split Strategy

### Official Split Rule
```
Train:      S1-S9   (1012 samples)
Validation: S10     (68 samples)
Test:       S11     (68 samples)
```

### No Random Split
- The official split is used WITHOUT randomization
- S11 (test set) is NEVER used for training or hyperparameter tuning
- Validation set (S10) may be used for early stopping only

## Implementation in Code

The `common_preprocessing.py` module enforces these rules:

1. **FORBIDDEN_FEATURES** - Set of all forbidden columns
2. **check_leakage()** - Detects forbidden columns in data
3. **remove_leakage_columns()** - Removes forbidden columns safely
4. **prepare_features_and_target()** - Separates features/target with leakage checking
5. **get_train_val_test_split()** - Uses official split (not random)

## Verification Checklist

- [x] Forbidden columns documented
- [x] Model-specific target columns identified
- [x] Official split validated (1012/68/68)
- [x] Random split NOT used
- [x] S11 NOT used for training/tuning
- [x] Preprocessing module enforces leakage rules
- [x] Each model script calls leakage prevention functions

## Safe Claims

Based on this leakage prevention strategy, the following claims are safe:

1. **Model A results** - Valid within the tested simulation domain (S1-S9 training, S10 validation, S11 test)
2. **Model B results** - Valid for trained metrics (delivery ratio, recovered clusters)
3. **Model B energy** - Results reported but not overclaimed if R² is poor
4. **Model C results** - Valid pairwise comparison (active healing vs H0 only)

## Unsafe Claims

These claims are explicitly NOT made:

1. **Model C is NOT** a full 5-way best-healing selector
2. **Energy prediction is NOT** claimed as reliable if R² < 0.5
3. **Results are NOT** generalizable to untested scenarios outside S1-S9
4. **Random split results are NOT** presented (only official split used)
5. **S11-trained models are NOT** reported as valid

---

**Report Generated**: ML Workspace V2  
**Location**: `08_REPORTS/ML_V2_LEAKAGE_AUDIT.md`
