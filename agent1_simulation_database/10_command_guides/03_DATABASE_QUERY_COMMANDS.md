# Database Query Commands

## Connect with psql
```bash
psql -h 127.0.0.1 -U wsn_user -d wsn_sim
```

## Basic checks
```sql
SELECT COUNT(*) FROM wsn.runs;

SELECT run_id, experiment_version, scale, node_count, run_status, started_at
FROM wsn.runs
ORDER BY run_id DESC
LIMIT 10;

SELECT COUNT(*) FROM wsn.run_summary;

SELECT COUNT(*) FROM wsn.events;

SELECT run_id, final_agg_rx, final_consumed_j, final_recovered_clusters
FROM wsn.run_summary
ORDER BY run_id DESC
LIMIT 10;
```

## Phase2A live DB checks
```sql
SELECT COUNT(*)
FROM wsn.runs
WHERE experiment_version LIKE 'S500_%'
   OR experiment_version LIKE 'S1000_%';

SELECT run_status, COUNT(*)
FROM wsn.runs
WHERE experiment_version LIKE 'S500_%'
   OR experiment_version LIKE 'S1000_%'
GROUP BY run_status;
```

## Event marker examples
```sql
SELECT run_id, event_type, event_time_s, cluster_id, node_id, message
FROM wsn.events
ORDER BY run_id DESC, event_time_s DESC
LIMIT 25;
```

## Demo notes
- Use read-only queries in the viva.
- Prefer latest-run summaries over deep table browsing.
- Keep any write queries out of the live demo.
