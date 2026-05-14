# PHASE 05 STAGE C - Viva Explanation

## What does the ML model do?
It analyzes the verified Phase 04 wireless sensor network dataset and predicts recovery-related outcomes from pre-recovery features. The model families are recovery-time regression, run-outcome regression, and pairwise healing classification.

## What does it not do?
It does not run new simulations, retrain the official split, modify PostgreSQL, or prove that the same behavior will hold in every real wireless sensor network deployment.

## Why are some scores perfect?
Some scores are perfect because several outcomes in the tested dataset are deterministic under the available pre-recovery features. The leakage audit also showed that Stage B1 included unsafe post-simulation features, so the perfect scores must be interpreted carefully.

## Why is energy prediction poor?
Energy consumption remains hard to predict from pre-recovery features. The safe Model B2 test R2 is negative, which means the model performs worse than a simple baseline mean predictor.

## Why is this still useful?
It shows which outcomes are predictable from safe pre-recovery inputs, which outcomes are deterministic in the tested domain, and which outcomes still need better feature design or temporal analysis.

## Short viva script
"The ML system uses the official Phase 04 dataset with a fixed S1 to S11 split. We audited the earlier models and removed unsafe post-simulation features. After that, recovery delay, delivery ratio, and cluster recovery remained deterministic in the tested domain, while energy consumption stayed difficult to predict. So the contribution is not just a model score, but a leakage-audited and reproducible analysis of what can and cannot be predicted safely from pre-recovery information."
