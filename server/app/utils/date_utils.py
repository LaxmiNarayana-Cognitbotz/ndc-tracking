from datetime import date, datetime, timedelta


def excel_serial_to_date(serial) -> date | None:
    """Convert Excel serial date number to Python date."""
    if serial is None:
        return None
        
    if isinstance(serial, float) and (serial != serial):  # check for NaN
        return None
        
    if isinstance(serial, str):
        serial = serial.strip()
        if not serial:
            return None
        if "-" in serial or "/" in serial:
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(serial, fmt).date()
                except ValueError:
                    pass
    try:
        serial = float(serial)
        if serial != serial:  # check for NaN
            return None
    except (ValueError, TypeError):
        return None
    return (datetime(1899, 12, 30) + timedelta(days=serial)).date()


def pending_days(ndc_initiated_date: date | None) -> int | None:
    """Days since NDC was initiated (for pending records)."""
    if not ndc_initiated_date:
        return None
    return (date.today() - ndc_initiated_date).days


def tat_days(ndc_initiated_date: date | None, ndc_completed_date: date | None) -> int | None:
    """Turnaround time in days for completed records."""
    if not ndc_initiated_date or not ndc_completed_date:
        return None
    return (ndc_completed_date - ndc_initiated_date).days


def days_to_lwd(last_working_date: date | None) -> int | None:
    """Days until last working date (negative = past LWD)."""
    if not last_working_date:
        return None
    return (last_working_date - date.today()).days


def days_since_assigned(ndc_assigned_date: date | None) -> int | None:
    """Days since NDC was assigned."""
    if not ndc_assigned_date:
        return None
    return (date.today() - ndc_assigned_date).days


def completion_delay(ndc_completed_date: date | None, last_working_date: date | None) -> int | None:
    """Days between LWD and completion (post-LWD lag)."""
    if not ndc_completed_date or not last_working_date:
        return None
    return (ndc_completed_date - last_working_date).days
