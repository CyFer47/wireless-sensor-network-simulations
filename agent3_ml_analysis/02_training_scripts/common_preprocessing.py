import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
import warnings
warnings.filterwarnings('ignore')

def load_data_for_model(filepath, target_col, model_name=''):
    df = pd.read_csv(filepath)
    return df

def check_leakage(df, target_col, model_name=''):
    forbidden = FORBIDDEN_FEATURES.copy()
    forbidden.discard(target_col)
    leaked_cols = forbidden & set(df.columns)
    if leaked_cols:
        print(f"WARNING: Potential data leakage in {model_name}!")
        print(f"Forbidden columns found: {leaked_cols}")
        return True
    return False

FORBIDDEN_FEATURES = {
    'run_id',
    'experiment_version',
    'map_signature',
    'split',
    'base_condition_key',
    'score_v1',
    'best_score_v1',
    'best_healing_id',
    'best_healing_id_derived',
    'candidate_is_best',
    'is_best_candidate',
    'is_best_candidate_derived',
    'active_healing_beats_H0',
    'traffic_recovery_delay_s',
    'final_agg_delivery_ratio',
    'final_consumed_j',
    'final_recovered_clusters'
}

def get_train_val_test_split(df, split_col='split'):
    if split_col not in df.columns:
        raise ValueError(f"Split column not found: {split_col}")
    train_df = df[df[split_col] == 'train'].copy()
    val_df = df[df[split_col] == 'validation'].copy()
    test_df = df[df[split_col] == 'test'].copy()
    print(f"Split sizes: train={len(train_df)}, validation={len(val_df)}, test={len(test_df)}")
    return train_df, val_df, test_df

def prepare_features_and_target(df, target_col, remove_na=True, model_name=''):
    if target_col not in df.columns:
        raise ValueError(f"Target column not found: {target_col}")
    
    # 1. Extract target variable y
    y = df[target_col].copy()
    
    # 2. Drop leakage columns and metadata columns from df
    forbidden_to_remove = FORBIDDEN_FEATURES.copy()
    forbidden_to_remove.discard(target_col)
    metadata_cols = {
        'split', 'run_id', 'experiment_version', 'map_signature', 'base_condition_key', 
        'candidate_id', 'healing_id', 'recovery_applied_delay_s', 'recovery_target_source',
        'recovery_start_s', 'recovery_applied_s', 'first_recovered_aggregate_s', 
        'traffic_recovery_delay_s', 'failure_injection_s'
    }
    cols_to_remove = (forbidden_to_remove | metadata_cols) & set(df.columns)
    
    if cols_to_remove:
        print(f"Removing {len(cols_to_remove)} leakage/metadata columns")
        
    # 3. Get remaining X features
    X = df.drop(columns=list(cols_to_remove | {target_col}))
    
    # 4 & 5. THEN check for NA values only in y and X (after removing leakage) and remove rows
    if remove_na:
        initial_size = len(df)
        na_mask = y.isna() | X.isna().any(axis=1)
        X = X[~na_mask].copy()
        y = y[~na_mask].copy()
        removed = initial_size - len(X)
        if removed > 0:
            print(f"Removed {removed} rows with NA values in features or target")
            
    # New step: Identify and encode categorical columns
    categorical_cols = X.select_dtypes(include=['object']).columns
    if not categorical_cols.empty:
        print(f"Encoding categorical columns: {list(categorical_cols)}")
        le = LabelEncoder()
        for col in categorical_cols:
            X[col] = le.fit_transform(X[col].astype(str))
            
    # 6. Return X and y
    print(f"Final features shape: {X.shape}")
    return X, y

def standardize_features(X_train, X_val, X_test, scaler_type='standard'):
    if scaler_type == 'standard':
        scaler = StandardScaler()
    else:
        scaler = MinMaxScaler()
    
    # Ensure inputs are handled correctly if they are DataFrames or arrays
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    return X_train_scaled, X_val_scaled, X_test_scaled, scaler

def print_class_distribution(y, dataset_name=''):
    print(f"Class distribution {dataset_name}:")
    print(y.value_counts().sort_index())

def validate_split(df):
    if 'split' not in df.columns:
        return False
    actual_split = df['split'].value_counts().to_dict()
    expected = {'train': 1012, 'validation': 68, 'test': 68}
    print("Expected vs Actual split:")
    for split_name, expected_count in expected.items():
        actual_count = actual_split.get(split_name, 0)
        match = "OK" if actual_count == expected_count else "MISMATCH"
        print(f"  {split_name}: {actual_count} [{match}]")
    return actual_split == expected
