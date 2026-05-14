# Agent 1 Packaging Staging Folder

This folder is the clean staging area for Agent 1 source material that will later be copied into the final GitHub repository `wsn-self-healing-bsbssp-research`.

## What Agent 1 owns
- VMware-side simulation and environment work
- ns-3 scenario and milestone source files
- PostgreSQL schema, validation, and query SQL
- importer scripts
- web dashboard backend and frontend source
- run-spec templates and selected examples
- selected map examples
- milestone and S7 documentation

## What is included
- `docs/` - milestone, operator, planning, acceptance, and query-proof markdown
- `sql/` - schema, migration, verification, and compatibility SQL
- `importer/` - import/export/connectivity scripts
- `tools/` - map generation, validation, launcher, and batch utilities
- `runspecs/` - base runspec plus selected examples and templates
- `maps/examples/` - selected small generated map examples only
- `web_dashboard/` - dashboard backend/frontend source and docs
- `ns3/` - simulation source and milestone scenario files
- `config_examples/` - example-only config files
- `results_summary/` - summary-level results docs only

## What is excluded
- `.env` files with real credentials
- `.venv/`
- `outputs/` raw run artifacts
- `__pycache__/`
- logs
- database dumps
- compiled binaries
- temporary files and caches

## How this supports the research paper
This staging folder collects the reproducible source, configuration examples, validation SQL, and narrative documentation needed to package the research workflow cleanly for GitHub without leaking secrets or bulky generated output.

## Notes
- Original workspace files were not moved or deleted.
- Only selected examples and summary files are staged; raw outputs remain in the source workspace.

## Security / local configuration
- Copy the provided `.env.example` files to local `.env` files before running anything.
- Fill in your own local database host, username, and password values.
- Never commit `.env`, logs, raw outputs, or database dumps.
- Use the staged example files only as templates for local setup.
