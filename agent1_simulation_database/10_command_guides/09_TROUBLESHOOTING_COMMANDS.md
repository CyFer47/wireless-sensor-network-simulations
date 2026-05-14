# Troubleshooting Commands

## PostgreSQL connection fail
```bash
psql -h 127.0.0.1 -U wsn_user -d wsn_sim
```
Check whether the service is running and whether the host/port match the VM.

## DB import fail
```bash
python3 /home/cyfer/FYP/WSN_simulation/03_database/import_export/import_run_to_postgres.py <RUN_FOLDER>
```
Confirm the run folder exists and contains the expected export files.

## ns-3 launcher missing
```bash
cd /home/cyfer/ns-allinone-3.42/ns-3.42
./ns3 --help
```

## Permission denied
```bash
ls -la
chmod +x run_baseline.sh
```

## GitHub push auth issue
```bash
ssh -T git@github.com
ssh-add -l
```
If SSH fails, use the HTTPS remote and rebase before pushing.

## MATLAB JDBC fail
- Verify host `192.168.1.7` and port `5432`.
- Confirm the DB password is set only in the local `.env` or local MATLAB config.
- Re-run `test_db_connection()`.

## Wrong path or case sensitivity
```bash
pwd
find /home/cyfer/FYP/WSN_simulation -iname '*s1*' -o -iname '*S1*'
```

## Phase2A scale-rule issue
The S12/S13 `ScaleRule` issue is already fixed in `m3-scenario-library.cc`.
Do not re-run the old failing path unless you intentionally want to verify the patch again.
