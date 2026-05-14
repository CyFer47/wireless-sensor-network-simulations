"""
Model B: Run Outcomes Regression
Predicts multiple run outcomes using network and failure features

Target variables:
- final_agg_delivery_ratio
- final_consumed_j
- final_recovered_clusters

Models trained:
- Decision Tree Regressor
- Random Forest Regressor
- Gradient Boosting Regressor

Metrics:
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- R² (Coefficient of Determination)

Note: Energy prediction (final_consumed_j) may have poor R² - reported without overclaiming
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# Add common preprocessing to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_preprocessing import (
    load_data_for_model, get_train_val_test_split, prepare_features_and_target,
    standardize_features, validate_split
)


def train_single_target(X_train_scaled, X_val_scaled, X_test_scaled, 
                       y_train, y_val, y_test, target_name):
    """Train all models for a single target variable"""
    
    print(f"\n--- Training for target: {target_name} ---")
    
    models = {
        'Decision Tree': DecisionTreeRegressor(random_state=42, max_depth=10),
        'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42, max_depth=15),
        'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42, max_depth=5)
    }
    
    results = {}
    
    for model_name, model in models.items():
        print(f"  Training {model_name}...")
        
        # Train
        model.fit(X_train_scaled, y_train)
        
        # Predict
        y_train_pred = model.predict(X_train_scaled)
        y_val_pred = model.predict(X_val_scaled)
        y_test_pred = model.predict(X_test_scaled)
        
        # Calculate metrics
        train_mae = mean_absolute_error(y_train, y_train_pred)
        train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
        train_r2 = r2_score(y_train, y_train_pred)
        
        val_mae = mean_absolute_error(y_val, y_val_pred)
        val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
        val_r2 = r2_score(y_val, y_val_pred)
        
        test_mae = mean_absolute_error(y_test, y_test_pred)
        test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
        test_r2 = r2_score(y_test, y_test_pred)
        
        results[model_name] = {
            'train': {'MAE': train_mae, 'RMSE': train_rmse, 'R2': train_r2},
            'validation': {'MAE': val_mae, 'RMSE': val_rmse, 'R2': val_r2},
            'test': {'MAE': test_mae, 'RMSE': test_rmse, 'R2': test_r2},
            'model': model
        }
        
        print(f"    Train   | MAE: {train_mae:.4f}, RMSE: {train_rmse:.4f}, R²: {train_r2:.4f}")
        print(f"    Val     | MAE: {val_mae:.4f}, RMSE: {val_rmse:.4f}, R²: {val_r2:.4f}")
        print(f"    Test    | MAE: {test_mae:.4f}, RMSE: {test_rmse:.4f}, R²: {test_r2:.4f}")
    
    return results


def train_model_b():
    """Train all Model B variants and return results"""
    
    print("\n" + "="*70)
    print("MODEL B: RUN OUTCOMES REGRESSION")
    print("="*70)
    
    # Configuration
    workspace_root = r"C:\Users\MSI\Desktop\2025 UH\Final Year Project\Machine learning model"
    data_file = os.path.join(workspace_root, "01_DATA_INPUT", "DATA", 
                             "01_official_ml_dataset", "ml_run_outcomes.csv")
    target_cols = [
        'final_agg_delivery_ratio',
        'final_consumed_j',
        'final_recovered_clusters'
    ]
    
    print(f"\nDataset: {data_file}")
    print(f"Targets: {', '.join(target_cols)}")
    
    # ============ STEP 1: Load and validate data ============
    print("\n--- Step 1: Loading data ---")
    df = pd.read_csv(data_file)
    print(f"Data shape: {df.shape}")
    
    # Validate split
    validate_split(df)
    
    # Check that all targets exist
    for target_col in target_cols:
        if target_col not in df.columns:
            raise ValueError(f"Target column {target_col} not found!")
    
    # ============ STEP 2: Split data (official split) ============
    print("\n--- Step 2: Splitting data (official split) ---")
    train_df, val_df, test_df = get_train_val_test_split(df, split_col='split')
    
    # ============ STEP 3: Prepare a single feature set (shared by all targets) ============
    print("\n--- Step 3: Preparing features ---")
    
    # Use first target to get features (same features for all)
    X_train, y_train_temp = prepare_features_and_target(train_df, target_cols[0], model_name="Model B (features)")
    X_val, y_val_temp = prepare_features_and_target(val_df, target_cols[0], model_name="Model B (features)")
    X_test, y_test_temp = prepare_features_and_target(test_df, target_cols[0], model_name="Model B (features)")
    
    print(f"Train: {X_train.shape[0]} samples, {X_train.shape[1]} features")
    print(f"Validation: {X_val.shape[0]} samples")
    print(f"Test: {X_test.shape[0]} samples")
    
    # ============ STEP 4: Feature standardization ============
    print("\n--- Step 4: Standardizing features ---")
    X_train_scaled, X_val_scaled, X_test_scaled, scaler = standardize_features(
        X_train, X_val, X_test, scaler_type='standard'
    )
    
    # ============ STEP 5: Train models for each target ============
    print("\n--- Step 5: Training models for each target ---")
    
    all_results = {}
    best_models = {}
    
    for target_col in target_cols:
        print(f"\n=== Target: {target_col} ===")
        
        # Get targets
        y_train = train_df[target_col].values
        y_val = val_df[target_col].values
        y_test = test_df[target_col].values
        
        # Train models
        target_results = train_single_target(
            X_train_scaled, X_val_scaled, X_test_scaled,
            y_train, y_val, y_test, target_col
        )
        
        # Select best model
        best_model_name = min(target_results, key=lambda x: target_results[x]['validation']['RMSE'])
        print(f"  Best model: {best_model_name}")
        print(f"  Test RMSE: {target_results[best_model_name]['test']['RMSE']:.4f}")
        
        all_results[target_col] = target_results
        best_models[target_col] = (best_model_name, target_results[best_model_name]['model'])
    
    # ============ STEP 6: Save results ============
    print("\n--- Step 6: Saving results ---")
    
    # Prepare output
    output_results = {}
    for target_col, models_dict in all_results.items():
        output_results[target_col] = {}
        for model_name, model_data in models_dict.items():
            output_results[target_col][model_name] = {
                'train_MAE': float(model_data['train']['MAE']),
                'train_RMSE': float(model_data['train']['RMSE']),
                'train_R2': float(model_data['train']['R2']),
                'val_MAE': float(model_data['validation']['MAE']),
                'val_RMSE': float(model_data['validation']['RMSE']),
                'val_R2': float(model_data['validation']['R2']),
                'test_MAE': float(model_data['test']['MAE']),
                'test_RMSE': float(model_data['test']['RMSE']),
                'test_R2': float(model_data['test']['R2']),
            }
    
    # Save to JSON
    results_file = os.path.join(workspace_root, "06_RESULTS", "MODEL_B_RESULTS.json")
    with open(results_file, 'w') as f:
        json.dump(output_results, f, indent=2)
    print(f"Results saved to {results_file}")
    
    # Save best models
    import joblib
    for target_col, (model_name, model) in best_models.items():
        safe_name = target_col.replace('_', '-')
        model_file = os.path.join(workspace_root, "05_MODELS", f"model_b_{safe_name}_best.joblib")
        joblib.dump(model, model_file)
        print(f"Saved {target_col} best model to {model_file}")
    
    print("\n" + "="*70)
    print("MODEL B TRAINING COMPLETE")
    print("="*70)
    
    return {
        'results': output_results,
        'best_models': {col: name for col, (name, _) in best_models.items()},
        'targets': target_cols
    }


if __name__ == '__main__':
    try:
        result = train_model_b()
        print("\nSUCCESS: Model B training completed successfully")
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
