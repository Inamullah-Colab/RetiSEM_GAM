from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path('NAHES_Dataset')
SRC = DATA_DIR / 'NHANES_merged_cvd_extended.csv'
MAP1 = DATA_DIR / 'nhanes_cad_only_variable_map.csv'
MAP2 = DATA_DIR / 'nhanes_cvd_extension_variable_map.csv'
OUT = DATA_DIR / 'NHANES_cvd_cad_master_selected.csv'
SUM = DATA_DIR / 'NHANES_cvd_cad_master_selected_summary.txt'


def safe_mean(df, cols):
    use = [c for c in cols if c in df.columns]
    if not use:
        return pd.Series(np.nan, index=df.index)
    return df[use].mean(axis=1, skipna=True)


def recode_missing_codes(s):
    return s.replace({7: np.nan, 9: np.nan, 77: np.nan, 99: np.nan, 777: np.nan, 999: np.nan})


def main():
    df = pd.read_csv(SRC)
    m1 = pd.read_csv(MAP1)
    m2 = pd.read_csv(MAP2)

    wanted = set(m1['nhanes_code'].tolist()) | set(m2['nhanes_code'].tolist())
    keep = ['SEQN'] + sorted([c for c in wanted if c in df.columns and c != 'SEQN'])

    out = df[keep].copy()

    # Derived features
    out['SBP_mean'] = safe_mean(df, ['BPXSY1','BPXSY2','BPXSY3','BPXSY4'])
    out['DBP_mean'] = safe_mean(df, ['BPXDI1','BPXDI2','BPXDI3','BPXDI4'])
    out['PulsePressure_mean'] = out['SBP_mean'] - out['DBP_mean']
    out['MAP_mean'] = out['DBP_mean'] + out['PulsePressure_mean'] / 3.0

    if {'LBXTC','LBDHDD'}.issubset(df.columns):
        out['NonHDL_C'] = df['LBXTC'] - df['LBDHDD']
    if {'BMXWAIST','BMXHT'}.issubset(df.columns):
        out['WaistHeightRatio'] = df['BMXWAIST'] / df['BMXHT']

    if {'MCQ160C','MCQ160E'}.issubset(out.columns):
        out['MCQ160C'] = recode_missing_codes(out['MCQ160C'])
        out['MCQ160E'] = recode_missing_codes(out['MCQ160E'])
        out['CAD_any'] = np.where((out['MCQ160C'] == 1) | (out['MCQ160E'] == 1), 1,
                           np.where((out['MCQ160C'].isna()) & (out['MCQ160E'].isna()), np.nan, 0))

    out.to_csv(OUT, index=False)

    lines = []
    lines.append('NHANES CVD+CAD master selected dataset summary')
    lines.append('='*68)
    lines.append(f'Source: {SRC.name}')
    lines.append(f'Output: {OUT.name}')
    lines.append(f'Rows: {len(out):,}')
    lines.append(f'Columns: {len(out.columns)}')
    lines.append('')

    core_check = ['MCQ160C','MCQ160E','DIQ010','LBXGLU','LBXGH','LBXCRP','LBXSCR','URXUMA','URXUCR','BPQ020','BPQ050A','BPQ080','LEXLABPI','LEXRABPI']
    lines.append('Core variable availability:')
    for c in core_check:
        lines.append(f'- {c}: {"present" if c in out.columns else "missing"}')

    if 'CAD_any' in out.columns:
        vc = out['CAD_any'].value_counts(dropna=False)
        lines.append('')
        lines.append('CAD_any distribution:')
        for k, v in vc.items():
            lines.append(f'- {k}: {int(v)}')

    SUM.write_text('\n'.join(lines), encoding='utf-8')
    print('Saved:', OUT)
    print('Saved:', SUM)
    print('Shape:', out.shape)


if __name__ == '__main__':
    main()
