# M7 Progress Report

Date: 2026-04-14
Status: In progress

## Batch Scope

- planned runs (runnable M7 matrix): 864
- launch mode: resumable serial execution (`tools/run_m7_production_batch.py`)

## Live Snapshot

Snapshot source:

- `outputs/m7_state.json`
- `outputs/m7_quarantine.json`

Current counts:

| Metric | Count |
|---|---:|
| planned runs | 864 |
| launched runs (processed so far) | 47 |
| completed runs | 47 |
| imported runs | 47 |
| failed runs | 0 |
| partial runs | 0 |
| quarantined runs | 0 |

## Breakdown: Completed/Imported So Far

### By architecture

| Architecture | Count |
|---|---:|
| A | 24 |
| B | 23 |

### By failure family

| Failure Family | Count |
|---|---:|
| F0 | 47 |
| F1 | 0 |
| F2 | 0 |
| F3 | 0 |
| F4 | 0 |

### By scale

| Scale | Count |
|---|---:|
| S1 | 16 |
| S2 | 16 |
| S3 | 15 |
| S4 | 0 |
| S5 | 0 |
| S6 | 0 |

### By load

| Load | Count |
|---|---:|
| L1 | 24 |
| L2 | 23 |

### By seed

| Seed | Count |
|---|---:|
| 01 | 12 |
| 02 | 12 |
| 03 | 12 |
| 04 | 11 |

## Health Summary

- launch failures: none
- import failures: none
- quarantine entries: none
- metadata gate status: passed

## Notes

- M7 runner is active and progressing through V1 control rows across scales/seeds/architectures.
- First generated S3 maps are validated and used successfully.
- `run_id` remains the DB anchor via importer inserts.

## Next Checkpoint

At 100 processed rows:

- refresh this report
- run query-proof subset
- run dashboard sanity check
