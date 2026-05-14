# FINAL_SCALE5000 S9 Stage A — Go/No-Go

Date: 2026-05-02

**Gate checks performed in MATLAB:**

| Check | Result | Details |
|-------|--------|---------|
| S9 Stage A visibility (12/12) | PASS | All 12 expected runs present with run_status='complete' |
| Node/cluster/sim-time parameters | PASS | 4000 nodes, 160 clusters, 250 s per run (all confirmed) |
| Architecture balance (A/B) | PASS | A=6, B=6 |
| Load balance (L1/L2) | PASS | L1=6, L2=6 |
| Failure/healing groups | PASS | F0/H0=4, F1/H1=4, F4/H4=4 |
| Representative baseline readability | PASS | Run 1027 loads: 4160 cluster_ts, 4005 node_summary, 26 global_ts |
| Representative A/B pair readability | PASS | Runs 1032 (A), 1034 (B) load successfully with matching row counts |
| Representative stress/healing readability | PASS | Run 1039 (F4_H4_B_S9_L2_seed01) loads: 13320 events, 4160 cluster_ts, 4005 node_summary |
| Event marker usability | PASS | Failure injection @10s, recovery start @22s, recovery applied @22s, first agg @30s |
| Plotting usability | PASS | All 7 PNG/PDF/FIG outputs generated; no legend truncation or vector PDF warnings |
| Map lineage presence | PASS | Single map (map_S9_seed01) per all 12 runs |

**Final Verdict:**

- **S9 Stage A MATLAB passed:** YES
- **S9 overall completion (MATLAB QA perspective):** YES
- **Safe to proceed to S9 Stage B:** YES
- **Status:** COMPLETE

**Conditions/Notes:**

- Selection rule enforced: deterministic latest-per-key across all 12 runs
- No run duplicates or re-import artifacts observed
- Baseline (F0_H0) shows minimal event activity (1281 events) as expected for no-failure scenario
- F1 pair shows high event activity (~624k each), indicating complex recovery patterns
- F4 stress/healing run (1039) shows moderate event activity (13.3k), matching S9 workload intensity
- Representative figures available in `matlab_local/output/run_1039/` for review

**Gate Status:** ✅ APPROVED for S9 Stage B

