import os
import pandas as pd
from pathlib import Path

# Directory containing XPT files
data_dir = Path(r"c:\Users\i1n23\OneDrive - University of Southampton\Desktop\New folder\NAHES_Dataset")

# List of XPT files
xpt_files = [
    "BMX_D.xpt",
    "BPX_D.xpt", 
    "DEMO_D.xpt",
    "HDL_D.xpt",
    "LEXABPI.xpt",
    "SLQ_D.xpt",
    "SMQ_D.xpt",
    "TCHOL_D.xpt",
    "TRIGLY_D.xpt"
]

print("Attempting to read NHANES XPT files...\n")

# Try different methods
dfs = {}
for file in xpt_files:
    file_path = data_dir / file
    print(f"Reading {file}...")
    
    try:
        # Method 1: Try with xport library
        import xport.v5
        with xport.v5.Reader(str(file_path)) as reader:
            df = reader.read()
            dfs[file.replace('.xpt', '')] = df
            print(f"  ✓ Success with xport! Shape: {df.shape}")
            print(f"  Columns: {list(df.columns)[:5]}...")
    except Exception as e1:
        print(f"  ✗ xport failed: {e1}")
        try:
            # Method 2: Try sas7bdat
            from sas7bdat import SAS7BDAT
            with SAS7BDAT(str(file_path)) as f:
                df = pd.DataFrame.from_records(f.readlines())
                dfs[file.replace('.xpt', '')] = df
                print(f"  ✓ Success with sas7bdat! Shape: {df.shape}")
        except Exception as e2:
            print(f"  ✗ sas7bdat failed: {e2}")
            try:
                # Method 3: Try pandas read_sas with encoding
                df = pd.read_sas(str(file_path), format='xport')
                dfs[file.replace('.xpt', '')] = df
                print(f"  ✓ Success with pd.read_sas! Shape: {df.shape}")
            except Exception as e3:
                print(f"  ✗ pd.read_sas failed: {e3}")

print(f"\n\nSuccessfully read {len(dfs)} files:")
for name, df in dfs.items():
    print(f"  {name}: {df.shape}")
