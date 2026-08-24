"""Ingest service — validate, normalize, upsert NDC records from parsed Excel rows."""

import logging
from datetime import date
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers.upload.excel_parser import read_excel
from app.helpers.upload.status_mapper import APPROVAL_STAGES, normalize_status
from app.models.ndc_approval import NdcApproval
from app.models.ndc_deleted_record import NdcDeletedRecord
from app.models.ndc_record import NdcRecord
from app.models.upload_batch import UploadBatch
from app.utils.date_utils import excel_serial_to_date

logger = logging.getLogger(__name__)

# Required columns for validation
REQUIRED_COLUMNS = ["Person Number", "Name of an Employee", "NDC Stage"]
VALID_STAGES = {"Recovery Pending", "GCC Pending", "NDC Completed"}


def _str_or_none(val) -> str | None:
    try:
        if val is None:
            return None
        if isinstance(val, float) and val != val:  # check for NaN
            return None
        s = str(val).strip()
        return s if s else None
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in _str_or_none: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


class IngestService:
    @staticmethod
    async def ingest_excel_file(
        file_path: str | Path,
        file_name: str,
        uploaded_by: str,
        db: AsyncSession,
        source_type: str = "manual",
    ) -> dict:
        """Parse Excel file, validate, and upsert into DB. Returns ingest result dict."""
        try:
            # Create batch record
            batch = UploadBatch(
                file_name=file_name,
                source_type=source_type,
                uploaded_by=uploaded_by,
                status="processing",
            )
            db.add(batch)
            await db.flush()
            batch_id = batch.id

            errors: list[str] = []
            records_processed = 0
            records_failed = 0

            try:
                rows = read_excel(file_path)
            except Exception as e:
                batch.status = "failed"
                batch.error_message = str(e)
                await db.commit()
                return {
                    "batch_id": batch_id,
                    "records_processed": 0,
                    "records_failed": 0,
                    "status": "failed",
                    "errors": [f"Failed to parse file: {e}"],
                }

            if not rows:
                batch.status = "failed"
                batch.error_message = "No data rows found"
                await db.commit()
                return {
                    "batch_id": batch_id,
                    "records_processed": 0,
                    "records_failed": 0,
                    "status": "failed",
                    "errors": ["No data rows found in file"],
                }

            # Validate column presence
            first_row_keys = set(rows[0].keys())
            missing = [c for c in REQUIRED_COLUMNS if c not in first_row_keys]
            if missing:
                batch.status = "failed"
                batch.error_message = f"Missing columns: {missing}"
                await db.commit()
                return {
                    "batch_id": batch_id,
                    "records_processed": 0,
                    "records_failed": 0,
                    "status": "failed",
                    "errors": [f"Missing required columns: {missing}"],
                }

            # Load excluded / deleted employees to prevent re-importing
            deleted_res = await db.execute(select(NdcDeletedRecord.person_number))
            deleted_person_numbers = set(deleted_res.scalars().all())

            for idx, row in enumerate(rows, start=2):  # row 2 = first data row in Excel
                try:
                    person_number = row.get("Person Number")
                    employee_name = row.get("Name of an Employee")
                    ndc_stage = row.get("NDC Stage")

                    # Row-level validation
                    if not person_number:
                        errors.append(f"Row {idx}: Missing Person Number")
                        records_failed += 1
                        continue
                    if not employee_name:
                        errors.append(f"Row {idx}: Missing Employee Name")
                        records_failed += 1
                        continue
                    if ndc_stage and ndc_stage not in VALID_STAGES:
                        errors.append(f"Row {idx}: Invalid NDC Stage '{ndc_stage}'")
                        records_failed += 1
                        continue

                    person_number = int(float(person_number))

                    # Permanently excluded by Super Admin — skip row
                    if person_number in deleted_person_numbers:
                        continue

                    # Upsert ndc_record
                    result = await db.execute(
                        select(NdcRecord).where(NdcRecord.person_number == person_number)
                    )
                    record = result.scalar_one_or_none()

                    record_data = {
                        "person_number": person_number,
                        "employee_name": str(employee_name).strip(),
                        "business_unit": _str_or_none(row.get("Business Unit")),
                        "legal_employer": _str_or_none(row.get("Legal Employer")),
                        "location": _str_or_none(row.get("Location")),
                        "location_city": _str_or_none(row.get("Location City")),
                        "department": _str_or_none(row.get("Department")),
                        "department_reporting_name": _str_or_none(row.get("Department Reporting Name")),
                        "ndc_stage": ndc_stage,
                        "resignation_date": excel_serial_to_date(row.get("Resignation Date")),
                        "last_working_date": excel_serial_to_date(row.get("Last Working Date")),
                        "ndc_assigned_date": excel_serial_to_date(row.get("NDC Assigned date")),
                        "ndc_initiated_date": excel_serial_to_date(row.get("NDC Initiated Date")),
                        "ndc_completed_date": excel_serial_to_date(row.get("NDC Completed Date")),
                        "created_by": _str_or_none(row.get("Created by")),
                        "source_file": file_name,
                        "batch_id": batch_id,
                    }

                    # Only ingest records where NDC Assigned date is >= 09/02/2026
                    cutoff_date = date(2026, 2, 9)
                    if record_data["ndc_assigned_date"] and record_data["ndc_assigned_date"] < cutoff_date:
                        continue

                    if record:
                        # Preserve F&F fields that are manually set — don't overwrite them
                        preserved_fields = {
                            "is_fnf_completed", "is_fnf_revision", "fnf_completed_date",
                            "gcc_initiate_date", "fnf_document_count", "fnf_revision_comment",
                        }
                        for key, value in record_data.items():
                            if key not in preserved_fields:
                                setattr(record, key, value)
                    else:
                        record = NdcRecord(**record_data)
                        db.add(record)

                    await db.flush()

                    # Build a map of existing approvals for date preservation
                    existing_approvals_res = await db.execute(
                        select(NdcApproval).where(NdcApproval.ndc_record_id == record.id)
                    )
                    existing_approvals_map = {
                        a.stage_name: a for a in existing_approvals_res.scalars().all()
                    }

                    # Delete existing approvals, then reinsert with preserved dates
                    await db.execute(
                        delete(NdcApproval).where(NdcApproval.ndc_record_id == record.id)
                    )

                    for stage_key, type_col, status_col, order in APPROVAL_STAGES:
                        raw_status = row.get(status_col)
                        approver = row.get(type_col)
                        new_status = normalize_status(raw_status) if raw_status else None

                        existing = existing_approvals_map.get(stage_key)
                        today_date = date.today()

                        # --- stage_completed_at logic ---
                        # 1. If existing date exists and status is still COMPLETED → preserve it
                        # 2. If new status is COMPLETED but no existing date → auto-stamp today
                        # 3. If status changed away from COMPLETED → clear the date
                        preserved_date = None
                        if existing and existing.stage_completed_at:
                            if new_status == "COMPLETED":
                                preserved_date = existing.stage_completed_at  # keep existing date
                            # else: status changed away from COMPLETED, date is cleared
                        elif new_status == "COMPLETED":
                            preserved_date = today_date  # newly completed → auto-stamp today

                        # --- stage_started_at logic ---
                        # 1. If existing start date exists → always preserve it
                        # 2. If new status is non-null and no existing start → auto-stamp today
                        preserved_start = None
                        if existing and existing.stage_started_at:
                            preserved_start = existing.stage_started_at  # always preserve
                        elif new_status and new_status not in ("NOT_APPLICABLE", None):
                            preserved_start = today_date  # first time this stage has a status

                        approval = NdcApproval(
                            ndc_record_id=record.id,
                            stage_name=stage_key,
                            approver_name=_str_or_none(approver),
                            status=new_status,
                            sequence_order=order,
                            stage_completed_at=preserved_date,
                            stage_started_at=preserved_start,
                        )
                        db.add(approval)
                        
                        # Also save the date explicitly on the NdcRecord for the database
                        # Map stage_key to the explicit column name on NdcRecord
                        col_name_map = {
                            "RM": "rm_approval_date",
                            "IT": "it_approval_date",
                            "Abex": "abex_approval_date",
                            "Telecom": "telecom_approval_date",
                            "Store": "store_approval_date",
                            "Safety": "safety_approval_date",
                            "Administration": "administration_approval_date",
                            "Security": "security_approval_date",
                            "HR": "hr_approval_date",
                            "GCC HR": "gcc_hr_approval_date",
                            "Final Abex": "final_abex_approval_date",
                            "Business Specific": "business_specific_approval_date",
                            "Legatrix": "legatrix_approval_date"
                        }
                        col_name = col_name_map.get(stage_key)
                        if col_name:
                            setattr(record, col_name, preserved_date)

                    records_processed += 1

                except Exception as e:
                    logger.exception(f"Row {idx} failed: {e}")
                    errors.append(f"Row {idx}: {e}")
                    records_failed += 1

            # Update batch record
            batch.records_count = records_processed
            batch.status = "success" if records_failed == 0 else "partial"
            if errors:
                batch.error_message = "\n".join(errors[:50])  # cap stored errors

            await db.commit()

            return {
                "batch_id": batch_id,
                "records_processed": records_processed,
                "records_failed": records_failed,
                "status": batch.status,
                "errors": errors,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in ingest_excel_file: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")
