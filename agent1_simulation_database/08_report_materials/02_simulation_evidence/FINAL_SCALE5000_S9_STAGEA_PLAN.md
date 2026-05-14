# FINAL_SCALE5000_S9_STAGEA_PLAN

Purpose: Run S9 Stage A (4000-node smoke test) — DB-aware, reuse existing runs, generate missing runs only.

Scope:
- Execute only S9 Stage A (12 runs) using seed01.
- Follow MATLAB selection rule: for each scenario key use latest complete run_id.
- Stop on first unrecoverable failure and quarantine failing run.

Key automation:
- `tools/run_s9_stagea_batch.py` performs DB pre-scan, spec generation, map validation, simulation, import, and verification.

Monitoring and artifacts:
- outputs/s9_stagea_state.json
- outputs/s9_stagea_quarantine.json
- outputs/s9_stagea_batch.log
