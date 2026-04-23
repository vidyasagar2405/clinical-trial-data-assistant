import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("TRIAL_DATA_PATH", "./trial_data")


def _load_domain(domain: str) -> pd.DataFrame:
    path = os.path.join(BASE, "sdtm", f"{domain}.csv")
    if not os.path.exists(path):
        return pd.DataFrame()

    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.upper()

    if "SUBJID" in df.columns and "USUBJID" not in df.columns:
        df = df.rename(columns={"SUBJID": "USUBJID"})

    return df


def _filter_patient(df: pd.DataFrame, pid: str) -> pd.DataFrame:
    if df.empty:
        return df
    if "USUBJID" not in df.columns:
        return pd.DataFrame()
    return df[df["USUBJID"].astype(str).str.upper() == pid]


def summarize_patient(patient_id: str) -> dict:
    pid = patient_id.strip().upper()

    dm = _load_domain("dm")
    ae = _load_domain("ae")
    lb = _load_domain("lb")
    cm = _load_domain("cm")
    vs = _load_domain("vs")

    dm_p = _filter_patient(dm, pid)
    if dm_p.empty:
        return {"error": f"Patient '{pid}' not found in demographics (DM) domain"}

    ae_p = _filter_patient(ae, pid)
    lb_p = _filter_patient(lb, pid)
    cm_p = _filter_patient(cm, pid)
    vs_p = _filter_patient(vs, pid)

    severe_mask = pd.Series([False] * len(ae_p), index=ae_p.index)
    if "AESEV" in ae_p.columns:
        severe_mask = ae_p["AESEV"].astype(str).str.upper() == "SEVERE"
    elif "SEVERITY" in ae_p.columns:
        severe_mask = ae_p["SEVERITY"].astype(str).str.upper() == "SEVERE"

    fatal_mask = pd.Series([False] * len(ae_p), index=ae_p.index)
    if "AEOUT" in ae_p.columns:
        fatal_mask = ae_p["AEOUT"].astype(str).str.upper() == "FATAL"

    abnormal_lb = pd.DataFrame()
    if not lb_p.empty:
        if "LBNRIND" in lb_p.columns:
            abnormal_lb = lb_p[lb_p["LBNRIND"].astype(str).str.upper() != "NORMAL"]

    dm_record = dm_p.iloc[0].to_dict()

    return {
        "patient_id": pid,
        "demographics": dm_record,
        "adverse_events": ae_p.to_dict(orient="records"),
        "lab_results": lb_p.to_dict(orient="records"),
        "medications": cm_p.to_dict(orient="records"),
        "vital_signs": vs_p.to_dict(orient="records"),
        "summary": {
            "total_adverse_events": len(ae_p),
            "severe_adverse_events": int(severe_mask.sum()),
            "fatal_adverse_events": int(fatal_mask.sum()),
            "abnormal_lab_results": len(abnormal_lb),
            "total_medications": len(cm_p),
            "total_vital_sign_records": len(vs_p),
        },
    }