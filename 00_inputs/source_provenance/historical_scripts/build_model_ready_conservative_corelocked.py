from pathlib import Path
import numpy as np
import pandas as pd
from statsmodels.stats.outliers_influence import variance_inflation_factor

DATA_DIR = Path('NAHES_Dataset')
IN_PATH = DATA_DIR / 'NHANES_cvd_extended_with_macular_full_matched.csv'
OUT_DATA = DATA_DIR / 'NHANES_model_ready_conservative_corelocked.csv'
OUT_FEATS = DATA_DIR / 'selected_features_conservative_corelocked.csv'
OUT_SUM = DATA_DIR / 'MODEL_READY_CONSERVATIVE_CORELOCKED_SUMMARY.txt'
OUT_DROP = DATA_DIR / 'drop_log_conservative_corelocked.csv'

R_THRESH = 0.85
VIF_THRESH = 15.0

# Keep these no matter what
CORE_LOCK = [
    'RIDAGEYR','RIAGENDR','RIDRETH1','INDFMPIR',
    'BMXBMI','BMXWAIST',
    'BPXSY1','BPXDI1','BPXPLS',
    'LBXTC','LBDHDD','LBDLDL','LBXTR','LBXAPB',
    'LBXGLU','LBXGH','LBXCRP','LBXSCR','URXUMA','URXUCR',
    'MCQ160C','MCQ160E','CAD_any',
    'Squared_curvature_tortuosity','Artery_Distance_tortuosity','Artery_Squared_curvature_tortuosity',
    'Vein_Distance_tortuosity','Vein_Squared_curvature_tortuosity',
    'CRAE_Knudtson','CRVE_Knudtson','AVR_Knudtson'
]

CANDIDATE_EXTRA = [
    'Disc_height','Disc_width','Cup_height','Cup_width','CDR_vertical','CDR_horizontal',
    'Fractal_dimension','Vessel_density','Average_width','Distance_tortuosity','Tortuosity_density',
    'Artery_Fractal_dimension','Artery_Vessel_density','Artery_Average_width','Artery_Tortuosity_density',
    'CRAE_Hubbard','Vein_Fractal_dimension','Vein_Vessel_density','Vein_Average_width','Vein_Tortuosity_density',
    'CRVE_Hubbard','AVR_Hubbard','SMQ020','SMD030','SMD641','SMD650','BPQ020','BPQ050A','BPQ080',
    'LEXLABPI','LEXRABPI','WTMEC2YR','WTSAF2YR','LBXIN'
]


def build(df):
    if 'SBP_mean' not in df.columns:
        c=[x for x in ['BPXSY1','BPXSY2','BPXSY3','BPXSY4'] if x in df.columns]
        if c: df['SBP_mean']=df[c].mean(axis=1)
    if 'DBP_mean' not in df.columns:
        c=[x for x in ['BPXDI1','BPXDI2','BPXDI3','BPXDI4'] if x in df.columns]
        if c: df['DBP_mean']=df[c].mean(axis=1)
    if 'PulsePressure_mean' not in df.columns and {'SBP_mean','DBP_mean'}.issubset(df.columns):
        df['PulsePressure_mean']=df['SBP_mean']-df['DBP_mean']
    if 'MAP_mean' not in df.columns and {'SBP_mean','DBP_mean'}.issubset(df.columns):
        df['MAP_mean']=df['DBP_mean']+(df['SBP_mean']-df['DBP_mean'])/3
    if 'NonHDL_C' not in df.columns and {'LBXTC','LBDHDD'}.issubset(df.columns):
        df['NonHDL_C']=df['LBXTC']-df['LBDHDD']
    if 'WaistHeightRatio' not in df.columns and {'BMXWAIST','BMXHT'}.issubset(df.columns):
        df['WaistHeightRatio']=df['BMXWAIST']/df['BMXHT']

    cols = [c for c in (CORE_LOCK + CANDIDATE_EXTRA + ['SBP_mean','DBP_mean','PulsePressure_mean','MAP_mean','NonHDL_C','WaistHeightRatio']) if c in df.columns]
    X = df[cols].copy()
    for c in X.columns:
        X[c] = pd.to_numeric(X[c], errors='coerce')
    X = X.replace({7: np.nan,9: np.nan,77: np.nan,99: np.nan,777: np.nan,999: np.nan})
    X = X.dropna(axis=1, how='all')
    X = X.loc[:, X.nunique(dropna=True) > 1]
    X = X.fillna(X.median(numeric_only=True))
    return X


def vif_series(X):
    vals = X.values.astype(float)
    return pd.Series([variance_inflation_factor(vals, i) for i in range(vals.shape[1])], index=X.columns)


def main():
    raw = pd.read_csv(IN_PATH)
    X = build(raw)
    start = X.shape[1]
    core = {c for c in CORE_LOCK if c in X.columns}
    drops=[]

    # Pair pruning among non-core only
    corr = X.corr().abs()
    cols = corr.columns.tolist()
    pairs=[]
    for i in range(len(cols)):
        for j in range(i+1,len(cols)):
            r = corr.iloc[i,j]
            if r >= R_THRESH:
                pairs.append((cols[i],cols[j],float(r)))
    for a,b,r in sorted(pairs,key=lambda z:z[2], reverse=True):
        if a not in X.columns or b not in X.columns:
            continue
        if a in core and b in core:
            continue
        if a in core and b not in core:
            X = X.drop(columns=[b]); drops.append({'stage':'pair','drop':b,'pair':f'{a}~{b}','r':r,'reason':'keep_core'})
        elif b in core and a not in core:
            X = X.drop(columns=[a]); drops.append({'stage':'pair','drop':a,'pair':f'{a}~{b}','r':r,'reason':'keep_core'})
        else:
            # both non-core: drop second
            X = X.drop(columns=[b]); drops.append({'stage':'pair','drop':b,'pair':f'{a}~{b}','r':r,'reason':'noncore_prune'})

    # VIF prune non-core only
    for _ in range(300):
        if X.shape[1] <= len(core)+2:
            break
        v = vif_series(X)
        bad = v[v>VIF_THRESH].sort_values(ascending=False)
        if bad.empty:
            break
        cand = [c for c in bad.index if c not in core]
        if not cand:
            break
        d = cand[0]
        drops.append({'stage':'vif','drop':d,'vif':float(v[d]),'reason':'noncore_vif'})
        X = X.drop(columns=[d])

    final_v = vif_series(X).sort_values(ascending=False)

    id_cols=[c for c in ['SEQN','Name'] if c in raw.columns]
    out = pd.concat([raw[id_cols].reset_index(drop=True), X.reset_index(drop=True)], axis=1)
    out.to_csv(OUT_DATA,index=False)
    pd.DataFrame({'Variable':X.columns}).to_csv(OUT_FEATS,index=False)
    pd.DataFrame(drops).to_csv(OUT_DROP,index=False)

    with open(OUT_SUM,'w',encoding='utf-8') as f:
        f.write('Conservative core-locked pruning summary\n')
        f.write('='*60+'\n')
        f.write(f'Start features: {start}\n')
        f.write(f'Final features: {X.shape[1]}\n')
        f.write(f'Dropped features: {start - X.shape[1]}\n')
        f.write(f'Core locked kept: {len(core)}\n')
        f.write(f'Final max VIF: {final_v.max():.3f}\n')
        f.write('\nTop 15 VIF:\n')
        for k,val in final_v.head(15).items():
            f.write(f'- {k}: {val:.3f}\n')

    print('Saved:', OUT_DATA)
    print('Saved:', OUT_FEATS)
    print('Saved:', OUT_DROP)
    print('Saved:', OUT_SUM)
    print('Start:', start, 'Final:', X.shape[1], 'Core kept:', len(core))

if __name__ == '__main__':
    main()
