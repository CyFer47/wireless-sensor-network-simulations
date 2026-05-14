# Report Materials Manifest

**Date Created:** 2026-05-12  
**Purpose:** Structured collection of evidence files for final report and viva presentation  
**Total Files:** 55  
**Total Size:** ~2.3 MB (text, markdown, CSV only)  

---

## Manifest Index

### 00_project_status (3 files)

| File | Purpose | Source | Safe | Notes |
|------|---------|--------|------|-------|
| MILESTONE_SUMMARY.md | Overall project completion status | agent1_simulation_platform | Yes | High-level summary of all milestones |
| FINAL_SCALE5000_S8_STAGEC_GO_NO_GO.md | Scale 8 final validation sign-off | agent1_simulation_platform | Yes | Stage C completion evidence for 5000-node scale |
| FINAL_SCALE5000_S8_STAGEC_RESULTS.md | Scale 8 final results and metrics | agent1_simulation_platform | Yes | Quantitative results for largest test scale |

### 01_methodology (1 file)

| File | Purpose | Source | Safe | Notes |
|------|---------|--------|------|-------|
| README_AGENT1.md | Agent 1 simulation platform overview | agent1_simulation_platform | Yes | Simulation methodology and architecture |

### 02_simulation_evidence (42 files)

#### Scale S7-S11 Results by Stage

| File Pattern | Purpose | Safe | Notes |
|------|---------|------|-------|
| FINAL_SCALE5000_S{8-11}_STAGE{A-C}_RESULTS.md | Detailed results for each stage | Yes | 12 files covering all final scales and stages |
| FINAL_SCALE5000_S{8-11}_STAGE{A-C}_MATRIX.md | Comparison matrices for each stage | Yes | 8 files with metric summaries |
| FINAL_SCALE5000_S{8-11}_STAGE{A-C}_PLAN.md | Execution plans for each stage | Yes | 8 files with test parameters |
| FINAL_SCALE5000_S{8-11}_STAGE{A-C}_QUERY_PROOF.md | Database validation for each stage | Yes | 7 files with row count verification |
| FINAL_SCALE5000_S{8-11}_{STAGE}_GO_NO_GO.md | Final sign-off for each scale/stage | Yes | 7 files with acceptance criteria |

#### Infrastructure & Earlier Phases

| File | Purpose | Safe | Notes |
|------|---------|------|-------|
| FINAL_SCALE5000_PHASE1_DB_DASHBOARD_CHECK.md | Phase 1 database + dashboard validation | Yes | Infrastructure readiness evidence |
| M5_MILESTONE_SUMMARY.md | Milestone 5 completion summary | Yes | Early validation results |
| M6_PILOT_RESULTS.md | Pilot run results | Yes | Proof of concept execution |
| M7_PROGRESS_REPORT.md | Milestone 7 progress update | Yes | Development progress tracking |
| M7_QUERY_PROOF.md | Milestone 7 database verification | Yes | Database integrity validation |
| S7_STAGEA_RESULTS.md | Scale 7 Stage A results | Yes | Earlier scale validation |
| S7_STAGEA_QUERY_PROOF.md | Scale 7 Stage A database check | Yes | Earlier scale database validation |

### 03_database_evidence (3 files)

| File | Purpose | Source | Safe | Notes |
|------|---------|--------|------|-------|
| DATABASE_EXPORT_CONTRACT.md | Export specification and validation | agent1_simulation_platform | Yes | Database schema and export format definition |
| M5_DB_HARDENING_PLAN.md | Database security and reliability plan | agent1_simulation_platform | Yes | Database infrastructure design |
| README_M5.md | Database configuration guide | agent1_simulation_platform | Yes | Setup and deployment documentation |

### 04_matlab_evidence (0 files)

**Status:** No MATLAB-specific evidence files exported to GitHub at this time  
**Note:** MATLAB analysis available in local WSN_simulation/matlab/ directory

### 05_ml_evidence (8 files)

| File | Purpose | Source | Safe | Notes |
|------|---------|--------|------|-------|
| ML_PHASE01_FREEZE_STATUS.md | Phase 01 dataset freeze checkpoint | WSN_simulation | Yes | Dataset version and completeness verification |
| ML_DATASET_AUDIT_REPORT.md | Comprehensive dataset audit with statistics | WSN_simulation | Yes | Row counts, marker distribution, quality checks |
| ML_DATASET_SPLIT_DECISION.md | Train/validation/test split rationale | WSN_simulation | Yes | Deterministic partition rules (S1-S11) |
| ML_SEED_EXPANSION_DECISION.md | Seed sampling strategy documentation | WSN_simulation | Yes | Explanation of seed coverage decisions |
| ML_DATASET_EXPORT_LOCAL_VERIFICATION.md | Local verification of all exports | WSN_simulation | Yes | Split distributions, duplicate checks, secret scan results |
| ML_BEST_HEALING_LABEL_DB_SOURCE_REPORT.md | Best-healing label derivation report | WSN_simulation | Yes | Score_v1 formula, derivation methodology, constraints |
| ml_best_healing_labels_derived_from_db_v1.csv | Derived best-healing labels | WSN_simulation | Yes | 636 base conditions with best healing assignments |
| ml_healing_candidates_scored_from_db_v1.csv | Scored healing candidates | WSN_simulation | Yes | 1,150 runs with score_v1 and metrics |
| ml_scenario_base_conditions_v1.csv | Base condition definitions | WSN_simulation | Yes | 636 scenarios with candidate healing counts |

### 06_viva_demo_plan (0 files)

**Status:** Not yet created  
**Note:** To be populated with viva presentation outline and demonstration guide

### 07_figures_selected (0 files)

**Status:** No figures available at this time  
**Note:** Report generation typically produces comparison charts; can be added post-analysis

### 08_tables_selected (0 files)

**Status:** CSV files available in ML evidence folder  
**Note:** Tables incorporated into ML evidence for easy access

---

## File Categories

### Safe to Publish (All 55 Files)

✅ **Markdown documentation** — All analysis, planning, and results documents  
✅ **CSV datasets** — Anonymized, non-sensitive data exports  
✅ **No logs** — No application logs or debug traces  
✅ **No secrets** — No credentials, API keys, or internal addresses  
✅ **No binaries** — No compiled objects or binary artifacts  

### Excluded (Intentionally Not Pushed)

❌ **Database dumps** — PostgreSQL backup files (.sql)  
❌ **Full output folders** — Raw simulation output (TeraBytes)  
❌ **Binary figures** — Large .fig or image files > 5MB  
❌ **Environment files** — .env files with credentials  
❌ **Log files** — Application logs, error traces  
❌ **Archives** — tar.gz, zip, or other compressed backups  
❌ **Credentials** — SSH keys, database passwords  
❌ **VCS directories** — .venv, node_modules, __pycache__  

---

## Usage for Final Report

### Phase 1: Report Structure

1. **Project Status** → Use files in `00_project_status/` for executive summary
2. **Methodology** → Reference `01_methodology/` for simulation design
3. **Simulation Results** → Use `02_simulation_evidence/` for results sections
4. **Database Design** → Reference `03_database_evidence/` for infrastructure chapter
5. **ML Analysis** → Use `05_ml_evidence/` for machine learning results

### Phase 2: Viva Preparation

1. Create presentation outline in `06_viva_demo_plan/`
2. Add key figures/screenshots to `07_figures_selected/`
3. Add summary tables to `08_tables_selected/`
4. Reference CSV data for live demonstrations

### Phase 3: Evidence Verification

1. Cross-reference GO/NO-GO documents for sign-offs
2. Verify database queries in QUERY_PROOF files
3. Confirm metrics from RESULTS files
4. Check stage plans against actual execution

---

## Data Dictionary

### Key Columns in ML CSVs

**ml_best_healing_labels_derived_from_db_v1.csv**
- `base_condition_key` — Scenario identifier (scale, arch, failure, load, seed)
- `best_healing_id` — Selected healing method (H0/H1/H2/H3/H4)
- `best_run_id` — PostgreSQL run_id of best performer
- `best_score` — Normalized score [-2.5, 0.5]

**ml_healing_candidates_scored_from_db_v1.csv**
- `run_id` — PostgreSQL run identifier
- `healing_id` — Healing method applied (H0-H4)
- `base_condition_key` — Scenario identifier
- `score_v1` — Performance score (formula in report)
- Additional metrics: consumed_j, low_nodes, recovered_clusters, agg_delivery_ratio, recovery_delay_s

**ml_scenario_base_conditions_v1.csv**
- `base_condition_key` — Scenario identifier
- `scale` — Network scale (S1-S11)
- `architecture` — Network topology (A or B)
- `failure_family` — Failure type (F0, F1, F2)
- `load` — Traffic load level (L1, L2)
- `seed` — Pseudo-random seed
- `candidate_healing_count` — Number of healing methods tested
- `healing_methods` — Comma-separated list (e.g., "H0,H4")

---

## Verification Checklist

- ✅ All 55 files are text-based (markdown, CSV)
- ✅ No database dumps included
- ✅ No credentials or secrets in any file
- ✅ No binary artifacts or archives
- ✅ No full simulation output folders
- ✅ Files organized by logical category
- ✅ Manifest created for tracking
- ✅ Safe for public GitHub repository

---

## Next Steps

1. **Review README_REPORT_MATERIALS.md** for usage instructions
2. **Cross-reference manifest** when writing each report section
3. **Use CSV data** for tables and quantitative analysis
4. **Reference markdown files** for detailed explanations
5. **Prepare viva materials** by adding to sections 06, 07, 08
6. **Keep backup** of local WSN_simulation folder for any additional analysis

---

**Report Materials Created:** 2026-05-12 by Agent 1  
**Status:** ✅ Ready for Report Generation
