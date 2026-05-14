# FINAL_SCALE5000 S8 Stage B MATLAB Review

Date: 2026-05-01  
Scope: S8 Stage B only (representative-run QA only; no all-run plotting)

## 1) Live MATLAB visibility checks

Executed from live MATLAB (`matlab -batch`) using project DB config and helper stack.

Connection:

- Database Toolbox primary: fallback occurred during verifier startup in one phase, JDBC connected successfully.
- JDBC target: `192.168.1.4:5432/wsn_sim`, schema `wsn`.

Stage B target filter used:

- `scale='S8'`
- `run_status='complete'`
- `architecture IN ('A','B')`
- `load IN ('L1','L2')`
- `seed IN (1,2)` corresponding to `seed01/seed02`
- matched healing families only:
  - `(F1,H1) OR (F2,H2) OR (F3,H3) OR (F4,H4)`

Observed in MATLAB:

- Stage B rows visible: **32**
- Distinct Stage B scenario keys visible: **32**
- `map_id` / `map_signature` missing rows: **0**
- Newest Stage B run_id: **994**

Verdict: **Visibility PASS**.

## 2) Run-id continuity and re-import caveat assessment

Window inspected: `run_id 951..994`.

MATLAB query findings:

- Re-import focus rows present:
  - `969`: `A F1/H1 L1 seed01`
  - `970`: `A F1/H1 L2 seed01`
  - `971`: `B F1/H1 L1 seed01`
- Scenario labels for these rows: `m3-scenario-library`.
- Older complete rows with the same Stage B scenario key were searched via SQL self-join:
  - older count for 969: `0`
  - older count for 970: `0`
  - older count for 971: `0`
- Duplicate-key scan over complete S8 Stage B family space returned no duplicates (`duplicate_keys=[]`).

MATLAB risk conclusion:

- Representative selection will **not** accidentally pick stale duplicates in the current DB state.
- Even if re-imports happen later, deterministic selection should still use latest complete row by scenario key.

## 3) Representative run reads (one per family)

Selection basis: latest complete run_id per scenario key, then one representative chosen per family.

Selected representatives:

- `F1/H1`: run_id **974** (`B`, `L2`, `seed02`)
- `F2/H2`: run_id **982** (`B`, `L2`, `seed02`)
- `F3/H3`: run_id **990** (`B`, `L2`, `seed02`)
- `F4/H4`: run_id **994** (`B`, `L2`, `seed02`)

Actual row counts loaded in MATLAB:

- Run **974**: `run_summary=1`, `cluster_timeseries=32340`, `events=39540`, `node_final_summary=3505`, `global_timeseries=231`, markers `all_present`
- Run **982**: `run_summary=1`, `cluster_timeseries=32340`, `events=7844`, `node_final_summary=3505`, `global_timeseries=231`, markers `all_present`
- Run **990**: `run_summary=1`, `cluster_timeseries=32340`, `events=8078`, `node_final_summary=3505`, `global_timeseries=231`, markers `all_present`
- Run **994**: `run_summary=1`, `cluster_timeseries=32340`, `events=10606`, `node_final_summary=3505`, `global_timeseries=231`, markers `all_present`

## 4) Event marker verification (stress/healing representative)

Stress/healing run checked: **run_id 994** (`F4/H4`, `B`, `L2`, `seed02`).

Extracted markers:

- failure injection: `46`
- recovery start: `50`
- recovery applied: `50`
- first aggregate: `4`
- first recovered aggregate: `52`
- first recovered raw: `NA`

NA interpretation:

- `first_recovered_raw` is parser/logically optional for this run family and was absent in emitted event sequence for the current extraction logic; this does not block Stage B because failure/recovery/aggregate markers required for healing QA were present.

## 5) Plot check (single representative set only)

Executed one representative figure set through `analyze_single_run(994,false)`.

Observed:

- legend truncation warning: **no**
- vector PDF warning: **no**
- PNG generated: **yes** (`7` files)
- PDF generated: **yes** (`7` files)
- FIG generated: **yes** (`7` files)
- event diagnostic generated: **yes** (`run_994_event_diagnostic.txt`)

## 6) Stage B MATLAB decision

- S8 Stage B MATLAB visibility: **PASS**
- Duplicate/re-import caveat: **ACCEPTED** (no duplicate-key conflict in current Stage B complete set)
- Deterministic selection rule required: **YES**
- S8 Stage B MATLAB passed: **YES**
- Safe to proceed to S8 Stage C: **YES** (from MATLAB QA perspective)
