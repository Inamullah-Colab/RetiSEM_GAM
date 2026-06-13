from pathlib import Path
import json
import pandas as pd
import requests

DATA_DIR = Path(r"NAHES_Dataset")
BASE_URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles"
MODULES = ["MCQ_D", "DIQ_D", "GLU_D", "GHB_D", "CRP_D", "BIOPRO_D", "ALB_CR_D", "BPQ_D"]
EXISTING_MERGED = DATA_DIR / "NHANES_merged.csv"
OUT_MERGED = DATA_DIR / "NHANES_merged_cvd_extended.csv"
OUT_SUMMARY_JSON = DATA_DIR / "NHANES_cvd_extension_download_merge_summary.json"
OUT_SUMMARY_TXT = DATA_DIR / "NHANES_cvd_extension_download_merge_summary.txt"


def download_module(module: str):
    local_path = DATA_DIR / f"{module}.xpt"
    url = f"{BASE_URL}/{module}.xpt"
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200 and b"HEADER RECORD" in r.content[:120]:
            local_path.write_bytes(r.content)
            return {"module": module, "status": "downloaded_valid_xpt", "path": str(local_path), "url": url, "http": r.status_code, "bytes": len(r.content)}
        return {"module": module, "status": "download_not_xpt", "path": str(local_path), "url": url, "http": r.status_code, "bytes": len(r.content)}
    except Exception as e:
        return {"module": module, "status": "error", "path": str(local_path), "url": url, "http": None, "error": str(e)}


def read_xpt(path: Path) -> pd.DataFrame:
    df = pd.read_sas(path)
    df.columns = [c.decode() if isinstance(c, bytes) else c for c in df.columns]
    return df


def main():
    base_df = pd.read_csv(EXISTING_MERGED)
    merged = base_df.copy()

    download_log = [download_module(m) for m in MODULES]
    merge_log = []

    for d in download_log:
        module = d["module"]
        path = Path(d["path"])
        if not path.exists() or d["status"] != "downloaded_valid_xpt":
            merge_log.append({"module": module, "merge_status": "skipped_invalid_or_missing"})
            continue

        try:
            df = read_xpt(path)
            if "SEQN" not in df.columns:
                merge_log.append({"module": module, "merge_status": "skipped_no_SEQN"})
                continue

            add_cols = [c for c in df.columns if c != "SEQN" and c not in merged.columns]
            merged = merged.merge(df[["SEQN"] + add_cols], on="SEQN", how="left")
            merge_log.append({"module": module, "merge_status": "merged", "cols_added": len(add_cols), "sample_added": add_cols[:12]})
        except Exception as e:
            merge_log.append({"module": module, "merge_status": "error", "error": str(e)})

    merged.to_csv(OUT_MERGED, index=False)

    summary = {
        "base_shape": [int(base_df.shape[0]), int(base_df.shape[1])],
        "output_shape": [int(merged.shape[0]), int(merged.shape[1])],
        "download_log": download_log,
        "merge_log": merge_log,
        "output_file": str(OUT_MERGED),
    }
    OUT_SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = []
    lines.append("NHANES CVD extension scan/download/merge summary")
    lines.append("=" * 70)
    lines.append(f"Base shape: {base_df.shape}")
    lines.append(f"Output shape: {merged.shape}")
    lines.append("")
    lines.append("Download status:")
    for x in download_log:
        lines.append(f"- {x['module']}: {x['status']} | http={x.get('http')} | bytes={x.get('bytes')}")
    lines.append("")
    lines.append("Merge status:")
    for x in merge_log:
        lines.append(f"- {x['module']}: {x['merge_status']} | cols_added={x.get('cols_added')}")

    OUT_SUMMARY_TXT.write_text("\n".join(lines), encoding="utf-8")
    print("Saved:", OUT_MERGED)
    print("Final shape:", merged.shape)


if __name__ == "__main__":
    main()
