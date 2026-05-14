# MATLAB Final Demo Workspace

This workspace is the curated MATLAB side of the final viva/demo package. It keeps the small, report-ready pieces and separates bulky or legacy outputs into `archive_quarantine`.

## What This Workspace Contains
- MATLAB startup and PostgreSQL JDBC connection checks
- Phase2A live DB validation scripts and report outputs
- S8-S11 MATLAB validation summaries and review documents
- Selected lightweight figures and tables only
- Command guides for running each demo task
- Report wording and cleanup notes

## How MATLAB Connects to PostgreSQL
- The validated connection target is PostgreSQL at `192.168.1.7:5432`.
- Database: `wsn_sim`
- MATLAB uses the local JDBC driver and Database Toolbox fallback logic.
- The safest project-side connection check is `test_db_connection()`.

## Which Scripts to Run First
1. Run `startup` from the MATLAB workspace root.
2. Run `test_db_connection()` to confirm JDBC connectivity.
3. Run `phase2a_live_db_validation_clean()` for the live Phase2A proof.
4. Review the S8-S11 validation summaries for staged comparison evidence.

## Phase2A Files
- `02_PHASE2A_LIVE_DB_VALIDATION/PHASE2A_MATLAB_LIVE_DB_VALIDATION_REPORT.md`
- `04_SELECTED_FIGURES/phase2a_live_energy_summary.png`
- `04_SELECTED_FIGURES/phase2a_live_h0_vs_healing_summary.png`
- `04_SELECTED_FIGURES/phase2a_live_scale_summary.png`

## S8-S11 Files
- `03_S8_TO_S11_VALIDATION/FINAL_SCALE5000_*`
- `05_SELECTED_TABLES/*S8*`, `05_SELECTED_TABLES/*S9*`, `05_SELECTED_TABLES/*S10*`, `05_SELECTED_TABLES/*S11*`

## Safe Outputs For Report
- Markdown validation reports
- Selected PNG figures
- Short summary tables
- Command guides and README files

## Limitations To Mention
- Phase2A is mainly live DB validation evidence for scale and energy checks.
- Phase2A total live rows can exceed 162 because additional S100 variants are present.
- H0 versus active-healing comparison should be taken from the earlier S8-S11/S11 Stage C evidence set, not Phase2A.
- CSV package validation is skipped because live JDBC DB validation is available.
