# ML Export Summary

- Workspace: /home/cyfer/FYP/WSN_simulation
- Backup path: /home/cyfer/FYP/archive/db_backups/wsn_sim_before_ml_dataset_export.sql

## Exported files

- ml_run_outcomes.csv: 1148 rows
- ml_healing_candidates.csv: 1148 rows
- ml_best_healing_labels.csv: 636 rows
- ml_recovery_time_regression.csv: 520 rows
- dataset_split_manifest.csv: 1148 rows

## Split counts

- train: 1012
- validation: 68
- test: 68

## Missing value summary

| field | missing count |
| --- | --- |
| architecture | 0 |
| failure_family | 0 |
| healing_id | 0 |
| load | 0 |
| map_signature | 0 |
| scale | 0 |
| seed | 0 |

## Event marker limitations

- Event marker fields were derived from message patterns and earliest matching events; some rows may not expose all timing markers.
- If a recovered aggregate was not observable, the regression export falls back to recovery_applied_delay_s and notes the source.

## Seed03/seed04 note

- seed03/seed04 were not executed for this ML V1 export.
- They are deferred for later topology-generalization testing.

- No model training was performed.