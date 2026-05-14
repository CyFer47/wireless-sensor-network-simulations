# Final Demo Workspace

## Project Title
WSN Self-Healing BSBSSP Research Final Demonstration Workspace

## What This Workspace Contains
This workspace is a curated, demo-safe subset of the project for a viva or final presentation.
It is organized so that you can show:
- the simulation code and scale folders
- the database import and query workflow
- MATLAB validation evidence
- the ML supervisor demo materials
- the dashboard demo entry points
- selected report evidence and figures
- terminal command guides and troubleshooting notes

## What Not to Run Live
Do not run:
- the full 162-run batch
- heavy dataset exports
- large database backups
- any ML training workflow
- any command that modifies PostgreSQL outside the documented demo import path
- any command that depends on `.env` or `.venv` being copied into GitHub

## Safe Live-Demo Order
Use the order in `FINAL_VIVA_DEMO_RUN_ORDER.md` for a clean presentation flow.

## Where the Main Pieces Are
- Simulation scripts: `02_SIMULATION_DEMO/` and `10_TERMINAL_COMMAND_GUIDES/01_RUN_SIMULATION_COMMANDS.md`
- Database commands: `03_DATABASE_DEMO/` and `10_TERMINAL_COMMAND_GUIDES/02_IMPORT_TO_DATABASE_COMMANDS.md`
- MATLAB validation: `04_MATLAB_VALIDATION/` and `10_TERMINAL_COMMAND_GUIDES/04_MATLAB_CONNECTION_AND_VALIDATION_COMMANDS.md`
- ML demo: `05_ML_DEMO/` and `10_TERMINAL_COMMAND_GUIDES/05_ML_DEMO_COMMANDS.md`
- Dashboard demo: `06_DASHBOARD_DEMO/` and `10_TERMINAL_COMMAND_GUIDES/06_DASHBOARD_COMMANDS.md`
- Report evidence: `07_REPORT_EVIDENCE/`, `08_SELECTED_FIGURES/`, and `09_SELECTED_TABLES/`

## Known Limitations
- No 19-node official demo scale exists in the inspected workspace; S1 50-node is the smallest validated live demo.
- The final demo workspace is intentionally curated. Some heavy source-tree artifacts remain in the original workspace and are not copied here.
- SSH push may require HTTPS or a loaded GitHub key, depending on the machine state.

## Demo Rule
If in doubt, show the documentation and the smallest verified command path first.
