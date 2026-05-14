Failure cause:
- The Stage C runspec generator used inconsistent row key names and did not reliably set `timing.recovery_delay_s` to `null` for `H0`/`V2` control specs. A generated spec contained `recovery_delay_s: 12.0`, which violates validator rule `V2 requires timing.recovery_delay_s=null`.

Fix applied:
- `tools/run_s9_stagec_batch.py`: robustly read `healing` via `row.get('healing_id') or row.get('healing')`, read `variant`, and explicitly set `recovery_delay_s = null` for `H0` controls (variant `V2`).

Focused retry result:
- Regenerated `runspecs/generated/s9_stagec/F1_H0_A_S9_L1_seed01.json` using the fixed generator.
- Validator: PASS
- Simulation: completed and exported
- Import: successful (run_id 1064)
- DB verification: run_id 1064 present and `run_status='complete'` in `wsn.runs`.

Resume safety:
- The generator fix ensures H0 control specs will have `recovery_delay_s=null` and `recovery.enabled=false`.
- Focused retry succeeded; remaining H0 control specs can be regenerated and validated before batch resume.

Notes:
- I updated state/quarantine files locally to reflect the focused retry import, but per instructions I did not commit any outputs or logs.
