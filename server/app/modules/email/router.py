from fastapi import HTTPException
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.email import DelayedReminderRequest, EmailRecipientSchema, FnfEmailRequest
from app.helpers.email.recipient_service import EmailRecipientService
from app.modules.email.service import EmailService
from config.database import get_db

router = APIRouter(prefix="/api/v1", tags=["Email Notification Management"])


@router.get("/email-recipients", response_model=List[EmailRecipientSchema])
async def get_email_recipients(db: AsyncSession = Depends(get_db)):
    try:
        return await EmailRecipientService.get_all_recipients(db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.post("/email-recipients")
async def add_email_recipient(recipient: EmailRecipientSchema, db: AsyncSession = Depends(get_db)):
    try:
        return await EmailRecipientService.add_recipient(recipient, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.put("/email-recipients/{id}")
async def update_email_recipient(id: int, recipient: EmailRecipientSchema, db: AsyncSession = Depends(get_db)):
    try:
        return await EmailRecipientService.update_recipient(id, recipient, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.delete("/email-recipients/{id}")
async def delete_email_recipient(id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await EmailRecipientService.delete_recipient(id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.post("/send-delayed-reminder")
async def send_delayed_reminder_email(payload: DelayedReminderRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Send a reminder email for delayed/overdue cases (NDC or F&F)."""
    try:
        return await EmailRecipientService.prepare_and_send_delayed_reminder(payload.type, payload.email, background_tasks, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.post("/send-fnf-email")
async def send_fnf_email(payload: FnfEmailRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        outcome = await EmailService.send_fnf_email_service(payload.record_id, payload.email, db, background_tasks)
        if not outcome["success"]:
            status_code = outcome.get("status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
            raise HTTPException(status_code=status_code, detail=outcome["message"])
        return {"message": outcome["message"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")
