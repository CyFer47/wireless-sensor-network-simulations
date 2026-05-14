# MATLAB Validation Report Text

MATLAB was used as an independent validation and analysis layer. It connected to the PostgreSQL experiment database through JDBC and verified selected simulation results, event timing, energy fields, and scale comparison outputs. For Phase2A, live database validation confirmed that the S12/S13 scale-rule patch resolved the previous failed-run issue, leaving zero failed or partial Phase2A rows in the validated query set.

## Validation Purpose
- Confirm the MATLAB analysis layer could reach the live experiment database.
- Validate that the key report-ready tables and figures could be regenerated.
- Provide an independent check on selected simulation results.

## JDBC Live DB Validation
- MATLAB connected to PostgreSQL at `192.168.1.7:5432` using JDBC.
- The live database exposed the expected Phase2A rows and summary tables.
- The validated output was written as a report and a small figure set.

## Phase2A Patch Verification
- The live Phase2A query set showed the S12/S13 patch effect.
- Failed or partial Phase2A rows remaining: zero.
- The validated live DB evidence is safe for the report with the count-reconciliation note.

## S8-S11 Scale Validation
- S8-S11 review documents remain the stronger evidence for staged scale comparison.
- These files are preserved in the demo workspace for narration and report support.

## Event Marker Validation
- MATLAB can query event timing and marker data from the live database.
- Recovery timing is queryable where the scenario includes recovery events.

## Limitations
Phase2A is used mainly as energy/scale/live database validation evidence. H0 versus active-healing comparison should be based on the earlier S8-S11/S11 Stage C result set rather than Phase2A, because Phase2A did not contain sufficient H0/healing coverage for that comparison.
