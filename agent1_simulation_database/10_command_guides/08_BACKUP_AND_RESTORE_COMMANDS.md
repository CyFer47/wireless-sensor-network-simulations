# Backup and Restore Commands

## Database backup
```bash
mkdir -p /home/cyfer/FYP/archive/db_backups
pg_dump -h 127.0.0.1 -U wsn_user -d wsn_sim > /home/cyfer/FYP/archive/db_backups/wsn_sim_final_demo_backup.sql
```

## Workspace backup example
```bash
mkdir -p /home/cyfer/FYP/archive/final_demo_workspace_backup
rsync -a --exclude '.env' --exclude '.venv' --exclude '*.log' --exclude '*.sql' --exclude 'raw_outputs_full' \
  /home/cyfer/FYP/FINAL_DEMO_WORKSPACE/ /home/cyfer/FYP/archive/final_demo_workspace_backup/
```

## Restore guidance
- Restore only curated docs and small demo assets from archive.
- Avoid restoring raw exports or large generated datasets into the demo workspace.
