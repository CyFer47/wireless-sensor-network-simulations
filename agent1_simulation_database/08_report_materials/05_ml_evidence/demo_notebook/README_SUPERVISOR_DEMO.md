# Supervisor ML Demo

This folder contains a compact notebook and a backup script for a live supervisor demonstration of the verified Phase 05 / Stage C machine learning results.

## Folder layout
- `01_data/` - copied verified input files used by the demo
- `02_notebooks/` - the Jupyter notebook for step-by-step presentation
- `03_demo_scripts/` - backup script for terminal use
- `04_demo_outputs/` - demo outputs created during local runs
- `05_saved_models/` - copied safe model artifacts for quick loading

## Install requirements
From this folder, install the minimum packages:

```bash
pip install -r requirements.txt
```

Required packages:
- pandas
- numpy
- scikit-learn
- matplotlib
- joblib
- jupyter

## Open the notebook
Open `02_notebooks/WSN_ML_SUPERVISOR_DEMO.ipynb` in Jupyter or VS Code and run the cells in order.

The notebook is organized as:
1. Demo introduction
2. Import libraries
3. Load datasets
4. Verify official split
5. Explain why random split is not used
6. Model A - Recovery-time regression
7. Model B1 - Delivery ratio regression
8. Model B2 - Energy consumed regression
9. Model B3 - Recovered clusters regression
10. Model C - Pairwise healing classifier
11. Feature importance
12. Safe claims and unsafe claims
13. Final viva explanation

## Run the backup script
Use the script if you want a terminal-based walkthrough:

```bash
python 03_demo_scripts/run_supervisor_demo.py
```

It prints:
- dataset row counts
- split counts
- Model A metrics
- Model B metrics
- Model C metrics
- final safe claim summary

It also writes a compact JSON summary to `04_demo_outputs/`.

## What each model means
- Model A: regression for traffic recovery delay using pre-recovery network features.
- Model B1: regression for final aggregated delivery ratio.
- Model B2: regression for final energy consumed.
- Model B3: regression for final recovered clusters.
- Model C: pairwise decision support for active-healing versus H0.

## What to say to your supervisor
- The dataset uses the official verified split, not a random split.
- Stage B1 contained unsafe post-simulation features, so leakage was audited before final reporting.
- Recovery delay, delivery ratio, and recovered clusters behave deterministically in the tested domain.
- Energy prediction is not reliable and should not be overstated.
- Model C is pairwise decision support only; it is not a full five-way healing selector.

## Known limitations
- The results are limited to the official Phase 04 / Phase 05 verified domain.
- S11 is reserved for final test only.
- Energy consumption remains poorly predicted.
- Perfect scores do not prove generalization to other wireless sensor network deployments.
- The pairwise classifier should not be described as a full H0/H1/H2/H3/H4 optimizer.
