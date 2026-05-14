"""
Model C: Pairwise Active-Healing vs H0 Classifier

IMPORTANT SCOPE:
Model C is NOT a full 5-way best-healing selector.
Model C is specifically: Active healing vs H0 (baseline) only.

Dataset: DATA/02_derived_labels/ml_best_healing_labels_derived_from_db_v1.csv

Target: active_healing_beats_H0 (binary classification)
  0 = H0 is better/equal
  1 = Active healing is better

Models:
- Decision Tree Classifier
- Random Forest Classifier
- Gradient Boosting Classifier

Metrics:
- Accuracy
- Precision
- Recall
- F1-score
- Balanced Accuracy
- Confusion Matrix
- Class Distribution
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             balanced_accuracy_score, confusion_matrix, classification_report)
import warnings
warnings.filterwarnings('ignore')

# Add common preprocessing to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_preprocessing import (
    load_data_for_model, get_train_val_test_split, prepare_features_and_target,
    standardize_features, validate_split, print_class_distribution
)


def train_model_c():
    """Train Model C pairwise classifier and return results"""
    
    print("\n" + "="*70)
    print("MODEL C: PAIRWISE ACTIVE-HEALING VS H0 CLASSIFIER")
    print("="*70)
    print("\n*** IMPORTANT: This is a PAIRWISE classifier (Active vs H0 only) ***")
    print("*** This is NOT a full 5-way best-healing selector ***\n")
    
    # Configuration
    workspace_root = r"C:\Users\MSI\Desktop\2025 UH\Final Year Project\Machine learning model"
    data_file = os.path.join(workspace_root, "01_DATA_INPUT", "DATA", 
                             "02_derived_labels", "model_c_pairwise_dataset.csv")
    target_col = "active_healing_beats_H0"
    
    print(f"Dataset: {data_file}")
    print(f"Target: {target_col}")
    
    # ============ STEP 1: Check if file exists ============
    print("\n--- Step 1: Checking for derived labels file ---")
    if not os.path.exists(data_file):
        print(f"ERROR: Derived labels file not found!")
        print(f"Expected: {data_file}")
        return {'error': 'Derived labels file missing', 'success': False}
    
    # ============ STEP 2: Load and validate data ============
    print("\n--- Step 2: Loading data ---")
    df = pd.read_csv(data_file)
    print(f"Data shape: {df.shape}")
    
    # Check if target exists
    if target_col not in df.columns:
        print(f"ERROR: Target column '{target_col}' not found in data!")
        print(f"Available columns: {list(df.columns)}")
        return {'error': f'Target column {target_col} not found', 'success': False}
    
    # Check split column
    if 'split' in df.columns:
        validate_split(df)
    else:
        print("WARNING: No 'split' column found - using all data without official split")
    
    # ============ STEP 3: Analyze class distribution ============
    print("\n--- Step 3: Analyzing class distribution ---")
    print_class_distribution(df[target_col], "in full dataset")
    
    # ============ STEP 4: Split data ============
    print("\n--- Step 4: Splitting data ---")
    if 'split' in df.columns:
        train_df, val_df, test_df = get_train_val_test_split(df, split_col='split')
    else:
        # If no split column, use all data
        print("Using all data (no official split available)")
        train_df = df.copy()
        val_df = df.copy()
        test_df = df.copy()
    
    # ============ STEP 5: Prepare features and target ============
    print("\n--- Step 5: Preparing features and target ---")
    
    X_train, y_train = prepare_features_and_target(train_df, target_col, model_name="Model C")
    X_val, y_val = prepare_features_and_target(val_df, target_col, model_name="Model C")
    X_test, y_test = prepare_features_and_target(test_df, target_col, model_name="Model C")
    
    print(f"Train: {X_train.shape[0]} samples, {X_train.shape[1]} features")
    print(f"Validation: {X_val.shape[0]} samples")
    print(f"Test: {X_test.shape[0]} samples")
    
    # Check test set class distribution
    print("\nTest set class distribution:")
    test_counts = pd.Series(y_test).value_counts().sort_index()
    for label, count in test_counts.items():
        print(f"  Class {label}: {count} samples")
    
    # Warn if test set is single-class
    if len(test_counts) == 1:
        print("  WARNING: Test set is SINGLE-CLASS! Classification metrics may be misleading.")
    
    # ============ STEP 6: Feature standardization ============
    print("\n--- Step 6: Standardizing features ---")
    X_train_scaled, X_val_scaled, X_test_scaled, scaler = standardize_features(
        X_train, X_val, X_test, scaler_type='standard'
    )
    
    # ============ STEP 7: Train models ============
    print("\n--- Step 7: Training models ---")
    
    models = {
        'Decision Tree': DecisionTreeClassifier(random_state=42, max_depth=10),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42, max_depth=15),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5)
    }
    
    results = {}
    
    for model_name, model in models.items():
        print(f"\nTraining {model_name}...")
        
        # Train
        model.fit(X_train_scaled, y_train)
        
        # Predict
        y_train_pred = model.predict(X_train_scaled)
        y_val_pred = model.predict(X_val_scaled)
        y_test_pred = model.predict(X_test_scaled)
        
        # Calculate metrics for train
        train_acc = accuracy_score(y_train, y_train_pred)
        train_prec = precision_score(y_train, y_train_pred, zero_division=0)
        train_rec = recall_score(y_train, y_train_pred, zero_division=0)
        train_f1 = f1_score(y_train, y_train_pred, zero_division=0)
        train_bal_acc = balanced_accuracy_score(y_train, y_train_pred)
        
        # Calculate metrics for validation
        val_acc = accuracy_score(y_val, y_val_pred)
        val_prec = precision_score(y_val, y_val_pred, zero_division=0)
        val_rec = recall_score(y_val, y_val_pred, zero_division=0)
        val_f1 = f1_score(y_val, y_val_pred, zero_division=0)
        val_bal_acc = balanced_accuracy_score(y_val, y_val_pred)
        
        # Calculate metrics for test
        test_acc = accuracy_score(y_test, y_test_pred)
        test_prec = precision_score(y_test, y_test_pred, zero_division=0)
        test_rec = recall_score(y_test, y_test_pred, zero_division=0)
        test_f1 = f1_score(y_test, y_test_pred, zero_division=0)
        test_bal_acc = balanced_accuracy_score(y_test, y_test_pred)
        
        # Confusion matrix
        test_cm = confusion_matrix(y_test, y_test_pred)
        
        # Store results
        results[model_name] = {
            'train': {
                'accuracy': train_acc, 'precision': train_prec, 'recall': train_rec,
                'f1': train_f1, 'balanced_accuracy': train_bal_acc
            },
            'validation': {
                'accuracy': val_acc, 'precision': val_prec, 'recall': val_rec,
                'f1': val_f1, 'balanced_accuracy': val_bal_acc
            },
            'test': {
                'accuracy': test_acc, 'precision': test_prec, 'recall': test_rec,
                'f1': test_f1, 'balanced_accuracy': test_bal_acc,
                'confusion_matrix': test_cm.tolist()
            },
            'model': model
        }
        
        # Print results
        print(f"  Train   | Acc: {train_acc:.4f}, Prec: {train_prec:.4f}, Rec: {train_rec:.4f}, F1: {train_f1:.4f}")
        print(f"  Val     | Acc: {val_acc:.4f}, Prec: {val_prec:.4f}, Rec: {val_rec:.4f}, F1: {val_f1:.4f}")
        print(f"  Test    | Acc: {test_acc:.4f}, Prec: {test_prec:.4f}, Rec: {test_rec:.4f}, F1: {test_f1:.4f}")
        print(f"  Confusion Matrix (Test): {test_cm.tolist()}")
    
    # ============ STEP 8: Select best model ============
    print("\n--- Step 8: Selecting best model ---")
    best_model_name = min(results, key=lambda x: -results[x]['validation']['f1'])
    print(f"Best model (highest validation F1): {best_model_name}")
    print(f"Test F1: {results[best_model_name]['test']['f1']:.4f}")
    
    # ============ STEP 9: Save results ============
    print("\n--- Step 9: Saving results ---")
    
    # Prepare output
    output_results = {}
    for model_name, model_data in results.items():
        output_results[model_name] = {
            'train_accuracy': float(model_data['train']['accuracy']),
            'train_precision': float(model_data['train']['precision']),
            'train_recall': float(model_data['train']['recall']),
            'train_f1': float(model_data['train']['f1']),
            'train_balanced_accuracy': float(model_data['train']['balanced_accuracy']),
            'val_accuracy': float(model_data['validation']['accuracy']),
            'val_precision': float(model_data['validation']['precision']),
            'val_recall': float(model_data['validation']['recall']),
            'val_f1': float(model_data['validation']['f1']),
            'val_balanced_accuracy': float(model_data['validation']['balanced_accuracy']),
            'test_accuracy': float(model_data['test']['accuracy']),
            'test_precision': float(model_data['test']['precision']),
            'test_recall': float(model_data['test']['recall']),
            'test_f1': float(model_data['test']['f1']),
            'test_balanced_accuracy': float(model_data['test']['balanced_accuracy']),
            'test_confusion_matrix': model_data['test']['confusion_matrix'],
        }
    
    # Save to JSON
    results_file = os.path.join(workspace_root, "06_RESULTS", "MODEL_C_RESULTS.json")
    with open(results_file, 'w') as f:
        json.dump(output_results, f, indent=2)
    print(f"Results saved to {results_file}")
    
    # Save best model
    best_model = results[best_model_name]['model']
    import joblib
    model_file = os.path.join(workspace_root, "05_MODELS", "model_c_pairwise_best.joblib")
    joblib.dump(best_model, model_file)
    print(f"Best model saved to {model_file}")
    
    print("\n" + "="*70)
    print("MODEL C TRAINING COMPLETE")
    print("="*70)
    
    return {
        'success': True,
        'best_model_name': best_model_name,
        'results': output_results,
        'test_metrics': results[best_model_name]['test'],
        'is_single_class_test': len(test_counts) == 1
    }


if __name__ == '__main__':
    try:
        result = train_model_c()
        if result.get('success'):
            print("\nSUCCESS: Model C training completed successfully")
        else:
            print(f"\nERROR: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
