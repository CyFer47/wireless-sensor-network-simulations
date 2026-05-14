# PHASE 05 STAGE C - Safe and Unsafe Claims

## Safe claims
| Claim | Why it is safe |
|---|---|
| Recovery delay can be predicted within the tested simulation domain. | The safe Model A regression keeps R2 = 1.0000 after removing unsafe features. |
| Pairwise active-healing benefit over H0 can be identified within comparable tested scenarios. | The verified B1 classifier reports Accuracy = 1.0000 and F1 = 1.0000 on the saved test split. |
| Delivery and cluster recovery outcomes show deterministic behavior in this dataset. | Safe Models B1 and B3 remain at R2 = 1.0000 after leakage removal. |
| Leakage-free models reproduce the same conclusions for recovery delay, delivery ratio, and cluster recovery. | Safe performance does not drop after removing 56 unsafe features. |
| Energy consumption is not reliably predicted from pre-recovery features. | Safe Model B2 remains at negative R2. |

## Unsafe claims
| Claim | Why it is unsafe |
|---|---|
| The ML model globally chooses the best healing method among H0, H1, H2, H3, and H4. | The model only compares scenarios in the tested dataset and does not prove universal best choice. |
| The ML model reliably predicts energy consumption. | The safe Model B2 test R2 is -1.9995, which is worse than baseline. |
| The ML model generalizes to all real wireless sensor network deployments. | The evaluation was limited to the verified Phase 04 domain and seed-based split. |
| The current results prove universal superiority of the healing strategies outside the tested domain. | External validation has not been performed. |
| H1-H7 are the verified active healing strategies. | The verified dataset only contains H0, H1, H2, H3, and H4. |

## Report wording guidance
Use wording such as:
- "within the tested simulation domain"
- "for the verified Phase 04 dataset"
- "under the official S1-S11 split"
- "with limitations on generalization"

Avoid wording such as:
- "globally"
- "universally"
- "in all deployments"
- "best healing method in general"
