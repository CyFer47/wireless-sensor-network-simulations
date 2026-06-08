import json
import time
import csv
from pathlib import Path

import joblib
import pandas as pd
import psutil

BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_DIR = BASE_DIR / "models" / "selected_models"
INFO_DIR = BASE_DIR / "models" / "model_info"
SAMPLE_DIR = BASE_DIR / "models" / "sample_inputs"
OUT_DIR = BASE_DIR / "ml_results"
OUT_DIR.mkdir(exist_ok=True)

TASKS = [
    {
        "name": "Model_A",
        "model_path": MODEL_DIR / "model_A_best_recovery_delay.joblib",
        "info_path": INFO_DIR / "model_A_best_model_info.json",
        "sample_path": SAMPLE_DIR / "sample_model_A_input.csv",
    },
    {
        "name": "Model_B",
        "model_path": MODEL_DIR / "model_B_best_energy_outcomes.joblib",
        "info_path": INFO_DIR / "model_B_best_model_info.json",
        "sample_path": SAMPLE_DIR / "sample_model_B_input.csv",
    },
    {
        "name": "Model_C",
        "model_path": MODEL_DIR / "model_C_best_tradeoff_healing_selector.joblib",
        "info_path": INFO_DIR / "model_C_best_model_info.json",
        "sample_path": SAMPLE_DIR / "sample_model_C_input.csv",
    },
]


def mem_snapshot():
    m = psutil.virtual_memory()
    return {
        "used_mb": m.used / 1024**2,
        "available_mb": m.available / 1024**2,
        "percent": m.percent,
    }


def load_features(info_path):
    with open(info_path, "r") as f:
        info = json.load(f)

    features = info.get("features")

    if features is None:
        raise KeyError(f"No 'features' key found in {info_path}")

    return features, info


def benchmark_task(task):
    name = task["name"]
    model_path = task["model_path"]
    info_path = task["info_path"]
    sample_path = task["sample_path"]

    print("=" * 90)
    print(f"Benchmarking {name}")
    print("=" * 90)

    if not model_path.exists():
        raise FileNotFoundError(f"Missing model file: {model_path}")

    if not info_path.exists():
        raise FileNotFoundError(f"Missing info file: {info_path}")

    if not sample_path.exists():
        raise FileNotFoundError(
            f"Missing sample input CSV: {sample_path}\n"
            f"Copy sample input files before running inference benchmark."
        )

    features, info = load_features(info_path)

    sample_df = pd.read_csv(sample_path)

    missing_features = [c for c in features if c not in sample_df.columns]

    if missing_features:
        raise ValueError(
            f"{name}: sample CSV is missing required feature columns:\n"
            f"{missing_features}"
        )

    X = sample_df[features].copy()

    before_load = mem_snapshot()
    t0 = time.perf_counter()
    model = joblib.load(model_path)
    load_time = time.perf_counter() - t0
    after_load = mem_snapshot()

    print(f"Loaded model in {load_time:.3f} seconds")
    print(f"Sample rows: {len(X)}")

    # Warm-up prediction
    _ = model.predict(X.head(1))

    # Single-row latency
    single_times = []
    for _ in range(30):
        row = X.sample(1, random_state=None)
        t1 = time.perf_counter()
        _ = model.predict(row)
        single_times.append(time.perf_counter() - t1)

    # Batch prediction latency
    t2 = time.perf_counter()
    preds = model.predict(X)
    batch_time = time.perf_counter() - t2

    after_predict = mem_snapshot()

    avg_single_ms = sum(single_times) / len(single_times) * 1000
    min_single_ms = min(single_times) * 1000
    max_single_ms = max(single_times) * 1000
    per_row_batch_ms = (batch_time / len(X)) * 1000

    print(f"Average single-row prediction: {avg_single_ms:.3f} ms")
    print(f"Batch prediction time: {batch_time:.3f} s")
    print(f"Batch per-row time: {per_row_batch_ms:.3f} ms")

    pred_preview_path = OUT_DIR / f"{name.lower()}_prediction_preview.csv"

    preview_df = sample_df.head(min(20, len(sample_df))).copy()
    preview_preds = model.predict(X.head(len(preview_df)))

    if name == "Model_B":
        # Multi-output regression
        pred_df = pd.DataFrame(
            preview_preds,
            columns=["pred_consumed_j", "pred_avg_res_j", "pred_low_nodes"]
        )
        preview_out = pd.concat([preview_df.reset_index(drop=True), pred_df], axis=1)
    else:
        preview_out = preview_df.copy()
        preview_out["prediction"] = preview_preds

    preview_out.to_csv(pred_preview_path, index=False)

    result = {
        "model": name,
        "model_file_mb": round(model_path.stat().st_size / 1024**2, 3),
        "sample_rows": len(X),
        "load_time_s": round(load_time, 6),
        "avg_single_prediction_ms": round(avg_single_ms, 6),
        "min_single_prediction_ms": round(min_single_ms, 6),
        "max_single_prediction_ms": round(max_single_ms, 6),
        "batch_prediction_time_s": round(batch_time, 6),
        "batch_per_row_ms": round(per_row_batch_ms, 6),
        "ram_used_before_load_mb": round(before_load["used_mb"], 3),
        "ram_used_after_load_mb": round(after_load["used_mb"], 3),
        "ram_used_after_predict_mb": round(after_predict["used_mb"], 3),
        "status": "ok",
        "prediction_preview_csv": str(pred_preview_path),
    }

    return result


def main():
    results = []

    for task in TASKS:
        try:
            result = benchmark_task(task)
            results.append(result)
        except Exception as e:
            print(f"FAILED: {task['name']}")
            print(type(e).__name__, str(e))
            results.append({
                "model": task["name"],
                "status": f"failed: {type(e).__name__}: {e}",
            })

    out_csv = OUT_DIR / "rpi_ml_inference_benchmark.csv"

    all_keys = sorted(set().union(*[r.keys() for r in results]))

    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        writer.writerows(results)

    out_txt = OUT_DIR / "rpi_ml_inference_benchmark_summary.txt"

    with open(out_txt, "w") as f:
        f.write("Raspberry Pi ML Inference Benchmark Summary\n")
        f.write("==========================================\n\n")
        for r in results:
            f.write(json.dumps(r, indent=2))
            f.write("\n\n")

    print()
    print("=" * 90)
    print("Benchmark complete.")
    print("CSV:", out_csv)
    print("Summary:", out_txt)


if __name__ == "__main__":
    main()
