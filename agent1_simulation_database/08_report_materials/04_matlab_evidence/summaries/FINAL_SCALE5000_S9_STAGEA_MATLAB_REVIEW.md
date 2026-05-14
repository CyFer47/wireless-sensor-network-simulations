# FINAL_SCALE5000 S9 Stage A — MATLAB Review

Date: 2026-05-02

**Summary (live MATLAB run):**

- S9 Stage A rows visible in MATLAB: **12**
- All rows have `run_status='complete'`
- Node count per run: **4000** (expected)
- Cluster count per run: **160** (expected)
- Simulation time per run: **250 s** (expected)
- All runs use `seed=01` (S9 Stage A smoke test)
- Architecture balance: **A=6, B=6**
- Load balance: **L1=6, L2=6**
- Failure/healing groups:
  - F0/H0 = 4 runs
  - F1/H1 = 4 runs
  - F4/H4 = 4 runs

**Verification method:**

- JDBC connection to PostgreSQL wsn_sim schema
- Deterministic selection: latest complete `run_id` per scenario key (scale + architecture + failure_family + healing_id + load + seed)
- Live MATLAB execution with event marker extraction and representative plotting

**Outcomes:**

- S9 Stage A matrix complete: **12/12 expected runs present**
- Representative run selection complete (see selection doc)
- Event markers extracted from stress/healing representative run (run_id 1039)
- Plotting completed without legend truncation or vector PDF warnings
- Full JSON/TXT results saved to `docs/S9_STAGEA_MATLAB_VERIFY_RESULT.*`

**Notes:**

- Map lineage: single map per seed (map_S9_seed01 for all 12 runs)
- Representative baseline, A/B pair, and stress/healing runs selected and loaded
- Event markers show: failure injection at 10s, recovery applied at 22s, first recovered aggregate at 30s
- All 7 representative PNG/PDF/FIG outputs generated without warnings

