# Dataset Split Explanation

## Train/Validation/Test Split Strategy

The ML dataset was split across simulation scales without random shuffling:

- **Train**: S1 through S9 (50 to 4000 nodes)
- **Validation**: S10 (4500 nodes)
- **Test**: S11 (5000 nodes, final scale, unseen during training)

## Design Rationale

1. **Progressive scale validation**: Train on moderate scales, validate on intermediate scale, test on final scale.
2. **No random split**: Scales are naturally separated to ensure the model generalizes across increasing complexity.
3. **S11 as final test**: The largest and most comprehensive scale (S11 5000-node) serves as the unseen test set.

## Row Counts

- Total runs: 1148
- Train runs: approximately 810 (S1-S9)
- Validation runs: approximately 169 (S10)
- Test runs: approximately 169 (S11)

## Verification

To verify the split:

```bash
python3 - <<'PY'
import pandas as pd
df = pd.read_csv("dataset_split_manifest.csv")
print("Split counts:")
print(df["split"].value_counts())
print("\nSplit by scale:")
print(df.groupby(["split", "scale"]).size())
PY
```

## Why This Matters

- **Generalization**: By testing on S11 (unseen scale), we verify the model generalizes beyond training data complexity.
- **Production readiness**: A model that works on S1-S11 is ready for deployment on new scales.
- **Safety for claims**: We avoid overfitting to a single scale by testing on progressively larger networks.
