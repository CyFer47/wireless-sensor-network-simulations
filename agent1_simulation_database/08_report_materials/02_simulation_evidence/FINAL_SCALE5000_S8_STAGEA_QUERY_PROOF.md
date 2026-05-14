# Final Scale5000 — S8 Stage A Query Proof

Live PostgreSQL proof collected after the S8 Stage A batch completed.

## Database Reachability
- target DB reachable: yes
- schema `wsn` exists: yes
- metadata views exist: yes

## Query Proof
The following queries succeeded against the live database and returned valid results (including empty/zero where applicable):

- `SELECT MAX(run_id) FROM wsn.runs;` → 962
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8';` → 12
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8' AND run_status='complete';` → 12
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8' AND architecture='A';` → 6
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8' AND architecture='B';` → 6
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8' AND load='L1';` → 6
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8' AND load='L2';` → 6
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8' AND failure_family='F0';` → 4
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8' AND failure_family='F1';` → 4
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8' AND failure_family='F4';` → 4
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8' AND healing_id='H0';` → 4
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8' AND healing_id='H1';` → 4
- `SELECT COUNT(*) FROM wsn.runs WHERE scale='S8' AND healing_id='H4';` → 4

## Required Fields Present
The live `runs` rows expose the required fields for S8 queryability:
- scale
- architecture
- failure_family
- healing_id
- load
- seed
- run_status
- map_id
- map_signature

## Sample Rows
The first three S8 rows returned by the proof query:

- `951` — `F0_H0_A_S8_L1_seed01` — `S8` / `A` / `F0` / `H0` / `L1` / seed 1 / `complete` / `map_S8_seed01`
- `952` — `F0_H0_A_S8_L2_seed01` — `S8` / `A` / `F0` / `H0` / `L2` / seed 1 / `complete` / `map_S8_seed01`
- `953` — `F0_H0_B_S8_L1_seed01` — `S8` / `B` / `F0` / `H0` / `L1` / seed 1 / `complete` / `map_S8_seed01`

## Conclusion
S8 rows are queryable by the full required metadata set, and scale-filtered queries do not error.
