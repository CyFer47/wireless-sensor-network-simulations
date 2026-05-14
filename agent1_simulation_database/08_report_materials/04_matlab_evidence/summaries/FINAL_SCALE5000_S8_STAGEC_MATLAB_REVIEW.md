# FINAL_SCALE5000 S8 Stage C — MATLAB Review

Date: 2026-05-01

Summary (live MATLAB run):

- Stage C rows visible in MATLAB: **64**
- Distinct Stage C scenario keys: **64**
- `map_id`/`map_signature` missing: **0**
- New Stage C run_id range observed: includes 995–1026 (Agent 1 reported)

Representative matched-control checks executed for families F1..F4. Full JSON/TXT results saved to `docs/S8_STAGEC_MATLAB_VERIFY_RESULT.json` and `.txt`.

Notes:

- MATLAB verifier selected latest-complete-per-key by SQL `ROW_NUMBER() OVER (...)` to avoid re-import ambiguity.
- Representative pairs selected and loaded; counts and markers confirmed.
