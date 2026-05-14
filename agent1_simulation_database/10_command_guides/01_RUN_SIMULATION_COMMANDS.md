# Run Simulation Commands

## Go to the workspace
```bash
cd /home/cyfer/FYP/WSN_simulation
```

## Official 50-node simulation
```bash
cd /home/cyfer/FYP/WSN_simulation/04_scale_runs/S1_50_nodes/simulations_50_to_5000
bash run_baseline.sh
bash run_active_healing.sh
```

## Official 100-node simulation
```bash
cd /home/cyfer/FYP/WSN_simulation/04_scale_runs/S2_100_nodes/simulations_50_to_5000
bash run_baseline.sh
bash run_active_healing.sh
```

## Check for 19-node or demo-scale runs
```bash
find /home/cyfer/FYP/WSN_simulation -iname "*19*" -o -iname "*demo*" | head -50
```

19-node simulation is not an official validated scale. Use S1 50-node for a safe live demonstration.

## Run with DB import
```bash
bash run_baseline.sh --import-db
bash run_active_healing.sh --import-db
```

## Run without DB import
```bash
bash run_baseline.sh --no-import
```

## Live-demo safety
Safe live demo:
- S1 50-node baseline without DB import
- S1 50-node active healing without DB import
- S2 100-node only if time allows

Too heavy for live demo:
- full batch runs
- large-scale exports
- any command that rebuilds or reruns the full dataset
