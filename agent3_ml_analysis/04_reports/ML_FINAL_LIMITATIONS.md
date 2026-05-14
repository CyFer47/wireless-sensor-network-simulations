# ML Workspace V2 - Final Limitations

**Critical Document** - Read before making any claims based on ML models

---

## Executive Summary

The ML models in Agent 3 have significant limitations that must be understood:

1. **Energy prediction is NOT usable** - test R² = -1.94 (worse than baseline)
2. **Model C is pairwise only** - binary active-healing vs H0, not 5-way selector
3. **ML is offline analysis** - not live closed-loop WSN control
4. **Results valid in tested domain only** - S1-S11 simulation scenarios
5. **Perfect fits may not generalize** - strong within simulator, uncertain in reality

---

## Limitation 1: Energy Prediction is Unreliable

### The Problem
```
Model B Target: final_consumed_j (energy consumed)
Best Algorithm: Decision Tree
Train R²: 1.00 (perfect fit)
Val R²:   0.16 (poor)
Test R²: -1.94  ❌ WORSE THAN BASELINE
```

### Why This Matters
- **Negative R² means**: Model predictions are worse than simply predicting the mean value
- **All three algorithms failed**: Decision Tree, Random Forest, Gradient Boosting all show same problem
- **Severe overfitting**: Large gap between train (1.00) and test (-1.94)
- **Test MAE**: 567.79 Joules (very large error)

### What This Means
**ENERGY PREDICTIONS CANNOT BE USED FOR ANY PURPOSE**

### Why It Might Be Happening
Possible causes:
- Energy calculation in simulator is not deterministic from available features
- Energy depends on features not in the dataset
- Energy is highly stochastic or random in simulator
- Feature engineering needed (not completed)

### Action Required
If energy prediction is needed:
1. Investigate energy calculation in simulator source code
2. Add new features that relate to energy consumption
3. Consider energy as not predictable from current feature set
4. Do NOT use current Model B energy predictions

---

## Limitation 2: Model C is Pairwise Only

### The Scope
```
Model C: Binary Classifier
Target: active_healing_beats_H0
Classes: [0] H0 is best, [1] Active healing beats H0

⚠️ EXPLICITLY NOT:
❌ Full 5-way best-healing selector (H0, H1, H2, H3, H4)
❌ Individual comparison between H1, H2, H3, H4
❌ Healing method ranking
❌ Multi-class classifier for all healing methods
```

### What Model C Can Do
✅ Compare: "Does ANY active healing strategy beat H0?"  
✅ Identify: "Active healing is beneficial or not"  
✅ Analyze: "Overall effectiveness of active healing"

### What Model C CANNOT Do
❌ Select: "Which specific healing method (H1/H2/H3/H4) is best?"  
❌ Compare: "Is H1 better than H2?"  
❌ Rank: "Order healing methods by effectiveness"  
❌ Provide: "5-way best-healing recommendation"

### Class Imbalance Problem
```
Test Set Distribution:
- Class 0 (H0 best): 52 samples (76.5%)
- Class 1 (Active best): 16 samples (23.5%)

Model Behavior on Test Set:
- Predicts majority class (0) for all samples
- Minority class F1 score: 0.0
- Cannot identify when active healing is beneficial
```

### Why This Limitation Exists
1. **Model was trained for pairwise comparison only** - Not designed as multi-class
2. **Class imbalance is real** - 77.7% baseline says H0 is best in dataset
3. **Binary features** - Only 5 features (outcome metrics), not rich feature set
4. **Scope limitation** - Not part of project scope to build 5-way selector

### What This Means
Do NOT claim Model C can:
- Select the best healing method
- Recommend among H1, H2, H3, H4
- Provide automatic healing selection
- Guarantee active healing is always checked

### If Full Selector Needed
Building a true 5-way best-healing selector would require:
1. New model architecture (multi-class, not binary)
2. Better feature engineering
3. Balancing techniques for class imbalance
4. Explicit comparison between all healing methods
5. Significant retraining effort

---

## Limitation 3: ML is Offline Analysis, Not Closed-Loop Control

### What These Models DO
✅ Analyze past simulation results
✅ Find patterns in historical data
✅ Predict outcomes given configuration
✅ Explain simulator behavior

### What These Models DO NOT DO
❌ Make real-time decisions in live system
❌ Adapt to network changes
❌ Provide live control signals
❌ Replace simulator or real system
❌ Function in real wireless network

### Why This Matters
**These models cannot be deployed as a live WSN controller.** They are research tools for understanding simulation behavior, not production software.

### Use Cases (Valid)
✅ Analyze simulation results post-hoc
✅ Understand relationships between inputs and outputs
✅ Generate hypotheses about network behavior
✅ Support research and paper writing
✅ Validate simulator behavior

### Use Cases (Invalid)
❌ Live network control
❌ Real-time healing decisions
❌ Embedded system deployment
❌ Operational decision support
❌ Replacing actual WSN protocols

---

## Limitation 4: Results Valid in Tested Domain Only

### The Domain
```
Simulation Scenarios: S1 through S11
Training Set: S1-S9 (1012 scenarios)
Validation Set: S10 (68 scenarios)
Test Set: S11 (68 scenarios)
```

### What's Tested
✅ 1148 specific simulation scenarios (S1-S11)
✅ Particular node counts, topologies, failures
✅ Specific healing strategies (H0, H1, H2, H3, H4)
✅ Failure types and magnitudes in dataset

### What's NOT Tested
❌ Different network sizes outside S1-S11
❌ New node types or architectures
❌ Scenarios not in S1-S11
❌ Future simulation modifications
❌ Real wireless networks

### The Problem
**Perfect fit (R² = 1.0) may indicate model learned simulator-specific patterns, not generalizable relationships.**

### Real-World Concerns
If applying to new scenarios:
- Perfect fit may not transfer
- Network size changes → model may fail
- New failure types → untested
- Real system → likely different
- Future simulator changes → model outdated

### Safe Boundaries
✅ Claim: "Models predict outcomes within tested simulation domain S1-S11"  
❌ Claim: "Models predict any scenario" or "Models work on real networks"

---

## Limitation 5: Perfect Fit May Indicate Overfitting

### The Situation
```
Model A: R² = 1.0 on recovery time (train, val, test all perfect)
Model B (delivery): R² = 1.0 on delivery ratio (train, val, test all perfect)
Model B (clusters): R² = 1.0 on clusters (train, val, test all perfect)
```

### Why This is Concerning
1. **Perfect fit is rare** in real ML unless data is deterministic
2. **Simulator is deterministic** - likely reason for perfect fit
3. **Tree-based models** can perfectly memorize patterns
4. **No generalization guarantee** to unseen systems

### Two Interpretations

**Optimistic Interpretation**
- ✅ Features deterministically determine outcomes
- ✅ Simulator correctly captures relationships
- ✅ Models learned true underlying logic

**Pessimistic Interpretation**
- ❌ Models memorized specific patterns
- ❌ Perfect fit is simulator-artifact
- ❌ Real systems won't match this
- ❌ Models are brittle and sensitive

### Reality Likely In Between
The models probably captured real simulator logic (optimistic) BUT may not generalize well to:
- Real hardware variations
- Different network sizes
- Unmodeled failure modes
- Real-world stochasticity

### Safe Claim
✅ "Models exhibit perfect fit within the tested simulation domain"  
✅ "Models accurately replicate simulator behavior for S1-S11"  
⚠️ "Models may or may not transfer to other systems"  
❌ "Models are universally applicable"  
❌ "Models guarantee performance on real systems"

---

## Limitation 6: Data Leakage Prevention Verified, But Not Exhaustive

### What We Checked
✅ 18 forbidden columns identified and excluded
✅ Recovery outcome columns (all-NA or mostly-NA) removed
✅ Categorical encoding applied correctly
✅ Train/validation/test split maintained

### What We Did NOT Check
⚠️ Future information leakage (features calculated after outcome?)
⚠️ Indirect information through feature correlations
⚠️ Subtle data preprocessing artifacts
⚠️ Simulator implementation details affecting features

### Confidence Level
**High confidence** in preventing explicit data leakage  
**Moderate confidence** in catching subtle leakage  
**Unknown** whether simulator has built-in dependencies

---

## Limitation 7: Limited Feature Set

### Features Used
- **Model A**: 14 features (configuration + network topology)
- **Model B**: 21 features (broader set with healing parameters)
- **Model C**: 5 features (outcome metrics, not configs)

### Potential Missing Features
For better predictions, could add:
- Power/energy profiles per node type
- Thermal characteristics
- Network congestion metrics
- Packet loss patterns
- Healing protocol version/configuration
- Node state evolution over time
- Temporal features (time-of-day, timestamp)
- Advanced network statistics

### Why This Matters
- Limited features may miss important predictors
- Energy prediction (R² = -1.94) might improve with better features
- Model C might benefit from configuration features instead of outcome metrics

---

## Limitation 8: Class Imbalance in Model C Not Addressed

### The Issue
```
Dataset: 77.7% class 0 (H0 best), 22.3% class 1 (active best)
Test Set: 76.5% class 0, 23.5% class 1

Result: All models predict majority class on test set
Minority F1: 0.0 (cannot identify when active healing wins)
```

### Standard Solutions Not Applied
❌ SMOTE (Synthetic Minority Oversampling)
❌ Class weights/balancing
❌ Custom loss functions
❌ Threshold adjustment
❌ Ensemble rebalancing

### Why Not Applied
Out of project scope; focus was on three models with standard settings.

### If Better Minority Prediction Needed
- Rebalance training data
- Use weighted loss functions
- Adjust classification threshold
- Ensemble methods
- Custom evaluation metrics (F1, PR-AUC instead of accuracy)

---

## Summary: What You Can Claim

### ✅ SAFE TO CLAIM
- Model A predicts recovery time within tested S1-S11 domain
- Model B accurately predicts delivery ratio
- Model B accurately predicts recovered clusters
- Official split was maintained (S1-S9 / S10 / S11)
- Data leakage was prevented
- S11 was not used for training/tuning
- Model C provides pairwise comparison (active vs H0)

### ❌ DO NOT CLAIM
- Model B can predict energy consumption (R² = -1.94)
- Model C is a best-healing selector (it's binary only)
- Model C can recommend specific healing methods (H1/H2/H3/H4)
- Models work on real networks
- Models generalize to new scenarios/domains
- ML provides live network control
- Perfect fit guarantees real-world performance
- Energy is predictable from current features

### ⚠️ CLAIM WITH CAVEATS
- "Models show perfect fit in simulation domain" (note: may not generalize)
- "Model C identifies when active healing beats H0" (caveat: only on majority class)
- "Models understand simulator behavior" (caveat: may reflect simulator quirks)

---

## Conclusion

These models provide **valuable research insights** into WSN simulation behavior but have **clear limitations** for deployment or generalization.

**The most critical limitations are:**
1. Energy prediction does not work (R² = -1.94)
2. Model C is binary, not multi-way selection
3. Results are validated only within S1-S11
4. Perfect fits may not transfer to real systems

**Always reference this document when making claims based on Agent 3 ML models.**

---

**Document Version**: 1.0  
**Date**: 2026-05-15  
**Applies To**: Agent 3 ML Workspace V2  
**Required Reading**: Before ANY publication or claim
