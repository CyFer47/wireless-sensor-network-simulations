from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

required_files = [
    BASE_DIR / "models" / "selected_models" / "model_A_best_recovery_delay.joblib",
    BASE_DIR / "models" / "selected_models" / "model_B_best_energy_outcomes.joblib",
    BASE_DIR / "models" / "selected_models" / "model_C_best_tradeoff_healing_selector.joblib",
    BASE_DIR / "models" / "model_info" / "model_A_best_model_info.json",
    BASE_DIR / "models" / "model_info" / "model_B_best_model_info.json",
    BASE_DIR / "models" / "model_info" / "model_C_best_model_info.json",
]

print("Checking Raspberry Pi ML deployment files")
print("=" * 80)

all_ok = True

for path in required_files:
    rel = path.relative_to(BASE_DIR)
    if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"OK      {rel}  ({size_mb:.2f} MB)")
    else:
        print(f"MISSING {rel}")
        all_ok = False

print("=" * 80)

if all_ok:
    print("All required ML model files are present.")
else:
    print("Some files are missing.")
