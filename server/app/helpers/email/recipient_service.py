from fastapi import HTTPException
from datetime import date
from typing import List

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.dto.email import EmailRecipientSchema
from app.models.email_recipient import EmailRecipient
from app.models.ndc_record import NdcRecord
from app.modules.email.service import EmailService

logger = logging.getLogger(__name__)

class EmailRecipientService:
    @staticmethod
    async def get_all_recipients(db: AsyncSession) -> List[EmailRecipientSchema]:
        """Fetch all email recipients."""
        try:
            res = await db.execute(select(EmailRecipient))
            records = res.scalars().all()
            return [
                EmailRecipientSchema(id=str(r.id), name=r.name, email=r.email, department=r.department, role=r.role or "")
                for r in records
            ]
        except Exception as e:
            logger.error(f"Error in get_all_recipients: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")

    @staticmethod
    async def add_recipient(recipient: EmailRecipientSchema, db: AsyncSession) -> dict:
        """Add a new email recipient with duplicate check."""
        try:
            # Duplicate email check
            existing = await db.execute(
                select(EmailRecipient).where(
                    EmailRecipient.email == recipient.email.strip().lower()
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A recipient with this email already exists.")

            new_rec = EmailRecipient(name=recipient.name, email=recipient.email.strip().lower(), department=recipient.department, role=recipient.role)
            db.add(new_rec)
            await db.commit()
            return {"message": "Recipient added successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in add_recipient: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")

    @staticmethod
    async def update_recipient(id: int, recipient: EmailRecipientSchema, db: AsyncSession) -> dict:
        """Update an existing email recipient with duplicate check."""
        try:
            res = await db.execute(select(EmailRecipient).where(EmailRecipient.id == id))
            rec = res.scalar_one_or_none()
            if not rec:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

            # Duplicate email check – exclude the current record from the check
            dup = await db.execute(
                select(EmailRecipient).where(
                    EmailRecipient.email == recipient.email.strip().lower(),
                    EmailRecipient.id != id,
                )
            )
            if dup.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Another recipient with this email already exists.")

            rec.name = recipient.name
            rec.email = recipient.email.strip().lower()
            rec.department = recipient.department
            rec.role = recipient.role
            await db.commit()
            return {"message": "Recipient updated successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in update_recipient: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")

    @staticmethod
    async def delete_recipient(id: int, db: AsyncSession) -> dict:
        """Delete an email recipient by ID."""
        try:
            res = await db.execute(select(EmailRecipient).where(EmailRecipient.id == id))
            rec = res.scalar_one_or_none()
            if rec:
                await db.delete(rec)
                await db.commit()
                return {"message": "Recipient deleted successfully"}
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in delete_recipient: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")

    @staticmethod
    async def prepare_and_send_delayed_reminder(
        payload_type: str | None,
        payload_email: str,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> dict:
        """Fetch delayed/overdue records, sort them, and dispatch reminder email."""
        try:
            today = date.today()

            # Fetch records based on type
            if payload_type == "fnf_open":
                # NDC Completed, but F&F is not completed and not revision
                result = await db.execute(
                    select(NdcRecord).where(
                        NdcRecord.ndc_stage == "NDC Completed",
                        NdcRecord.is_fnf_completed == False,
                        NdcRecord.is_fnf_revision == False,
                    )
                )
                records = result.scalars().all()
                sorted_records = sorted(
                    records,
                    key=lambda r: r.last_working_date or date.min,
                    reverse=True,
                )
            elif payload_type == "fnf_revision":
                # NDC Completed, but F&F needs revision
                result = await db.execute(
                    select(NdcRecord).where(
                        NdcRecord.ndc_stage == "NDC Completed",
                        NdcRecord.is_fnf_revision == True,
                    )
                )
                records = result.scalars().all()
                sorted_records = sorted(
                    records,
                    key=lambda r: r.last_working_date or date.min,
                    reverse=True,
                )
            elif payload_type == "fnf_delayed":
                # NDC Completed, but F&F is not completed and past last_working_date
                result = await db.execute(
                    select(NdcRecord).where(
                        NdcRecord.ndc_stage == "NDC Completed",
                        NdcRecord.is_fnf_completed == False,
                        NdcRecord.last_working_date < today,
                        NdcRecord.last_working_date.isnot(None),
                    )
                )
                records = result.scalars().all()
                sorted_records = sorted(
                    records,
                    key=lambda r: EmailService._days_delayed(r.last_working_date),
                    reverse=True,
                )
            else:
                # Default: ndc_delayed
                # Fetch overdue non-completed records delayed by > 30 days (Top Delayed Cases, matching dashboard card)
                result = await db.execute(
                    select(NdcRecord).where(
                        NdcRecord.ndc_stage != "NDC Completed",
                        NdcRecord.last_working_date < today,
                        NdcRecord.last_working_date.isnot(None),
                    )
                )
                records = result.scalars().all()
                top_delayed_records = [r for r in records if EmailService._days_delayed(r.last_working_date) > 30]
                sorted_records = sorted(
                    top_delayed_records,
                    key=lambda r: EmailService._days_delayed(r.last_working_date),
                    reverse=True,
                )

            selected_records = sorted_records

            records_payload = [
                {
                    "person_number": str(r.person_number),
                    "employee_name": r.employee_name,
                    "department": r.department or r.department_reporting_name or "—",
                    "last_working_date": r.last_working_date,
                    "days_delayed": EmailService._days_delayed(r.last_working_date),
                }
                for r in selected_records
            ]

            if background_tasks:
                background_tasks.add_task(
                    EmailService.send_delayed_reminder,
                    records_payload,
                    payload_email,
                    payload_type or "ndc_delayed",
                )
                outcome = {"success": True, "message": "Reminder email has been queued to run in the background."}
            else:
                outcome = await EmailService.send_delayed_reminder(
                    records=records_payload,
                    recipient=payload_email,
                    reminder_type=payload_type or "ndc_delayed",
                )

            if not outcome.get("success"):
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=outcome.get("message", "Failed to send email"))

            return {
                "records_sent": len(selected_records),
                "message": outcome["message"]
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in prepare_and_send_delayed_reminder: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")
