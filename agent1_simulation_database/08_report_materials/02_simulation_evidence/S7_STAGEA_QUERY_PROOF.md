# S7 Stage A Query Proof

Date: 2026-04-22
Status: Passed

## Connection Context

All checks executed against local PostgreSQL:

- host: `127.0.0.1`
- database: `wsn_sim`
- schema: `wsn`

## Proof 1: S7 Rows Exist In Metadata Gate View

SQL:

```sql
SET search_path TO wsn, public;
SELECT COUNT(*)
FROM runs_m7_metadata_gate
WHERE scale_id='S7';
```

Result:

- `12`

## Proof 2: Queryability By Architecture / Failure / Healing / Load / Seed / Run Status

SQL:

```sql
SELECT architecture_id, failure_family_id, healing_id, load_id, seed, run_status, COUNT(*)
FROM runs_m7_metadata_gate
WHERE scale_id='S7'
GROUP BY architecture_id, failure_family_id, healing_id, load_id, seed, run_status
ORDER BY architecture_id, failure_family_id, healing_id, load_id;
```

Result summary:

- A and B both present
- families/healing present exactly as Stage A design (`F0/H0`, `F1/H1`, `F4/H4`)
- both loads present (`L1`, `L2`)
- seed fixed at `1`
- run_status all `complete`

## Proof 3: Topology Lineage Queryability

SQL:

```sql
SELECT topology_map_id, topology_map_version, COUNT(*)
FROM runs_m7_metadata_gate
WHERE scale_id='S7'
GROUP BY topology_map_id, topology_map_version
ORDER BY topology_map_id;
```

Result:

- `map_S7_seed01 | m2_map_v1 | 12`

## Proof 4: Complete vs Partial

SQL:

```sql
SELECT COUNT(*)
FROM runs
WHERE scale='S7' AND seed=1 AND run_status <> 'complete';
```

Result:

- `0`

## Proof 5: Baseline Presence

SQL:

```sql
SELECT COUNT(*)
FROM runs
WHERE scale='S7' AND failure_family='F0' AND healing_id='H0';
```

Result:

- `4`

## Proof 6: Matched A/B Pair Presence

SQL:

```sql
SELECT COUNT(*)
FROM runs ra
JOIN runs rb
  ON ra.failure_family=rb.failure_family
 AND ra.healing_id=rb.healing_id
 AND ra.load=rb.load
 AND ra.scale=rb.scale
 AND ra.seed=rb.seed
WHERE ra.scale='S7'
  AND ra.architecture='A'
  AND rb.architecture='B'
  AND ra.failure_family='F1'
  AND ra.healing_id='H1';
```

Result:

- `2` matched pairs (`L1`, `L2`)

## Conclusion

S7 Stage A rows are queryable by all required axes, complete/partial filtering works, and topology lineage is present.
