"""Excel parser — reads .xlsb and .xlsx into a list of row dicts."""

from fastapi import HTTPException
import email
import io
import warnings
from email import policy
from pathlib import Path

import pandas as pd
import pyxlsb

# The main sheet name from the source file
EXPECTED_SHEET = "NDC Process Request Status(NDC )"


def read_excel(file_path: str | Path) -> list[dict]:
    """Read .xlsb or .xlsx and return rows as list of dicts.

    Uses pyxlsb for .xlsb files, openpyxl for .xlsx.
    Targets the expected sheet name; falls back to first sheet if not found.
    """
    try:
        file_path = Path(file_path)
        ext = file_path.suffix.lower()

        if ext == ".xlsb":
            return _read_xlsb(file_path)
        elif ext in (".xlsx", ".xls"):
            return _read_xlsx(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in read_excel: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


def _read_xlsb(file_path: Path) -> list[dict]:
    """Read .xlsb using pyxlsb, return list of dicts."""
    try:
        with pyxlsb.open_workbook(str(file_path)) as wb:
            # Try expected sheet, fallback to first
            sheet_name = EXPECTED_SHEET if EXPECTED_SHEET in wb.sheets else wb.sheets[0]
            rows = []
            with wb.get_sheet(sheet_name) as sheet:
                for row in sheet.rows():
                    rows.append([cell.v for cell in row])

        if not rows:
            return []

        # First row is headers
        headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(rows[0])]
        data = []
        for row in rows[1:]:
            # Pad row to match header length
            padded = row + [None] * (len(headers) - len(row))
            data.append(dict(zip(headers, padded[:len(headers)])))

        return data
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in _read_xlsb: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


def _read_xlsx(file_path: Path) -> list[dict]:
    """Read .xlsx using openpyxl via pandas, return list of dicts."""
    try:
        df = pd.read_excel(file_path, sheet_name=EXPECTED_SHEET, engine="openpyxl")
        df = df.where(df.notna(), None)
        return df.to_dict(orient="records")
    except ValueError:
        try:
            # Sheet not found, use first sheet
            df = pd.read_excel(file_path, sheet_name=0, engine="openpyxl")
            df = df.where(df.notna(), None)
            return df.to_dict(orient="records")
        except Exception:
            pass
    except Exception:
        pass
        
    # If openpyxl fails completely, it might be an Oracle MHTML file with .xls extension
    if file_path.suffix.lower() == ".xls":
        return _read_oracle_mhtml_xls(file_path)
    
    raise ValueError(f"Could not parse Excel file: {file_path}")


def _read_oracle_mhtml_xls(file_path: Path) -> list[dict]:
    """Read Oracle Fusion exported MHTML disguised as .xls and parse html content."""
    try:
        with open(file_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        html_content = b''
        charset = 'utf-8'
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    html_content = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    break
        else:
            html_content = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'

        if not html_content:
            # Fallback to reading raw file if email parsing didn't find HTML
            with open(file_path, 'rb') as f:
                raw = f.read()
                if b'<html' in raw.lower() or b'<table' in raw.lower():
                    html_content = raw

        if html_content:
            # Ignore Beautiful Soup's XMLParsedAsHTMLWarning
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # Parse HTML into DataFrames directly from bytes
                dfs = pd.read_html(io.BytesIO(html_content))

            # Find the main data table (it should have the most columns, e.g., > 10)
            data_df = None
            for df in dfs:
                if df.shape[1] > 10:
                    data_df = df
                    break

            if data_df is not None:
                # First row in the data table contains the headers
                raw_columns = data_df.iloc[0].astype(str).str.strip().tolist()
            
                # Fix em-dash encoding issues (often comes through as \ufffd or other symbols)
                fixed_columns = []
                for col in raw_columns:
                    fixed_col = col.replace('\ufffd', '\u2013')
                    # If there's an exact string like "Approval Type - GCC HR" that should have em-dash
                    if "GCC HR" in fixed_col and "Approval Type" in fixed_col:
                        fixed_col = "Approval Type \u2013 GCC HR"
                    elif "Final Abex" in fixed_col and "Approval Type" in fixed_col:
                        fixed_col = "Approval Type \u2013 Final Abex"
                    elif "Legatrix" in fixed_col and "Approval Type" in fixed_col:
                        fixed_col = "Approval Type \u2013 Legatrix"
                    fixed_columns.append(fixed_col)
                
                data_df.columns = fixed_columns
                data_df = data_df[1:].reset_index(drop=True)
            
                # Pad NaN values with None (astype(object) prevents nan floats)
                data_df = data_df.astype(object).where(pd.notna(data_df), None)
                return data_df.to_dict(orient="records")

        raise ValueError(f"Failed to parse Oracle MHTML from file: {file_path}")
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in _read_oracle_mhtml_xls: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')
