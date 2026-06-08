import time
import joblib
import psutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BASE_DIR / "models" / "selected_models"

models = [
    ("Model_A", MODEL_DIR / "model_A_best_recovery_delay.joblib"),
    ("Model_C", MODEL_DIR / "model_C_best_tradeoff_healing_selector.joblib"),
]

def mem():
    m = psutil.virtual_memory()
    return f"used={m.used/1024**2:.1f}MB available={m.available/1024**2:.1f}MB percent={m.percent}%"

print("Testing Model A and Model C loading")
print("=" * 70)

for name, path in models:
    print(f"\n{name}: {path}")
    print("Before:", mem())

    t0 = time.perf_counter()
    model = joblib.load(path)
    dt = time.perf_counter() - t0

    print("Loaded OK")
    print(f"Load time: {dt:.3f} seconds")
    print("After:", mem())

    del model

print("\nModel A and Model C loading test complete.")
