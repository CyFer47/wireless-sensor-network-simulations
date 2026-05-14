# Agent 3: ML Workspace V2 Analysis

**Fresh Windows ML Workspace V2** - Complete machine learning analysis with three trained models on Wireless Sensor Network simulation data.

---

## Overview

Agent 3 contains the outputs of the fresh Windows ML Workspace V2, which focuses on offline machine learning analysis of WSN simulation results. The work uses the curated DATA folder as input and produces three trained models with comprehensive documentation.

## Agent 3 Purpose

- Analyze WSN run outcomes using supervised learning
- Predict recovery time and healing effectiveness
- Provide safe, validated claims about model capabilities
- Document limitations and prevent overclaimingoutcomes Prevent overfitting and data leakage

---

## Three Models

### Model A: Recovery Time Regression
**Target**: `traffic_recovery_delay_s` (time for network to recover traffic delivery)

- **Best Algorithm**: Decision Tree
- **Test Performance**: R² = 1.0 (perfect fit within tested domain)
- **Status**: ✅ USABLE
- **Use Case**: Predict recovery time given network configuration and failure scenario
- **Limitation**: Perfect fit may not generalize to real systems; valid within simulation domain S1-S11

### Model B: Run Outcomes Regression
**Targets**: Three regression tasks

1. **final_agg_delivery_ratio** (network delivery success rate)
   - **Best Algorithm**: Decision Tree
   - **Test Performance**: R² = 1.0
   - **Status**: ✅ USABLE

2. **final_consumed_j** (energy consumed by nodes)
   - **Best Algorithm**: Decision Tree
   - **Test Performance**: R² = -1.94 ❌ POOR GENERALIZATION
   - **Status**: ❌ NOT USABLE - Do not report this metric
   - **Reason**: Severe overfitting; test error exceeds baseline mean

3. **final_recovered_clusters** (number of clusters recovered)
   - **Best Algorithm**: Decision Tree
   - **Test Performance**: R² = 1.0
   - **Status**: ✅ USABLE

### Model C: Pairwise Active-Healing vs H0 Classifier
**Target**: Binary classification (Does active healing beat H0 baseline?)

- **Best Algorithm**: Decision Tree
- **Scope**: ⚠️ **BINARY ONLY** - Active healing vs H0 (NOT a 5-way selector)
- **Test Performance**: 76.5% accuracy (class 0), but minority class F1 = 0.0
- **Status**: ⚠️ LIMITED - Useful for comparative analysis, not decision-making
- **Class Distribution**: 77.7% class 0 (H0 best), 22.3% class 1 (active healing)
- **Limitation**: Severe class imbalance prevents minority class prediction

---

## Key Findings

✅ **What Works**
- Model A: Recovery time prediction is reliable
- Model B: Delivery ratio and cluster recovery are deterministic and predictable
- Official split maintained across all training (S1-S9 train / S10 val / S11 test)
- Data leakage prevention verified
- No S11 in training/tuning

❌ **What Doesn't Work**
- Model B energy prediction (R² = -1.94)
- Model C for automated decision-making (class imbalance)

⚠️ **Important Limitations**
- ML models are **offline analysis only** - not live closed-loop control
- Results valid in **tested simulation domain** (scenarios S1-S11)
- **Energy prediction is unreliable** - investigate simulator separately
- Model C is **pairwise comparison only** (H0 vs active healing)
- **No full 5-way best-healing selector** implemented or claimed

---

## Directory Structure

```
agent3_ml_analysis/
├── 00_START_HERE/                      <- Read these first
│   ├── README_AGENT3.md               (this file)
│   ├── README_ML_WORKSPACE_V2.md      (main overview)
│   ├── COMPLETION_SUMMARY.md          (what was done)
│   └── DOCUMENTATION_INDEX.md         (navigation guide)
│
├── 01_dataset_reference/               <- Data verification
│   └── DATA_VERIFICATION_REPORT.md    (dataset integrity checks)
│
├── 02_training_scripts/                <- Reproducible code
│   ├── common_preprocessing.py        (shared preprocessing)
│   ├── train_model_a_recovery_time.py
│   ├── train_model_b_outcomes.py
│   ├── train_model_c_pairwise_classifier.py
│   ├── prepare_model_c_data.py        (create dataset)
│   └── requirements.txt               (dependencies)
│
├── 03_results/                         <- Model outputs
│   ├── MODEL_A_RESULTS.json
│   ├── MODEL_B_RESULTS.json
│   ├── MODEL_C_RESULTS.json
│   └── FINAL_ML_V2_METRICS_TABLE.csv
│
├── 04_reports/                         <- Analysis reports
│   ├── ML_V2_TRAINING_REPORT.md       (detailed metrics)
│   ├── ML_V2_SAFE_AND_UNSAFE_CLAIMS.md (what to report)
│   ├── ML_V2_LEAKAGE_AUDIT.md         (data leakage prevention)
│   └── ML_FINAL_LIMITATIONS.md        (explicitly state limits)
│
├── 05_feature_importance/              <- Feature analysis
│   └── ML_V2_FEATURE_IMPORTANCE_SUMMARY.md
│
├── 06_supervisor_demo/                 <- Verification script
│   ├── run_supervisor_demo_v2.py
│   └── README_SUPERVISOR_DEMO_V2.md
│
├── 07_github_ready_notes/              <- Upload documentation
│   └── AGENT3_MANIFEST.md             (what's included/excluded)
│
└── AGENT3_MANIFEST.md                  (upload manifest)
```

---

## Quick Start Guide

### 1. Read Documentation (10 minutes)
- Start with `00_START_HERE/README_ML_WORKSPACE_V2.md`
- Review `04_reports/ML_V2_SAFE_AND_UNSAFE_CLAIMS.md`
- Check `04_reports/ML_FINAL_LIMITATIONS.md` for limitations

### 2. Run the Demo (5 minutes)
```bash
cd 06_supervisor_demo
python run_supervisor_demo_v2.py
```
Output shows:
- Dataset verification
- Split confirmation
- All model metrics
- Safe/unsafe claims

### 3. Reproduce Results (30+ minutes)
```bash
# Create environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r 02_training_scripts/requirements.txt

# Prepare and train models
cd 02_training_scripts
python prepare_model_c_data.py
python train_model_a_recovery_time.py
python train_model_b_outcomes.py
python train_model_c_pairwise_classifier.py
```

### 4. Review Results
- Check `03_results/FINAL_ML_V2_METRICS_TABLE.csv` for summary
- Review JSON files for detailed metrics per model
- See `04_reports/ML_V2_TRAINING_REPORT.md` for analysis

---

## Critical Statements

### Energy Prediction is NOT Usable
> "Model B energy prediction shows severe overfitting with test R² = -1.94. This indicates predictions are worse than simply predicting the mean. **Do not use energy predictions for any decisions.** See ML_FINAL_LIMITATIONS.md for details."

### Model C is Pairwise Only
> "Model C is a **binary classifier** comparing active healing vs H0 baseline only. It is NOT a 5-way best-healing selector. No claims are made about selecting between H0, H1, H2, H3, and H4."

### ML is Offline Analysis
> "These models perform offline analysis of simulation results. They are not live closed-loop control systems. Results are valid only within the tested simulation domain (S1-S11)."

---

## Data Flow

```
Official DATA folder (input)
         ↓
Dataset verification (DATA_VERIFICATION_REPORT.md)
         ↓
Common preprocessing (common_preprocessing.py)
         ↓
Three training pipelines:
├─→ Model A: Recovery Time (train_model_a_recovery_time.py)
├─→ Model B: Outcomes (train_model_b_outcomes.py)
└─→ Model C: Pairwise (train_model_c_pairwise_classifier.py)
         ↓
Results JSON files (MODEL_A/B/C_RESULTS.json)
         ↓
Analysis reports (04_reports/*.md)
         ↓
Supervisor demo (run_supervisor_demo_v2.py)
```

---

## Safety & Compliance

✅ **Data Split**
- Uses official S1-S9 / S10 / S11 split from dataset_split_manifest.csv
- No random splits
- S11 protected (test only, not training/tuning)

✅ **Leakage Prevention**
- 18 forbidden columns identified and excluded
- All features validated before training
- See ML_V2_LEAKAGE_AUDIT.md for details

✅ **No Model Modifications**
- Models saved as-is in joblib format (not included in GitHub upload)
- Scripts allow full reproduction

✅ **No Database Changes**
- PostgreSQL unchanged
- Only analysis of existing data

✅ **No Simulations Run**
- Training uses existing simulation outputs only
- No new data generated

---

## Recommended Reading Order

**For Quick Review (15 minutes)**
1. This file (README_AGENT3.md)
2. README_ML_WORKSPACE_V2.md (section: Safe Claims)
3. Run `python 06_supervisor_demo/run_supervisor_demo_v2.py`

**For Detailed Review (45 minutes)**
1. All of quick review above
2. ML_V2_TRAINING_REPORT.md (all model results)
3. ML_V2_SAFE_AND_UNSAFE_CLAIMS.md (complete list)
4. ML_FINAL_LIMITATIONS.md (what not to claim)

**For Complete Understanding (90+ minutes)**
1. All of detailed review above
2. DATA_VERIFICATION_REPORT.md (data integrity)
3. ML_V2_LEAKAGE_AUDIT.md (prevention details)
4. ML_V2_FEATURE_IMPORTANCE_SUMMARY.md (feature analysis)
5. Training scripts (see how it works)

---

## FAQ

**Q: Can I use Model B energy predictions?**  
A: No. Test R² = -1.94 indicates poor generalization. See ML_FINAL_LIMITATIONS.md.

**Q: Is Model C a best-healing selector?**  
A: No. Model C is binary only (active vs H0). It's not a 5-way selector.

**Q: What Python version?**  
A: Python 3.11+ (check requirements.txt)

**Q: Are the official data splits maintained?**  
A: Yes. All training uses official S1-S9 / S10 / S11 split. See DATA_VERIFICATION_REPORT.md.

**Q: Can I run this on new data?**  
A: Yes. Modify file paths in training scripts. Note: Energy prediction may still be unreliable.

**Q: Is this production-ready?**  
A: No. This is offline analysis. Perfect fits may not transfer to real systems. See ML_FINAL_LIMITATIONS.md.

---

## Connection to Agents 1 & 2

- **Agent 1** - WSN Simulation Framework and infrastructure
- **Agent 2** - Data collection and curation pipeline
- **Agent 3** - ML analysis on curated Agent 2 data (this folder)

Agent 3 uses DATA folder prepared by Agent 2 and analyzes it with ML models.

---

## Contact & Questions

For questions about:
- **Data verification** → See 01_dataset_reference/
- **Training details** → See 04_reports/
- **Safe claims** → See 04_reports/ML_V2_SAFE_AND_UNSAFE_CLAIMS.md
- **Limitations** → See 04_reports/ML_FINAL_LIMITATIONS.md
- **How to run** → See 06_supervisor_demo/README_SUPERVISOR_DEMO_V2.md
- **GitHub structure** → See AGENT3_MANIFEST.md

---

**Agent 3 Status**: ✅ Complete  
**Models Trained**: 3  
**Reports Generated**: 9  
**Supervisor Demo**: Ready  
**GitHub Upload**: Ready  
**Date**: 2026-05-15
