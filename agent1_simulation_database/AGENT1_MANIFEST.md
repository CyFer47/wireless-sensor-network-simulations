# Agent 1 Manifest

This manifest lists the Agent 1 files and folders added to this repository and their source locations.

## Summary
- Added Agent 1 content (simulation source, tools, database helpers, dashboard, scale run examples, Phase2A reports, final demo, DATA, command guides).
- Source locations are primarily under `/home/cyfer/FYP/WSN_simulation`, `/home/cyfer/FYP/github_export/agent1_simulation_platform`, `/home/cyfer/FYP/FINAL_DEMO_WORKSPACE`, `/home/cyfer/FYP/outputs`, and `/home/cyfer/FYP/garbage/.../report_materials`.

## Top-level Agent1 folders and primary sources
- `01_simulation_source/` — copied from `/home/cyfer/FYP/github_export/agent1_simulation_platform/ns3/test-ns3/` (includes `m3-scenario-library.cc` and supporting C++ files).
- `02_tools/` — copied from `/home/cyfer/FYP/WSN_simulation/02_tools/` and `/home/cyfer/FYP/github_export/agent1_simulation_platform/tools/` (Python helpers, runners).
- `03_database/` — schema and import/export scripts copied from `/home/cyfer/FYP/WSN_simulation/03_database/` and importer helpers.
- `04_dashboard/` — backend and frontend small sources copied from `/home/cyfer/FYP/garbage/WSN Dashboard Milestone V2/web-monitor/`.
- `05_scale_runs/` — representative scale folders `S1_50_nodes` and `S2_100_nodes` with run scripts and manifests (excludes local_outputs/raw outputs).
- `06_phase2A/` — Phase2A diagnostic and patch report copied from `/home/cyfer/FYP/outputs/` and final demo sources.
- `07_final_demo_workspace/` — key final demo README and run-order from `/home/cyfer/FYP/FINAL_DEMO_WORKSPACE/00_START_HERE/`.
- `08_report_materials/` — selected report MD/CSV files from report_materials.
- `09_DATA/` — curated DATA folder copied from `/home/cyfer/FYP/FINAL_DEMO_WORKSPACE/DATA/` (official ML CSVs and checksums).
- `10_command_guides/` — terminal command guides copied from final demo workspace command guides.

## Excluded items (intentionally not copied)
- `.env` files and other local credential files (excluded)
- `.venv` and virtual environment directories (excluded)
- Database dumps and `.sql` backups (excluded unless schema files)
- Raw `local_outputs/` and `raw_outputs/` directory contents (excluded)
- node_modules, build artifacts, compiled binaries, and CMake build folders (excluded)

## Safety notes
- All files were scanned for unsafe patterns (no `.env`, no `.venv`, no large DB dumps found in the added content).
- Any remaining symlinks were dereferenced and real file copies were added to avoid absolute symlink breakage on other machines.

## Next steps
- Review the staged content locally. If you want me to push this commit to GitHub now, I will attempt `git push origin main` and report the result.
