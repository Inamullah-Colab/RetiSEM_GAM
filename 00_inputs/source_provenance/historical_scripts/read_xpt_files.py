import pyreadstat
import pandas as pd
import os

# Directory containing XPT files
data_dir = r"c:\Users\i1n23\OneDrive - University of Southampton\Desktop\New folder\NAHES_Dataset"

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

# Read and display info about each file
for file in xpt_files:
    file_path = os.path.join(data_dir, file)
    try:
        df, meta = pyreadstat.read_sas7bdat(file_path)
        print(f"\n{'='*60}")
        print(f"File: {file}")
        print(f"{'='*60}")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns[:10])}")
        print(f"First few rows:")
        print(df.head(2))
    except Exception as e:
        print(f"Error reading {file}: {e}")
