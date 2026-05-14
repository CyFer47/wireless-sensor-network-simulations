"""
Model A: Recovery Time Regression
Predicts traffic_recovery_delay_s using network and failure configuration features

Models trained:
- Linear Regression
- Decision Tree Regressor
- Random Forest Regressor
- Gradient Boosting Regressor

Metrics:
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- R² (Coefficient of Determination)
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# Add common preprocessing to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_preprocessing import (
    load_data_for_model, get_train_val_test_split, prepare_features_and_target,
    standardize_features, validate_split, check_leakage
)


def train_model_a():
    """Train all Model A variants and return results"""
    
    print("\n" + "="*70)
    print("MODEL A: RECOVERY TIME REGRESSION")
    print("="*70)
    
    # Configuration
    workspace_root = r"C:\Users\MSI\Desktop\2025 UH\Final Year Project\Machine learning model"
    data_file = os.path.join(workspace_root, "01_DATA_INPUT", "DATA", 
                             "01_official_ml_dataset", "ml_recovery_time_regression.csv")
    target_col = "traffic_recovery_delay_s"
    
    print(f"\nDataset: {data_file}")
    print(f"Target: {target_col}")
    
    # ============ STEP 1: Load and validate data ============
    print("\n--- Step 1: Loading data ---")
    df = load_data_for_model(data_file, target_col, model_name="Model A")
    print(f"Data shape: {df.shape}")
    
    # Validate split
    validate_split(df)
    
    # ============ STEP 2: Split data (official split, not random) ============
    print("\n--- Step 2: Splitting data (official split) ---")
    train_df, val_df, test_df = get_train_val_test_split(df, split_col='split')
    
    # ============ STEP 3: Prepare features and target ============
    print("\n--- Step 3: Preparing features and target ---")
    
    X_train, y_train = prepare_features_and_target(train_df, target_col, model_name="Model A")
    X_val, y_val = prepare_features_and_target(val_df, target_col, model_name="Model A")
    X_test, y_test = prepare_features_and_target(test_df, target_col, model_name="Model A")
    
    print(f"Train: {X_train.shape[0]} samples, {X_train.shape[1]} features")
    print(f"Validation: {X_val.shape[0]} samples")
    print(f"Test: {X_test.shape[0]} samples")
    
    # ============ STEP 4: Feature standardization ============
    print("\n--- Step 4: Standardizing features ---")
    X_train_scaled, X_val_scaled, X_test_scaled, scaler = standardize_features(
        X_train, X_val, X_test, scaler_type='standard'
    )
    
    # ============ STEP 5: Train models ============
    print("\n--- Step 5: Training models ---")
    
    models = {
        'Linear Regression': LinearRegression(),
        'Decision Tree': DecisionTreeRegressor(random_state=42, max_depth=10),
        'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42, max_depth=15),
        'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42, max_depth=5)
    }
    
    results = {}
    
    for model_name, model in models.items():
        print(f"\nTraining {model_name}...")
        
        # Train on train set
        model.fit(X_train_scaled, y_train)
        
        # Predict on all sets
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
        
        # Store results
        results[model_name] = {
            'train': {'MAE': train_mae, 'RMSE': train_rmse, 'R2': train_r2},
            'validation': {'MAE': val_mae, 'RMSE': val_rmse, 'R2': val_r2},
            'test': {'MAE': test_mae, 'RMSE': test_rmse, 'R2': test_r2},
            'model': model
        }
        
        # Print results
        print(f"  Train   | MAE: {train_mae:.4f}, RMSE: {train_rmse:.4f}, R²: {train_r2:.4f}")
        print(f"  Val     | MAE: {val_mae:.4f}, RMSE: {val_rmse:.4f}, R²: {val_r2:.4f}")
        print(f"  Test    | MAE: {test_mae:.4f}, RMSE: {test_rmse:.4f}, R²: {test_r2:.4f}")
    
    # ============ STEP 6: Select best model ============
    print("\n--- Step 6: Selecting best model ---")
    best_model_name = min(results, key=lambda x: results[x]['validation']['RMSE'])
    print(f"Best model (lowest validation RMSE): {best_model_name}")
    print(f"Test RMSE: {results[best_model_name]['test']['RMSE']:.4f}")
    
    # ============ STEP 7: Save results ============
    print("\n--- Step 7: Saving results ---")
    
    # Prepare output
    output_results = {}
    for model_name, model_data in results.items():
        output_results[model_name] = {
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
    results_file = os.path.join(workspace_root, "06_RESULTS", "MODEL_A_RESULTS.json")
    with open(results_file, 'w') as f:
        json.dump(output_results, f, indent=2)
    print(f"Results saved to {results_file}")
    
    # Save best model
    best_model = results[best_model_name]['model']
    import joblib
    model_file = os.path.join(workspace_root, "05_MODELS", "model_a_recovery_time_best.joblib")
    joblib.dump(best_model, model_file)
    print(f"Best model saved to {model_file}")
    
    print("\n" + "="*70)
    print("MODEL A TRAINING COMPLETE")
    print("="*70)
    
    return {
        'best_model_name': best_model_name,
        'results': output_results,
        'test_metrics': results[best_model_name]['test']
    }


if __name__ == '__main__':
    try:
        result = train_model_a()
        print("\nSUCCESS: Model A training completed successfully")
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
