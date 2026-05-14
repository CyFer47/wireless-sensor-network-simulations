# M7 Query Proof

Date: 2026-04-14
Status: Active

## A vs B Queryability and Pairability

```sql
SELECT architecture_id, COUNT(*)
FROM runs_m7_metadata_gate
GROUP BY architecture_id
ORDER BY architecture_id;
```

```sql
SELECT
  a.run_id AS run_a,
  b.run_id AS run_b,
  a.failure_family_id,
  a.healing_id,
  a.scale_id,
  a.load_id,
  a.seed
FROM runs_m7_metadata_gate a
JOIN runs_m7_metadata_gate b
  ON a.failure_family_id = b.failure_family_id
 AND a.healing_id = b.healing_id
 AND a.scale_id = b.scale_id
 AND a.load_id = b.load_id
 AND a.seed = b.seed
WHERE a.architecture_id = 'A'
  AND b.architecture_id = 'B'
  AND a.run_status = 'complete'
  AND b.run_status = 'complete';
```

## Complete vs Partial Filtering

```sql
SELECT run_status, COUNT(*)
FROM runs_m7_metadata_gate
GROUP BY run_status
ORDER BY run_status;
```

## Scenario Axes Queryability

```sql
SELECT failure_family_id, healing_id, variant_id, load_id, scale_id, seed, COUNT(*)
FROM runs_m7_metadata_gate
GROUP BY failure_family_id, healing_id, variant_id, load_id, scale_id, seed
ORDER BY failure_family_id, healing_id, variant_id, scale_id, load_id, seed;
```

## Representative A/B Candidates

```sql
SELECT DISTINCT ON (failure_family_id, scale_id, load_id)
  run_id,
  architecture_id,
  failure_family_id,
  healing_id,
  variant_id,
  scale_id,
  load_id,
  seed
FROM runs_m7_metadata_gate
WHERE run_status = 'complete'
ORDER BY failure_family_id, scale_id, load_id, architecture_id, seed, run_id;
```

## Stress-Load Filtering

```sql
SELECT scale_id, architecture_id, COUNT(*)
FROM runs_m7_metadata_gate
WHERE load_id = 'L2'
GROUP BY scale_id, architecture_id
ORDER BY scale_id, architecture_id;
```

## Per-Scale Progress Tracking

```sql
SELECT scale_id, run_status, COUNT(*)
FROM runs_m7_metadata_gate
GROUP BY scale_id, run_status
ORDER BY scale_id, run_status;
```

## Event Code or Class Availability

```sql
SELECT event_code, event_class, COUNT(*)
FROM events_m7_metadata_gate
GROUP BY event_code, event_class
ORDER BY COUNT(*) DESC;
```
