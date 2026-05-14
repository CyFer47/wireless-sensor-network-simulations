"""
Prepare Model C dataset - Create pairwise active-healing vs H0 target
"""
import pandas as pd
import os

def create_model_c_dataset():
    """
    Create pairwise dataset: Active healing vs H0
    Returns 1 if best healing is active (not H0), 0 if best is H0
    """
    
    workspace_root = r"C:\Users\MSI\Desktop\2025 UH\Final Year Project\Machine learning model"
    data_path = os.path.join(workspace_root, "01_DATA_INPUT", "DATA", "02_derived_labels")
    
    # Load files
    candidates = pd.read_csv(os.path.join(data_path, "ml_healing_candidates_scored_from_db_v1.csv"))
    best_labels = pd.read_csv(os.path.join(data_path, "ml_best_healing_labels_derived_from_db_v1.csv"))
    
    # Load official split info - indexed by run_id
    split_file = os.path.join(workspace_root, "01_DATA_INPUT", "DATA", "01_official_ml_dataset", "dataset_split_manifest.csv")
    split_df = pd.read_csv(split_file)[['run_id', 'split']].drop_duplicates()
    
    # Create pairwise target: 1 if best healing is active (not H0)
    best_labels['active_healing_beats_H0'] = (best_labels['best_healing_id'] != 'H0').astype(int)
    
    # Merge candidates with pairwise target
    merged = candidates.merge(best_labels[['base_condition_key', 'best_healing_id', 'active_healing_beats_H0']], 
                              on='base_condition_key', how='left')
    
    # Add split information using run_id
    merged = merged.merge(split_df, on='run_id', how='left')
    
    print(f"Created pairwise dataset with {len(merged)} rows")
    print(f"Class distribution:")
    print(merged['active_healing_beats_H0'].value_counts())
    print()
    print(f"Split distribution:")
    print(merged['split'].value_counts())
    print()
    print(f"Columns: {list(merged.columns)}")
    
    # Save to temporary CSV
    output_file = os.path.join(data_path, "model_c_pairwise_dataset.csv")
    merged.to_csv(output_file, index=False)
    print(f"\nSaved to: {output_file}")
    
    return merged, output_file

if __name__ == '__main__':
    df, filepath = create_model_c_dataset()
