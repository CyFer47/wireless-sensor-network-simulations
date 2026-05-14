# FINAL_SCALE5000 S8 Stage B MATLAB Go/No-Go

Date: 2026-05-01

## Stage B MATLAB gate checks

- Stage B target rows visible in MATLAB: **32 / 32**
- A/B, L1/L2, seed01/seed02, and F1/H1..F4/H4 visibility: **pass**
- Map lineage fields (`map_id`, `map_signature`) available: **pass** (`missing=0`)
- Representative runs loaded with full table counts: **pass**
- Stress/healing marker extraction: **pass** (required markers present)
- Representative plotting warnings: **pass** (no legend truncation or vector PDF warnings)
- Plot outputs and diagnostic file generated: **pass**

## Run-id continuity caveat decision

- Caveat statement: Stage A re-import lineage introduced `969/970/971` continuity concern.
- MATLAB finding: no duplicate-key conflict remains in the complete Stage B keyspace.
- Decision: **accepted**, with mandatory deterministic rule:
  - Always select latest complete run per `(scale, architecture, failure_family, healing_id, load, seed)`.

## Final decision

- S8 Stage B MATLAB passed: **YES**
- Safe to proceed to S8 Stage C: **YES**

Scope note:

- This decision applies to S8 Stage B MATLAB representative QA only.
- This document does not start Stage C execution.
