import pandas as pd
from pathlib import Path

# Directory containing XPT files
data_dir = Path(r"c:\Users\i1n23\OneDrive - University of Southampton\Desktop\New folder\NAHES_Dataset")

# Load all datasets
datasets = {}
file_names = ["BMX_D", "BPX_D", "DEMO_D", "HDL_D", "LEXABPI", "SLQ_D", "SMQ_D", "TCHOL_D", "TRIGLY_D"]

for name in file_names:
    file_path = data_dir / f"{name}.xpt"
    datasets[name] = pd.read_sas(str(file_path), format='xport')

print("="*80)
print("NHANES DATASET ANALYSIS")
print("="*80)

# Display column names for each dataset
print("\nColumn names in each dataset:\n")
for name, df in datasets.items():
    print(f"{name}:")
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
    print(f"  First few rows ID column: {df.iloc[:3, 0].tolist()}")
    print()

# Check if all datasets have a common ID column for merging
print("\nFirst column appears to be ID in each file:")
for name, df in datasets.items():
    print(f"  {name}: '{df.columns[0]}' - {df[df.columns[0]].nunique()} unique values")

# Merge strategy: use first column (participant ID) to merge all datasets
print("\n" + "="*80)
print("MERGING DATASETS")
print("="*80)

# Start with largest dataset (DEMO_D has most rows)
merged_df = datasets["DEMO_D"].copy()
print(f"\nStarting with DEMO_D: {merged_df.shape}")

# Merge other datasets using the ID column
merge_order = ["BMX_D", "BPX_D", "HDL_D", "LEXABPI", "SLQ_D", "SMQ_D", "TCHOL_D", "TRIGLY_D"]

for name in merge_order:
    df = datasets[name]
    id_col = df.columns[0]
    merged_df = merged_df.merge(df, on=id_col, how='left', suffixes=('', f'_{name}'))
    print(f"After merging {name}: {merged_df.shape}")
    
print(f"\nFinal merged dataset shape: {merged_df.shape}")
print(f"Total columns: {len(merged_df.columns)}")

# Display sample
print(f"\nFirst few rows of merged data:")
print(merged_df.head())

# Save the merged dataset
output_path = data_dir / "NHANES_merged.csv"
merged_df.to_csv(output_path, index=False)
print(f"\n✓ Merged dataset saved to: {output_path}")

# Display missing values summary
print(f"\nMissing values summary:")
missing_pct = (merged_df.isnull().sum() / len(merged_df) * 100).sort_values(ascending=False)
print(missing_pct.head(20))

# Save summary to file
summary_path = data_dir / "NHANES_merge_summary.txt"
with open(summary_path, 'w') as f:
    f.write("NHANES CAUSAL MODELS DATASET - MERGE SUMMARY\n")
    f.write("="*80 + "\n\n")
    f.write(f"Final merged dataset shape: {merged_df.shape}\n")
    f.write(f"Rows: {merged_df.shape[0]}\n")
    f.write(f"Columns: {merged_df.shape[1]}\n\n")
    f.write("All columns in merged dataset:\n")
    for i, col in enumerate(merged_df.columns, 1):
        f.write(f"  {i}. {col}\n")
    f.write("\n" + "="*80 + "\n")
    f.write("Missing values (top 20):\n")
    f.write(missing_pct.head(20).to_string())

print(f"✓ Summary saved to: {summary_path}")
