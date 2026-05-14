# MATLAB Connection and Validation Commands

## Connection details
- JDBC host currently used: `192.168.1.7`
- Port: `5432`
- Database: `wsn_sim`
- Schema: `wsn`

## Connection test scripts found
- `/home/cyfer/FYP/garbage/github_packaging/wsn-self-healing-bsbssp-research/agent2_matlab_analytics/scripts/test_db_connection.m`
- `/home/cyfer/FYP/garbage/WSN Dashboard Milestone V2/matlab_local/scripts/test_db_connection.m`

## Example MATLAB commands
```matlab
test_db_connection()
```

If a live Phase2A validation function is available in the MATLAB scripts folder, run it the same way:
```matlab
phase2a_patch_validation()
```

## How to verify the connection
1. Confirm MATLAB can reach PostgreSQL on the host IP.
2. Run the JDBC or database test script.
3. Check that the script reports a successful connection and query result.
4. Open the final MATLAB summary documents and figures for the viva.

## Where to find generated figures
- `04_MATLAB_VALIDATION/selected_figures/`
- `04_MATLAB_VALIDATION/summaries/`

## Demo note
Use MATLAB for validation evidence and figure review, not for training or long-running analysis during the live demo.
