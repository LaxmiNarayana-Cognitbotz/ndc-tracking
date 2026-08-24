from fastapi import HTTPException
# Status normalization — Section 6 of DEVELOPMENT.md

STATUS_MAP: dict[str, str] = {
    "Pending": "PENDING",
    "Completed": "COMPLETED",
    "In Progress": "IN_PROGRESS",
    "Dependent": "DEPENDENT",
    "Not Applicable": "NOT_APPLICABLE",
}

# Approval stage column mapping — Section 8.3 of DEVELOPMENT.md
# (stage_key, assignee_column, status_column, sequence_order)
APPROVAL_STAGES: list[tuple[str, str, str, int]] = [
    ("RM",                "Approval Type - RM",                "RM- Approval Status",                 1),
    ("IT",                "Approval Type - IT",                "IT- Approval Status",                 2),
    ("Abex",              "Approval Type - Abex",              "Abex - Approval Status",              3),
    ("Telecom",           "Approval Type - Telecom",           "Telecom - Approval Status",           4),
    ("Store",             "Approval Type - Store",             "Store - Approval Status",             5),
    ("Safety",            "Approval Type - Safety",            "Safety - Approval Status",            6),
    ("Administration",    "Approval Type - Administration",    "Administration - Approval Status",    7),
    ("Security",          "Approval Type - Security",          "Security - Approval Status",          8),
    ("HR",                "Approval Type - HR",                "HR - Approval Status",                9),
    ("GCC HR",            "Approval Type \u2013 GCC HR",       "GCC HR - Approval Status",           10),
    ("Business Specific", "Approval Type - Business Specific", "Business Specific - Approval Status", 11),
    ("Final Abex",        "Approval Type \u2013 Final Abex",   "Final Abex - Approval Status",       12),
    ("Legatrix",          "Approval Type \u2013 Legatrix",     "Legatrix - Approval Status",         13),
]


def normalize_status(raw: str | None) -> str | None:
    """Normalize raw Excel status value to internal enum."""
    try:
        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            return None
        raw_stripped = raw.strip() if isinstance(raw, str) else str(raw).strip()
        return STATUS_MAP.get(raw_stripped)
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in normalize_status: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')
