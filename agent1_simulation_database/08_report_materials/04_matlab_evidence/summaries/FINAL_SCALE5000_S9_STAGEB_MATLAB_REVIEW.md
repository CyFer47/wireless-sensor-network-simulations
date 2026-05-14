# FINAL_SCALE5000 S9 Stage B — MATLAB Review

Date: 2026-05-02

**Summary (live MATLAB run):**

- S9 Stage B rows visible in MATLAB: **32**
- All rows have `run_status='complete'`
- Node count per run: **4000** (expected)
- Cluster count per run: **160** (expected)
- Simulation time per run: **250 s** (expected)
- Healing families present: **F1/H1, F2/H2, F3/H3, F4/H4** (8 rows each)
- Architecture balance: **A=16, B=16**
- Load balance: **L1=16, L2=16**
- Seed balance: **seed01=16, seed02=16**

**Verification method:**

- JDBC connection to PostgreSQL wsn_sim schema
- Deterministic selection: latest complete `run_id` per scenario key (scale + architecture + failure_family + healing_id + load + seed)
- Duplicate/re-import check: no scenario keys with multiple runs detected
- Live MATLAB execution with event marker extraction and representative plotting

**Outcomes:**

- S9 Stage B matrix complete: **32/32 expected runs present**
- Duplicate/re-import risk: **NONE DETECTED**
- Representative run selection complete for each healing family (see selection doc)
- Event markers extracted from F4/H4 representative run (run_id 1036)
- Plotting completed without legend truncation or vector PDF warnings
- Full JSON/TXT results saved to `docs/S9_STAGEB_MATLAB_VERIFY_RESULT.*`

**Notes:**

- Map lineage: per-seed maps (map_S9_seed01 for seed01 runs, map_S9_seed02 for seed02 runs)
- Representative run selection: latest complete per family, balancing architecture/load/seed
- Event markers show consistent pattern across healing runs: failure injection @10s, recovery start/applied @22s, first recovered aggregate @30s
- All 7 representative PNG/PDF/FIG outputs generated without warnings
- Total rows after Stage B as reported by Agent 1: 36 S9 complete runs (8 from Stage A + 24 new Stage B + 4 Stage B reusing Stage A runs that now have a second seed)

