# M6 Pilot Results

Date: 2026-04-14
Status: Complete

## Planned Pilot Size

- total planned runs: 68

## Results Summary

| Metric | Count |
|---|---:|
| total completed runs | 68 |
| total imported runs | 68 |
| failed runs | 0 |
| partial runs | 0 |
| complete runs | 68 |

## By Architecture

| Architecture | Count |
|---|---:|
| A | 34 |
| B | 34 |

## By Failure Family

| Failure Family | Count |
|---|---:|
| F0 | 2 |
| F1 | 18 |
| F2 | 16 |
| F3 | 16 |
| F4 | 16 |

## By Scale

| Scale | Count |
|---|---:|
| S1 | 36 |
| S2 | 32 |

## By Load

| Load | Count |
|---|---:|
| L1 | 36 |
| L2 | 32 |

## By Seed

| Seed | Count |
|---|---:|
| 01 | 36 |
| 02 | 32 |

## Queryability Summary

- A/B queryability: proven
- complete vs partial filtering: proven
- failure family filtering: proven
- healing ID filtering: proven
- scale, load, and seed filtering: proven
- representative QA candidate selection: proven

## Dashboard Visibility

- dashboard backend reachable on port 8083
- imported pilot rows are visible to DB-backed dashboard queries

## Systematic Issues

- none discovered in the pilot batch
- all 68 planned runs exported and imported cleanly
- no partial or failed rows were produced during the pilot

## Notes

- `run_id` remained the DB anchor for every imported row.
- `run_status` remained `complete` for every pilot row.
- The pilot is stable enough to proceed to M7 planning.
