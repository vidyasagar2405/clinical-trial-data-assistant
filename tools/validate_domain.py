import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("TRIAL_DATA_PATH", "./trial_data")

# This version supports both your synthetic files and a more SDTM-like layout.
REQUIRED_GROUPS = {
    "AE": [
        ["STUDYID"],
        ["USUBJID"],
        ["AETERM", "AEDECOD"],
        ["AESEV", "SEVERITY"],
    ],
    "DM": [
        ["STUDYID"],
        ["USUBJID"],
        ["AGE"],
        ["SEX"],
    ],
    "LB": [
        ["STUDYID"],
        ["USUBJID"],
        ["LBTEST"],
        ["LBSTRESN", "LBVAL"],
    ],
    "CM": [
        ["STUDYID"],
        ["USUBJID"],
        ["CMTRT"],
        ["CMDOSE", "DOSE"],
    ],
    "VS": [
        ["STUDYID"],
        ["USUBJID"],
        ["VSTEST"],
        ["VSSTRESN", "VSVAL"],
    ],
}

CONTROLLED_TERMS = {
    "AESEV": ["MILD", "MODERATE", "SEVERE"],
    "SEVERITY": ["MILD", "MODERATE", "SEVERE"],
    "SEX": ["M", "F"],
    "AESER": ["Y", "N", "YES", "NO"],
    "AEOUT": ["FATAL", "RECOVERED", "RECOVERING", "UNKNOWN"],
    "LBNRIND": ["NORMAL", "LOW", "HIGH"],
}


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip().str.upper()
    if "SUBJID" in df.columns and "USUBJID" not in df.columns:
        df = df.rename(columns={"SUBJID": "USUBJID"})
    return df


def validate_domain(domain: str) -> dict:
    domain = domain.upper()
    filename = f"{domain.lower()}.csv"
    filepath = os.path.join(BASE, "sdtm", filename)

    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    try:
        df = pd.read_csv(filepath)
    except pd.errors.EmptyDataError:
        return {"error": f"{filename} is empty"}

    df = _standardize_columns(df)
    issues = []

    # Check required groups: at least one column from each group must exist
    for group in REQUIRED_GROUPS.get(domain, []):
        if not any(col in df.columns for col in group):
            issues.append({
                "type": "MISSING_COLUMN",
                "detail": f"Missing at least one of required columns: {group}"
            })

    # Duplicate subject check
    if "USUBJID" in df.columns:
        dup_count = int(df["USUBJID"].duplicated().sum())
        if dup_count > 0:
            issues.append({
                "type": "DUPLICATE_SUBJECT_ID",
                "detail": f"Found {dup_count} duplicate USUBJID values"
            })

    # Row-level checks
    for i, row in df.iterrows():
        row_num = i + 2  # header + 1-indexed row number

        # Controlled terminology checks
        for field, valid_vals in CONTROLLED_TERMS.items():
            if field in df.columns and pd.notna(row.get(field)):
                val = str(row[field]).strip().upper()
                if val not in valid_vals:
                    issues.append({
                        "type": "INVALID_TERMINOLOGY",
                        "row": row_num,
                        "field": field,
                        "detail": f"'{row[field]}' not in {valid_vals}"
                    })

        # Date checks
        for date_col in ["AESTDTC", "LBDTC", "CMSTDTC", "VSDTC"]:
            if date_col in df.columns and pd.notna(row.get(date_col)):
                import re
                if not re.match(r"^\d{4}-\d{2}-\d{2}", str(row[date_col])):
                    issues.append({
                        "type": "DATE_FORMAT",
                        "row": row_num,
                        "field": date_col,
                        "detail": f"'{row[date_col]}' must be YYYY-MM-DD (ISO 8601)"
                    })

        # Age numeric check for DM
        if domain == "DM" and "AGE" in df.columns and pd.notna(row.get("AGE")):
            try:
                float(row["AGE"])
            except Exception:
                issues.append({
                    "type": "INVALID_NUMERIC",
                    "row": row_num,
                    "field": "AGE",
                    "detail": f"'{row['AGE']}' is not numeric"
                })

        # USUBJID presence
        if "USUBJID" in df.columns and pd.isna(row.get("USUBJID")):
            issues.append({
                "type": "MISSING_VALUE",
                "row": row_num,
                "field": "USUBJID",
                "detail": "USUBJID is empty"
            })

    return {
        "domain": domain,
        "total_rows": len(df),
        "compliance_status": "COMPLIANT" if not issues else "NON-COMPLIANT",
        "issues_found": len(issues),
        "issues": issues,
    }