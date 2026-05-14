# ML Dataset Split Decision

This dataset uses a deterministic split by scale:

- Train: S1-S9
- Validation: S10
- Test: S11

## Why this split

- No random leakage: the split is based only on scale, not on row order or random sampling.
- Scale generalization: the model sees the lower and mid scales during training and must generalize upward.
- Final 5000-node S11 is reserved as an unseen test scale.
- S10 is held out as the validation scale for tuning and model selection.

This split is fixed for ML V1 dataset export.
