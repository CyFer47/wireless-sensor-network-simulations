# FINAL_SCALE5000 S9 Stage B — Go/No-Go

Date: 2026-05-02

**Gate checks performed in MATLAB:**

| Check | Result | Details |
|-------|--------|---------|
| S9 Stage B visibility (32/32) | PASS | All 32 healing-family runs present with run_status='complete' |
| Node/cluster/sim-time parameters | PASS | 4000 nodes, 160 clusters, 250 s per run (all confirmed) |
| Healing family balance | PASS | F1/H1=8, F2/H2=8, F3/H3=8, F4/H4=8 |
| Architecture balance (A/B) | PASS | A=16, B=16 |
| Load balance (L1/L2) | PASS | L1=16, L2=16 |
| Seed balance (seed01/seed02) | PASS | seed01=16, seed02=16 |
| Duplicate/re-import risk | PASS | No scenario keys with multiple runs detected |
| Representative F1/H1 readability | PASS | Run 1032 loads: 624209 events, 4160 cluster_ts, 4005 node_summary |
| Representative F2/H2 readability | PASS | Run 1044 loads: 1284 events, 4160 cluster_ts, 4005 node_summary |
| Representative F3/H3 readability | PASS | Run 1052 loads: 2367 events, 4160 cluster_ts, 4005 node_summary |
| Representative F4/H4 readability | PASS | Run 1036 loads: 13318 events, 4160 cluster_ts, 4005 node_summary |
| Event marker usability | PASS | F4/H4: failure injection @10s, recovery start/applied @22s, first agg @30s |
| Plotting usability | PASS | All 7 PNG/PDF/FIG outputs for run 1036 generated; no warnings |
| Map lineage presence | PASS | Dual maps (map_S9_seed01, map_S9_seed02) present for stage B |

**Final Verdict:**

- **S9 Stage B MATLAB passed:** YES
- **Duplicate/re-import risk:** ACCEPTED (no duplicates present; deterministic selection rule applied successfully)
- **Safe to proceed to S9 Stage C:** YES
- **Status:** COMPLETE

**Conditions/Notes:**

- Selection rule enforced: deterministic latest-per-key across all 32 Stage B runs
- No run duplicates or re-import artifacts observed
- All healing families (F1-F4) present and balanced across architecture/load/seed combinations
- Event marker consistency observed: healing runs show similar recovery timelines (22s recovery start, 30s first aggregate recovery)
- Representative figures available in `matlab_local/output/run_1036/` for review
- S9 Stage B data quality confirmed as suitable for Stage C (matched control-vs-healing analysis)

**Gate Status:** ✅ APPROVED for S9 Stage C

