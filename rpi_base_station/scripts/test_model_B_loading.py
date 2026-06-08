import time
import joblib
import psutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "selected_models" / "model_B_best_energy_outcomes.joblib"

def mem():
    m = psutil.virtual_memory()
    return {
        "used_mb": m.used / 1024**2,
        "available_mb": m.available / 1024**2,
        "percent": m.percent
    }

print("Testing Model B loading")
print("=" * 80)
print("Model path:", MODEL_PATH)

if not MODEL_PATH.exists():
    raise FileNotFoundError(MODEL_PATH)

print(f"File size: {MODEL_PATH.stat().st_size / 1024**2:.2f} MB")

before = mem()
print(f"Before: used={before['used_mb']:.1f}MB available={before['available_mb']:.1f}MB percent={before['percent']}%")

t0 = time.perf_counter()
model = joblib.load(MODEL_PATH)
dt = time.perf_counter() - t0

after = mem()
print("Loaded OK")
print(f"Load time: {dt:.3f} seconds")
print(f"After: used={after['used_mb']:.1f}MB available={after['available_mb']:.1f}MB percent={after['percent']}%")

print()
print("Model B is currently loaded in RAM.")
input("Press Enter to release Model B and exit...")
