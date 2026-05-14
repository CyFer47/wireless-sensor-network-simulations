# Import to Database Commands

## Import a single run folder
```bash
python3 /home/cyfer/FYP/WSN_simulation/03_database/import_export/import_run_to_postgres.py \
  /home/cyfer/FYP/WSN_simulation/04_scale_runs/S1_50_nodes/local_outputs/<RUN_FOLDER>
```

## Find the latest run folder
```bash
ls -lt /home/cyfer/FYP/WSN_simulation/04_scale_runs/S1_50_nodes/local_outputs | head
```

## Safe demo import flow
1. Run a small simulation.
2. Confirm the output folder exists.
3. Import that single folder.
4. Verify the row counts with `psql`.

## Notes
- Do not import large raw archives during the viva.
- Do not change database rows manually unless the command is specifically documented as a demo import.
