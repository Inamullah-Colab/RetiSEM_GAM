from pathlib import Path
import pandas as pd

DATA_DIR = Path('NAHES_Dataset')
NHANES_PATH = DATA_DIR / 'NHANES_merged_cvd_extended.csv'
MAC_FULL_PATH = DATA_DIR / 'Macular_Zone_B_Measurement_imputed.csv'
NAME_SEQ_PATH = DATA_DIR / 'Name_SEQ.csv'

OUT_MAC_WITH_SEQ = DATA_DIR / 'Macular_Zone_B_Measurement_imputed_with_SEQ.csv'
OUT_COV = DATA_DIR / 'NHANES_cvd_extended_with_macular_full_coverage.csv'
OUT_MATCHED = DATA_DIR / 'NHANES_cvd_extended_with_macular_full_matched.csv'
OUT_SUM = DATA_DIR / 'NHANES_macular_full_merge_summary.txt'


def main():
    nh = pd.read_csv(NHANES_PATH)
    mac = pd.read_csv(MAC_FULL_PATH)
    mseq = pd.read_csv(NAME_SEQ_PATH)

    # Attach SEQN to full macular by image name
    mac_seq = mac.merge(mseq[['Name', 'SEQN']], on='Name', how='left')

    # Normalize SEQN and deduplicate
    nh['SEQN'] = pd.to_numeric(nh['SEQN'], errors='coerce')
    mac_seq['SEQN'] = pd.to_numeric(mac_seq['SEQN'], errors='coerce')

    nh = nh.dropna(subset=['SEQN']).copy()
    mac_seq = mac_seq.dropna(subset=['SEQN']).copy()

    nh['SEQN'] = nh['SEQN'].astype(int)
    mac_seq['SEQN'] = mac_seq['SEQN'].astype(int)

    mac_seq = mac_seq.drop_duplicates(subset=['SEQN'], keep='first').copy()

    # Coverage and matched outputs
    cov = nh.merge(mac_seq, on='SEQN', how='left')
    cov['HAS_MACULAR_FULL'] = cov['Name'].notna().astype(int)

    matched = nh.merge(mac_seq, on='SEQN', how='inner')

    # Save files
    mac_seq.to_csv(OUT_MAC_WITH_SEQ, index=False)
    cov.to_csv(OUT_COV, index=False)
    matched.to_csv(OUT_MATCHED, index=False)

    nh_n = len(nh)
    mac_n = len(mac_seq)
    mt_n = len(matched)
    unmatched_nh = nh_n - mt_n
    unmatched_mac = mac_n - mt_n

    lines = []
    lines.append('NHANES + Full Imputed Macular Zone B merge summary')
    lines.append('=' * 72)
    lines.append(f'NHANES source: {NHANES_PATH.name} | rows={nh_n:,} | cols={nh.shape[1]}')
    lines.append(f'Macular full source: {MAC_FULL_PATH.name} | rows={len(mac):,} | cols={mac.shape[1]}')
    lines.append(f'Name-SEQ map source: {NAME_SEQ_PATH.name} | rows={len(mseq):,}')
    lines.append(f'Macular with SEQN: {OUT_MAC_WITH_SEQ.name} | rows={mac_n:,} | cols={mac_seq.shape[1]}')
    lines.append('')
    lines.append(f'Coverage file: {OUT_COV.name} | rows={len(cov):,} | cols={cov.shape[1]}')
    lines.append(f'Matched file: {OUT_MATCHED.name} | rows={mt_n:,} | cols={matched.shape[1]}')
    lines.append('')
    lines.append(f'Match rate vs NHANES: {mt_n/nh_n:.2%}')
    lines.append(f'Match rate vs Full Macular: {mt_n/mac_n:.2%}')
    lines.append(f'NHANES without macular match: {unmatched_nh:,}')
    lines.append(f'Macular without NHANES match: {unmatched_mac:,}')

    OUT_SUM.write_text('\n'.join(lines), encoding='utf-8')

    print('Saved:', OUT_MAC_WITH_SEQ)
    print('Saved:', OUT_COV)
    print('Saved:', OUT_MATCHED)
    print('Saved:', OUT_SUM)
    print('Matched rows:', mt_n)


if __name__ == '__main__':
    main()
