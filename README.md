# Wireless Sensor Network Self-Healing Simulation Research

This repository organizes deliverables across three agents:

1. `agent1_simulation_database/` — simulation, database, dashboard, and final demo workspace (Agent 1)
2. `agent2_matlab_validation/` — MATLAB validation workspace (Agent 2)
3. `agent3_ml_analysis/` — ML analysis workspace (Agent 3) **NEW**

## Agent 3: ML Workspace V2

Agent 3 contains fresh ML analysis of WSN simulation results using machine learning:

- **Three trained models**: Recovery time prediction, run outcomes regression, active-healing vs H0 classifier
- **Comprehensive documentation**: Safe/unsafe claims, limitations, safe claims, training reports
- **Reproducible code**: Training scripts, preprocessing module, requirements for dependencies
- **Demo and verification**: Supervisor demo script, data verification, leakage audit
- **Results**: JSON metrics for all models, summary CSV table for Excel import

**Key findings**: Model A predicts recovery time accurately. Model B predicts delivery ratio and clusters accurately, but energy prediction is not usable (R²=-1.94). Model C is pairwise binary classifier (active healing vs H0), not a 5-way selector.

**Start here**: See `agent3_ml_analysis/00_START_HERE/README_AGENT3.md`

**Critical limitations**: Energy prediction unreliable. Model C is pairwise only. ML is offline analysis. Results valid in tested domain (S1-S11) only.

---

**Current status:** ✅ Agent 1 uploaded. ✅ Agent 2 uploaded. ✅ Agent 3 uploaded.
