import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("TRIAL_DATA_PATH", "./trial_data")

DOMAIN_FILES = {
    "AE": "ae.csv",
    "DM": "dm.csv",
    "LB": "lb.csv",
    "CM": "cm.csv",
    "VS": "vs.csv",
}

FIELD_ALIASES = {
    "AESEV": ["AESEV", "SEVERITY"],
    "SEVERITY": ["SEVERITY", "AESEV"],
    "AESER": ["AESER"],
    "AEOUT": ["AEOUT"],
    "USUBJID": ["USUBJID", "SUBJID"],
    "SEX": ["SEX"],
    "AGE": ["AGE"],
}


def _load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.upper()

    if "SUBJID" in df.columns and "USUBJID" not in df.columns:
        df = df.rename(columns={"SUBJID": "USUBJID"})

    return df


def _resolve_field(df: pd.DataFrame, field: str) -> str | None:
    if not field:
        return None

    key = field.strip().upper()
    if key in df.columns:
        return key

    for alias in FIELD_ALIASES.get(key, []):
        if alias in df.columns:
            return alias

    return None


def query_sdtm(
    domain: str,
    filter_field: str = None,
    filter_value: str = None,
    age_gt: int = None,
    sex: str = None,
) -> dict:
    domain = domain.upper()
    filename = DOMAIN_FILES.get(domain)

    if not filename:
        return {"error": f"Unknown domain: {domain}. Use: AE, DM, LB, CM, VS"}

    filepath = os.path.join(BASE, "sdtm", filename)
    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    try:
        df = _load_csv(filepath)
    except pd.errors.EmptyDataError:
        return {"error": f"{filename} is empty"}

    # Join with DM only when needed and only if the domain is not DM.
    if (age_gt is not None or sex is not None) and domain != "DM":
        dm_path = os.path.join(BASE, "sdtm", "dm.csv")
        if not os.path.exists(dm_path):
            return {"error": "DM file required for age/sex filtering"}

        dm = _load_csv(dm_path)
        if "USUBJID" not in dm.columns:
            return {"error": "USUBJID missing in DM file"}

        dm_needed = [c for c in ["USUBJID", "AGE", "SEX"] if c in dm.columns]
        if "AGE" not in dm_needed or "SEX" not in dm_needed:
            return {"error": "DM file must contain AGE and SEX for age/sex filtering"}

        if "USUBJID" not in df.columns:
            return {"error": f"USUBJID missing in {filename}"}

        # ---- CLEAN JOIN KEYS ----
        df["USUBJID"] = df["USUBJID"].astype(str).str.strip()
        dm["USUBJID"] = dm["USUBJID"].astype(str).str.strip()

        # ---- MERGE ----
        df = df.merge(dm[dm_needed], on="USUBJID", how="left", suffixes=("", "_DM"))

        # ---- CLEAN TYPES AFTER MERGE ----
        if "AGE" in df.columns:
            df["AGE"] = pd.to_numeric(df["AGE"], errors="coerce")

        if "SEX" in df.columns:
            df["SEX"] = df["SEX"].astype(str).str.strip().str.upper()

    # Age filter
    if age_gt is not None:
        if "AGE" not in df.columns:
            return {"error": "AGE column not available for age filtering"}

        df["AGE"] = pd.to_numeric(df["AGE"], errors="coerce")
        df = df[df["AGE"].notna()]
        df = df[df["AGE"] > int(age_gt)]

    # Sex filter
    if sex:
        if "SEX" not in df.columns:
            return {"error": "SEX column not available for sex filtering"}

        # Normalize input
        sex_clean = sex.strip().upper()

        if sex_clean in ["FEMALE", "F"]:
            sex_clean = "F"
        elif sex_clean in ["MALE", "M"]:
            sex_clean = "M"

        df["SEX"] = df["SEX"].astype(str).str.strip().str.upper()
        df = df[df["SEX"] == sex_clean]

    # Generic field filter
    if filter_field and filter_value:
        resolved = _resolve_field(df, filter_field)
        if resolved:
            series = df[resolved].astype(str).str.upper()
            df = df[series.str.contains(str(filter_value).strip().upper(), na=False)]

    if df.empty:
        return {
            "domain": domain,
            "total_records": 0,
            "columns": list(df.columns),
            "records": [],
            "message": "No matching records found",
        }

    return {
        "domain": domain,
        "total_records": len(df),
        "columns": list(df.columns),
        "records": df.to_dict(orient="records"),
    }