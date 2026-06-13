from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path('NAHES_Dataset')
IN_PATH = DATA_DIR / 'NHANES_cvd_extended_with_macular_full_matched.csv'
OUT_PATH = DATA_DIR / 'NHANES_with_1000G_reference_proxy.csv'
OUT_MAP = DATA_DIR / 'reference_1000g_proxy_mapping.csv'
OUT_SUM = DATA_DIR / 'REFERENCE_1000G_PROXY_ASSUMPTIONS.txt'

# NHANES RIDRETH1 to 1000G superpopulation proxy weights
# SUPERPOPS: AFR, AMR, EAS, EUR, SAS
# NOTE: These are heuristic proxies, not participant genotypes.
MAPPING = {
    1: {'label': 'Mexican American',   'AFR': 0.05, 'AMR': 0.85, 'EAS': 0.00, 'EUR': 0.10, 'SAS': 0.00},
    2: {'label': 'Other Hispanic',     'AFR': 0.10, 'AMR': 0.50, 'EAS': 0.05, 'EUR': 0.35, 'SAS': 0.00},
    3: {'label': 'Non-Hispanic White', 'AFR': 0.03, 'AMR': 0.05, 'EAS': 0.00, 'EUR': 0.90, 'SAS': 0.02},
    4: {'label': 'Non-Hispanic Black', 'AFR': 0.90, 'AMR': 0.02, 'EAS': 0.00, 'EUR': 0.08, 'SAS': 0.00},
    5: {'label': 'Other/Multi',        'AFR': 0.10, 'AMR': 0.10, 'EAS': 0.35, 'EUR': 0.20, 'SAS': 0.25},
}


def entropy(p):
    p = np.array(p, dtype=float)
    p = p[p > 0]
    if len(p) == 0:
        return np.nan
    return float(-(p * np.log(p)).sum())


def main():
    df = pd.read_csv(IN_PATH)

    if 'RIDRETH1' not in df.columns:
        raise ValueError('RIDRETH1 not found; cannot build demographic proxy mapping.')

    r = pd.to_numeric(df['RIDRETH1'], errors='coerce')

    # Initialize proxy columns
    for c in ['GREF_AFR', 'GREF_AMR', 'GREF_EAS', 'GREF_EUR', 'GREF_SAS']:
        df[c] = np.nan
    df['GREF_LABEL'] = 'Unknown'

    for code, vals in MAPPING.items():
        mask = (r == code)
        df.loc[mask, 'GREF_AFR'] = vals['AFR']
        df.loc[mask, 'GREF_AMR'] = vals['AMR']
        df.loc[mask, 'GREF_EAS'] = vals['EAS']
        df.loc[mask, 'GREF_EUR'] = vals['EUR']
        df.loc[mask, 'GREF_SAS'] = vals['SAS']
        df.loc[mask, 'GREF_LABEL'] = vals['label']

    # Missing categories fallback: uniform weak prior
    miss = df['GREF_AFR'].isna()
    if miss.any():
        df.loc[miss, ['GREF_AFR', 'GREF_AMR', 'GREF_EAS', 'GREF_EUR', 'GREF_SAS']] = 0.2
        df.loc[miss, 'GREF_LABEL'] = 'Unknown_uniform'

    # Derived descriptors
    probs = df[['GREF_AFR', 'GREF_AMR', 'GREF_EAS', 'GREF_EUR', 'GREF_SAS']].values
    df['GREF_entropy'] = [entropy(p) for p in probs]
    df['GREF_major_superpop'] = df[['GREF_AFR', 'GREF_AMR', 'GREF_EAS', 'GREF_EUR', 'GREF_SAS']].idxmax(axis=1).str.replace('GREF_', '', regex=False)

    df.to_csv(OUT_PATH, index=False)

    map_rows = []
    for code, vals in MAPPING.items():
        map_rows.append({
            'RIDRETH1_code': code,
            'NHANES_label': vals['label'],
            'GREF_AFR': vals['AFR'],
            'GREF_AMR': vals['AMR'],
            'GREF_EAS': vals['EAS'],
            'GREF_EUR': vals['EUR'],
            'GREF_SAS': vals['SAS'],
        })
    pd.DataFrame(map_rows).to_csv(OUT_MAP, index=False)

    # Quick diagnostics
    diag = df[['GREF_AFR', 'GREF_AMR', 'GREF_EAS', 'GREF_EUR', 'GREF_SAS']].mean().to_dict()
    n = len(df)

    lines = []
    lines.append('1000G REFERENCE PROXY MERGE - ASSUMPTIONS AND LIMITATIONS')
    lines.append('=' * 68)
    lines.append('Purpose: add cross-population reference proxy features when participant-level genetics are unavailable.')
    lines.append('')
    lines.append('IMPORTANT: This is NOT a true genetic merge and cannot replace individual SNP/PRS data.')
    lines.append('Proxy features are demographic-to-superpopulation mappings only.')
    lines.append('')
    lines.append(f'Input rows: {n}')
    lines.append(f'Output file: {OUT_PATH.name}')
    lines.append(f'Mapping file: {OUT_MAP.name}')
    lines.append('')
    lines.append('Mean proxy superpopulation composition (dataset-level):')
    for k, v in diag.items():
        lines.append(f'- {k}: {v:.4f}')
    lines.append('')
    lines.append('Recommended use:')
    lines.append('- Include GREF_* variables only as sensitivity covariates.')
    lines.append('- Do not interpret GREF_* as participant genotypes.')
    lines.append('- For causal genetic inference, use NHANES genotype data + PRS/MR pipelines.')

    OUT_SUM.write_text('\n'.join(lines), encoding='utf-8')

    print('Saved:', OUT_PATH)
    print('Saved:', OUT_MAP)
    print('Saved:', OUT_SUM)


if __name__ == '__main__':
    main()
