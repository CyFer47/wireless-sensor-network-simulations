# ML Demo Commands

## Demo folder
Use the curated notebook and backup script in the final demo workspace:

```bash
cd /home/cyfer/FYP/FINAL_DEMO_WORKSPACE/05_ML_DEMO/ML_supervisor_demo
```

## Optional local setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter notebook
```

## Backup script
```bash
python3 03_demo_scripts/run_supervisor_demo.py
```

## Model summary
- Model A: recovery-time regression
- Model B: delivery/recovered-cluster outcome regression; energy is not usable as a claim target
- Model C: pairwise active-healing vs H0 classifier, not a full 5-way selector

## Safe / unsafe claims
Safe to say:
- the dataset split was verified
- the supervisor demo reproduces the approved metrics
- feature importance was summarized and reviewed

Unsafe to say:
- energy prediction is strong
- the classifier is a full optimizer for all healing families
- the model generalizes beyond the verified demo domain

## Where to look
- notebook: `ML_supervisor_demo/WSN_ML_SUPERVISOR_DEMO.ipynb`
- script: `ML_supervisor_demo/run_supervisor_demo.py`
- summary: `ML_supervisor_demo/README_SUPERVISOR_DEMO.md`
