# Report Materials Guide

**WSN Self-Healing with BSBSSP Research — Final Report Evidence Package**

---

## Overview

This folder contains evidence files needed to prepare the final research report and viva presentation. All files are:

- ✅ **Safe to publish** — No credentials, logs, or sensitive data
- ✅ **Text-based** — Markdown (.md) and CSV (.csv) only
- ✅ **Well-organized** — Grouped by project phase and evidence type
- ✅ **Report-ready** — No further processing needed

---

## Folder Structure

```
report_materials/
├── 00_project_status/          ← Project completion summary
├── 01_methodology/             ← Simulation approach and design
├── 02_simulation_evidence/     ← Scale S8-S11 results and validation
├── 03_database_evidence/       ← PostgreSQL setup and export contracts
├── 04_matlab_evidence/         ← (Placeholder for MATLAB analysis)
├── 05_ml_evidence/             ← Dataset audit, splits, and labels
├── 06_viva_demo_plan/          ← (To be populated: viva outline)
├── 07_figures_selected/        ← (To be populated: key charts/plots)
├── 08_tables_selected/         ← (To be populated: summary tables)
├── REPORT_MATERIALS_MANIFEST.md ← Detailed file inventory
└── README_REPORT_MATERIALS.md  ← This file
```

---

## Quick Start: Writing the Report

### 1. Executive Summary

**Read First:**
- `00_project_status/MILESTONE_SUMMARY.md` — Overall progress
- `00_project_status/FINAL_SCALE5000_S8_STAGEC_RESULTS.md` — Final validation

**Key Metrics to Include:**
- Project completion percentage
- Final scale (5000 nodes)
- Go/No-Go status for each stage

### 2. Introduction & Motivation

**Reference:**
- `01_methodology/README_AGENT1.md` — Research methodology

**Include:**
- Healing method definitions (H0 control, H1-H4 approaches)
- Network architecture (topology A vs B)
- Failure types and scales

### 3. Simulation Results Chapter

**Primary Evidence:**
```
02_simulation_evidence/FINAL_SCALE5000_S{8-11}_STAGE{A-C}_RESULTS.md
```

**What Each File Contains:**
- Delivery ratio comparison across healing methods
- Energy consumption analysis
- Recovery delay measurements
- Recovered cluster counts
- Node failure impact assessment

**Cross-Reference:**
- `FINAL_SCALE5000_S{8-11}_{STAGE}_GO_NO_GO.md` — Stage acceptance
- `FINAL_SCALE5000_S{8-11}_{STAGE}_MATRIX.md` — Summary comparisons
- `FINAL_SCALE5000_S{8-11}_{STAGE}_QUERY_PROOF.md` — Database validation

### 4. Database & Infrastructure

**Read:**
- `03_database_evidence/DATABASE_EXPORT_CONTRACT.md` — Schema definition
- `03_database_evidence/M5_DB_HARDENING_PLAN.md` — Infrastructure design
- `03_database_evidence/README_M5.md` — Setup documentation

### 5. Machine Learning & Analysis

**Dataset Overview:**
- `05_ml_evidence/ML_PHASE01_FREEZE_STATUS.md` — Dataset finalization
- `05_ml_evidence/ML_DATASET_AUDIT_REPORT.md` — Quality assurance

**Splits & Labels:**
- `05_ml_evidence/ML_DATASET_SPLIT_DECISION.md` — Train/val/test split
- `05_ml_evidence/ML_BEST_HEALING_LABEL_DB_SOURCE_REPORT.md` — Label derivation

**Data Files for Analysis:**
- `05_ml_evidence/ml_best_healing_labels_derived_from_db_v1.csv` (636 rows)
- `05_ml_evidence/ml_healing_candidates_scored_from_db_v1.csv` (1,150 rows)
- `05_ml_evidence/ml_scenario_base_conditions_v1.csv` (636 rows)

---

## File Guide by Purpose

### For Results Sections

Use **02_simulation_evidence/**:
- `FINAL_SCALE5000_S8_STAGE*_RESULTS.md` for metric tables
- `FINAL_SCALE5000_S9_STAGE*_RESULTS.md` for architecture comparison
- `FINAL_SCALE5000_S10_STAGE*_RESULTS.md` for larger-scale validation
- `FINAL_SCALE5000_S11_STAGE*_RESULTS.md` for maximum-scale evidence

### For Methodology

Use **01_methodology/** and **03_database_evidence/**:
- `README_AGENT1.md` for simulation platform overview
- `DATABASE_EXPORT_CONTRACT.md` for data collection methodology
- `M5_DB_HARDENING_PLAN.md` for database design

### For Validation & Verification

Use **02_simulation_evidence/** `*_QUERY_PROOF.md` files:
- Each scale/stage has a QUERY_PROOF file
- Demonstrates row counts and data integrity
- Can include as appendix for reproducibility

### For Machine Learning

Use **05_ml_evidence/**:
- CSV files for data tables in report
- Markdown files for methodology sections
- Score_v1 formula from DB_SOURCE_REPORT

---

## Data Summary

### Simulation Coverage

| Scale | Nodes | Stages | Status | Evidence |
|-------|-------|--------|--------|----------|
| S8 | 1,000 | A, B, C | ✅ Complete | 12 files (plans, results, GO/NO-GO) |
| S9 | 2,000 | A, B, C | ✅ Complete | 12 files |
| S10 | 4,000 | A, B, C | ✅ Complete | 12 files |
| S11 | 5,000 | A, B, C | ✅ Complete | 12 files |

### Healing Methods Tested

| Method | Type | Description |
|--------|------|-------------|
| H0 | Control | No healing applied (baseline) |
| H1 | Conservative | Minimal healing intervention |
| H2 | Moderate | Balanced recovery approach |
| H3 | Aggressive | Strong but energy-intensive |
| H4 | Maximum | Most aggressive healing strategy |

### Network Architectures

| Arch | Description | Note |
|------|-------------|------|
| A | Flat/Direct | Single-hop communication |
| B | Hierarchical | Multi-hop via cluster heads |

### Failure Types

| Type | Description |
|------|-------------|
| F0 | Single cluster head failure (controlled) |
| F1 | Multiple CH failures (progressive) |
| F2 | Network-wide degradation (cascading) |

### Traffic Loads

| Load | Intensity |
|------|-----------|
| L1 | Light (low traffic) |
| L2 | Heavy (high traffic) |

### Scales

- S1-S7: Pilot and validation scales (50-500 nodes)
- **S8-S11: Final production scales (1K-5K nodes)** ← Focus for report

---

## CSV Data Reference

### ml_best_healing_labels_derived_from_db_v1.csv

**Use For:** Best healing method selection per scenario

```
base_condition_key,best_healing_id,best_run_id,best_score
S=S1_A=A_F=F0_L=L1_seed=1,H0,101,-0.50
S=S1_A=A_F=F0_L=L1_seed=2,H4,102,0.25
...
```

**Statistics:** 636 rows (one per unique scenario)

### ml_healing_candidates_scored_from_db_v1.csv

**Use For:** Individual run performance metrics

```
run_id,healing_id,base_condition_key,score_v1,consumed_j,low_nodes,...
101,H0,S=S1_A=A_F=F0_L=L1_seed=1,-0.50,0.64,0,1.0,0.0
102,H4,S=S1_A=A_F=F0_L=L1_seed=1,0.25,0.89,1,0.95,1.0
...
```

**Statistics:** 1,150 rows (all tested runs with metrics)

### ml_scenario_base_conditions_v1.csv

**Use For:** Scenario definitions and healing availability

```
base_condition_key,scale,architecture,failure_family,load,seed,candidate_healing_count,healing_methods
S=S1_A=A_F=F0_L=L1_seed=1,S1,A,F0,L1,1,2,H0,H4
...
```

**Statistics:** 636 rows (unique scenario keys)

---

## Viva Presentation Prep

### Structure for 06_viva_demo_plan/

1. **Outline slides** — Project motivation, methods, results
2. **Key findings** — Most important discoveries
3. **Live demonstrations** — Using CSV data for queries
4. **Q&A preparation** — Common questions and answers

### Figures for 07_figures_selected/

Recommended to create after analysis:
- Healing method comparison charts (H0 vs H1-H4)
- Scale comparison (S8-S11 trends)
- Architecture comparison (A vs B)
- Feature importance (from ML analysis)
- Network topology diagrams
- Failure scenario examples

### Tables for 08_tables_selected/

Create from CSV data:
- Summary statistics per scale and stage
- Healing method ranking table
- Architecture performance comparison
- Energy vs recovery time trade-off table

---

## Important Notes

### What's Included

✅ Text documentation (markdown files)  
✅ Structured data (CSV files)  
✅ Validation reports (GO/NO-GO, QUERY_PROOF)  
✅ Stage-specific results and plans  
✅ ML analysis and datasets  

### What's NOT Included

❌ Raw simulation output (stored locally in WSN_simulation/)  
❌ Database dumps (.sql files)  
❌ Full MATLAB datasets (available locally)  
❌ Large binary figures (to be generated)  
❌ Credentials or configuration files  
❌ Build artifacts or temporary files  

**Note:** Local copies of excluded items remain in:
- `/home/cyfer/FYP/WSN_simulation/` — ML datasets, MATLAB analysis
- `/home/cyfer/FYP/archive/` — Database backups and archives
- `agent1_simulation_platform/` — Full simulation outputs

---

## Using These Files for Report Writing

### Step 1: Read Evidence Files

Start with these in order:
1. MILESTONE_SUMMARY.md
2. README_AGENT1.md
3. DATABASE_EXPORT_CONTRACT.md
4. ML_DATASET_AUDIT_REPORT.md

### Step 2: Organize by Chapter

Map files to report sections:
- **Chapter 1 (Introduction):** Methodology files
- **Chapter 2 (Methods):** Database and simulation docs
- **Chapter 3 (Results):** All FINAL_SCALE5000_S*_STAGE*_RESULTS.md
- **Chapter 4 (Validation):** GO_NO_GO and QUERY_PROOF files
- **Chapter 5 (Analysis):** ML_* files and CSV data

### Step 3: Create Tables & Figures

Extract data from:
- CSV files for quantitative tables
- Markdown sections for methodology descriptions
- Evidence files for quotes and citations

### Step 4: Cross-Reference

Use REPORT_MATERIALS_MANIFEST.md to:
- Track which files you've referenced
- Verify all key evidence is included
- Maintain appendix citations

---

## Contact & Questions

For questions about:
- **Simulation methodology:** See README_AGENT1.md
- **Database design:** See DATABASE_EXPORT_CONTRACT.md
- **ML methodology:** See ML_BEST_HEALING_LABEL_DB_SOURCE_REPORT.md
- **Specific results:** See relevant FINAL_SCALE5000_S*_STAGE*.md file
- **Data integrity:** See corresponding *_QUERY_PROOF.md file

---

## Version & Date

**Report Materials Package Created:** 2026-05-12  
**Status:** ✅ Ready for Report Generation  
**Next Update:** Post-VIVA (if needed for final publication)

---

**For Report Writing:** Start with [00_project_status/](00_project_status/) folder and work through in order.  
**For Viva Prep:** Add your demonstration plan to [06_viva_demo_plan/](06_viva_demo_plan/).  
**For Publication:** All files in this folder are approved for public GitHub.
