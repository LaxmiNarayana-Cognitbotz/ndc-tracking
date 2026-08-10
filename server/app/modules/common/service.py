import logging
from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.dto.common import CommonNDCRecord, FnfUpdateRequest
from app.models.ndc_approval import NdcApproval
from app.models.ndc_record import NdcRecord
from config.database import BASE_DIR

logger = logging.getLogger(__name__)



class CommonService:
    @staticmethod
    async def fetch_common_records(
        db: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[CommonNDCRecord]:
        """Fetch and construct unified NDC/F&F records."""
        try:
            stmt = select(NdcRecord)
            if start_date:
                stmt = stmt.where(NdcRecord.last_working_date >= start_date)
            if end_date:
                stmt = stmt.where(NdcRecord.last_working_date <= end_date)

            stmt = stmt.order_by(NdcRecord.ndc_initiated_date.desc())
            records_res = await db.execute(stmt)
            records = records_res.scalars().all()

            approvals_res = await db.execute(select(NdcApproval))
            all_approvals = approvals_res.scalars().all()
        except Exception as e:
            logger.error(f"Error in fetch_common_records: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")

        # Group approvals by record id for fast lookup
        approvals_by_record = {}
        for approval in all_approvals:
            if approval.ndc_record_id not in approvals_by_record:
                approvals_by_record[approval.ndc_record_id] = []
            approvals_by_record[approval.ndc_record_id].append(approval)

        result = []

        # Map stages to the specific properties client expects
        stage_key_map = {
            "RM": "rm",
            "IT": "it",
            "Abex": "abex",
            "Telecom": "telecom",
            "Store": "store",
            "Safety": "safety",
            "Administration": "administration",
            "Security": "security",
            "HR": "hr",
            "GCC HR": "gcc_hr",
            "Final Abex": "final_abex",
            "Business Specific": "business_specific",
            "Legatrix": "legatrix",
        }

        for record in records:
            record_approvals = approvals_by_record.get(record.id, [])

            # Derive gcc_initiate_date from GCC HR approval stage_started_at
            gcc_initiate = record.gcc_initiate_date
            if not gcc_initiate:
                for a in record_approvals:
                    if a.stage_name == "GCC HR" and a.stage_started_at:
                        gcc_initiate = (
                            a.stage_started_at.date()
                            if hasattr(a.stage_started_at, "date")
                            else a.stage_started_at
                        )
                        break
            # Fallback to ndc_initiated_date if gcc_initiate_date is still not available
            if not gcc_initiate:
                gcc_initiate = record.ndc_initiated_date

            # Check if an F&F document file exists on the server in the uploads folder
            fnf_doc_name = ""
            for ext in [".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".xls"]:
                possible_file = f"{record.person_number}{ext}"
                possible_path = BASE_DIR / "uploads" / possible_file
                if possible_path.exists():
                    fnf_doc_name = possible_file
                    break

            item = {
                "id": str(record.id),
                "ndc_assigned_date": (
                    record.ndc_assigned_date.strftime("%Y-%m-%d")
                    if record.ndc_assigned_date
                    else ""
                ),
                "person_number": str(record.person_number),
                "employee_name": record.employee_name or "",
                "department": record.department or record.department_reporting_name or "",
                "ndc_stage": record.ndc_stage or "",
                "resignation_date": (
                    record.resignation_date.strftime("%Y-%m-%d")
                    if record.resignation_date
                    else ""
                ),
                "last_working_date": (
                    record.last_working_date.strftime("%Y-%m-%d")
                    if record.last_working_date
                    else ""
                ),
                "ndc_initiated_date": (
                    record.ndc_initiated_date.strftime("%Y-%m-%d")
                    if record.ndc_initiated_date
                    else ""
                ),
                "ndc_completed_date": (
                    record.ndc_completed_date.strftime("%Y-%m-%d")
                    if record.ndc_completed_date
                    else ""
                ),
                "created_by": record.created_by or "",
                # F&F fields — derive fnf_status from booleans for backward compat
                "fnf_status": CommonService._derive_fnf_status(record),
                "fnf_document": fnf_doc_name,
                "fnf_action_date": "",
                "fnf_completed_date": (
                    record.fnf_completed_date.strftime("%Y-%m-%d")
                    if record.fnf_completed_date
                    else ""
                ),
                "is_fnf_completed": record.is_fnf_completed,
                "is_fnf_closed": record.is_fnf_closed,
                "is_fnf_revision": record.is_fnf_revision,
                "gcc_initiate_date": (
                    gcc_initiate.strftime("%Y-%m-%d") if gcc_initiate else ""
                ),
                "fnf_document_count": record.fnf_document_count,
                "fnf_revision_start_date": (
                    record.fnf_revision_start_date.strftime("%Y-%m-%d")
                    if record.fnf_revision_start_date
                    else ""
                ),
                "fnf_revision_completed_date": (
                    record.fnf_revision_completed_date.strftime("%Y-%m-%d")
                    if record.fnf_revision_completed_date
                    else ""
                ),
                "recovery_pending_dept": "",
                "recovery_amount": 0.0,
                "recovery_status": "",
                "open_text_notes": "",
            }

            for prefix in stage_key_map.values():
                item[f"{prefix}_approval_status"] = "Not Applicable"
                item[f"{prefix}_approver"] = ""
                item[f"{prefix}_approval_date"] = ""

            for approval in record_approvals:
                prefix = stage_key_map.get(approval.stage_name)
                if prefix:
                    status_mapped = ""
                    if approval.status == "PENDING":
                        status_mapped = "Pending"
                    elif approval.status == "IN_PROGRESS":
                        status_mapped = "In Progress"
                    elif approval.status == "COMPLETED":
                        status_mapped = "Completed"
                    elif approval.status == "NOT_APPLICABLE":
                        status_mapped = "Not Applicable"
                    else:
                        status_mapped = (
                            approval.status.capitalize()
                            if approval.status
                            else "Not Applicable"
                        )

                    item[f"{prefix}_approval_status"] = status_mapped
                    item[f"{prefix}_approver"] = approval.approver_name or ""
                    item[f"{prefix}_approval_date"] = (
                        approval.stage_completed_at.strftime("%Y-%m-%d")
                        if approval.stage_completed_at
                        else ""
                    )

            result.append(CommonNDCRecord(**item))
        return result


    @staticmethod
    def _derive_fnf_status(record: NdcRecord) -> str:
        """Derive a string F&F status from boolean fields for backward compatibility."""
        try:
            if record.is_fnf_completed:
                return "Done"
            if record.is_fnf_revision:
                return "Revision Required"
            # Eligible = NDC Completed AND GCC HR Completed (check ndc_stage only; GCC status checked separately)
            if record.ndc_stage == "NDC Completed":
                return "Open"
            return ""
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in _derive_fnf_status: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def update_fnf_status(
        record_id: int, body: FnfUpdateRequest, db: AsyncSession
    ) -> Optional[NdcRecord]:
        """Update F&F flags on a record and optionally propagate dates."""
        try:
            result = await db.execute(select(NdcRecord).where(NdcRecord.id == record_id))
            record = result.scalar_one_or_none()
            if not record:
                return None

            today = date.today()
            was_revision = getattr(record, "is_fnf_revision", False)

            if body.is_fnf_closed is not None:
                record.is_fnf_closed = body.is_fnf_closed
                if body.is_fnf_closed:
                    record.is_fnf_completed = True
                    if not record.fnf_completed_date:
                        record.fnf_completed_date = today
                    # Clear revision flag if marking closed
                    if record.is_fnf_revision or (record.fnf_revision_start_date and not record.fnf_revision_completed_date):
                        record.fnf_revision_completed_date = today
                    record.is_fnf_revision = False
                    if hasattr(record, "is_fnf_revision_email_sent"):
                        record.is_fnf_revision_email_sent = False
                    # Propagate department dates
                    await CommonService._propagate_department_dates(record.id, today, db)

            if body.is_fnf_completed is not None:
                record.is_fnf_completed = body.is_fnf_completed
                if body.is_fnf_completed:
                    if not record.fnf_completed_date:
                        record.fnf_completed_date = today
                    # Clear revision flag if marking completed
                    if record.is_fnf_revision or (record.fnf_revision_start_date and not record.fnf_revision_completed_date):
                        record.fnf_revision_completed_date = today
                    record.is_fnf_revision = False
                    if hasattr(record, "is_fnf_revision_email_sent"):
                        record.is_fnf_revision_email_sent = False
                    # Propagate department dates
                    await CommonService._propagate_department_dates(record.id, today, db)
                else:
                    record.fnf_completed_date = None
                    record.is_fnf_closed = False

            if body.is_fnf_revision is not None:
                record.is_fnf_revision = body.is_fnf_revision
                if body.is_fnf_revision:
                    # Clear completed and closed flags if marking revision
                    record.is_fnf_completed = False
                    record.is_fnf_closed = False
                    record.fnf_completed_date = None
                    record.fnf_revision_start_date = today
                    record.fnf_revision_completed_date = None
                    if not was_revision and hasattr(record, "is_fnf_revision_email_sent"):
                        record.is_fnf_revision_email_sent = False

            if body.fnf_document_count is not None:
                record.fnf_document_count = body.fnf_document_count

            await db.commit()
            return record
        except Exception as e:
            logger.error(f"Error in update_fnf_status: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")


    @staticmethod
    async def _propagate_department_dates(
        record_id: int, fnf_completed_date: date, db: AsyncSession
    ):
        """Auto-fill blank department stage_completed_at dates when F&F is completed."""
        try:
            record_res = await db.execute(select(NdcRecord).where(NdcRecord.id == record_id))
            record = record_res.scalar_one_or_none()

            approvals_res = await db.execute(
                select(NdcApproval).where(NdcApproval.ndc_record_id == record_id)
            )
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
                "Legatrix": "legatrix_approval_date",
            }
            for approval in approvals_res.scalars().all():
                # Only fill if both status and date are blank/null
                status_blank = approval.status is None or approval.status == ""
                date_blank = approval.stage_completed_at is None
                if status_blank and date_blank:
                    approval.stage_completed_at = fnf_completed_date
                    if record:
                        col_name = col_name_map.get(approval.stage_name)
                        if col_name and getattr(record, col_name) is None:
                            setattr(record, col_name, fnf_completed_date)
        except Exception as e:
            logger.error(f"Error in _propagate_department_dates: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")

