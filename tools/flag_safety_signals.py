import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("TRIAL_DATA_PATH", "./trial_data")


def flag_safety_signals() -> dict:
    ae_path = os.path.join(BASE, "sdtm", "ae.csv")
    if not os.path.exists(ae_path):
        return {"error": "ae.csv not found in trial_data/sdtm/"}

    try:
        df = pd.read_csv(ae_path)
    except pd.errors.EmptyDataError:
        return {"error": "ae.csv is empty"}

    df.columns = df.columns.str.strip().str.upper()

    if "SUBJID" in df.columns and "USUBJID" not in df.columns:
        df = df.rename(columns={"SUBJID": "USUBJID"})

    serious = pd.DataFrame()
    severe = pd.DataFrame()
    fatal = pd.DataFrame()

    if "AESER" in df.columns:
        serious = df[df["AESER"].astype(str).str.upper().isin(["Y", "YES", "TRUE", "1"])]

    if "AESEV" in df.columns:
        severe = df[df["AESEV"].astype(str).str.upper() == "SEVERE"]
    elif "SEVERITY" in df.columns:
        severe = df[df["SEVERITY"].astype(str).str.upper() == "SEVERE"]

    if "AEOUT" in df.columns:
        fatal = df[df["AEOUT"].astype(str).str.upper() == "FATAL"]

    signals = pd.concat([serious, severe, fatal], ignore_index=True).drop_duplicates()

    return {
        "total_ae_records": len(df),
        "serious_aes": len(serious),
        "severe_aes": len(severe),
        "fatal_aes": len(fatal),
        "unique_signals": len(signals),
        "signals": signals.to_dict(orient="records"),
        "alert": (
            f"⚠️ CRITICAL: {len(fatal)} fatal and {len(serious)} serious AEs detected. Immediate review required."
            if len(fatal) > 0 or len(serious) > 0
            else "✅ No critical safety signals detected."
        ),
    }