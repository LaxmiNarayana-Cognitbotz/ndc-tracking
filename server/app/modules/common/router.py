from fastapi import HTTPException
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.common import CommonNDCRecord, FnfUpdateRequest
from app.helpers.upload.service import UploadService
from app.models.email_recipient import EmailRecipient
from app.modules.common.service import CommonService
from app.modules.email.service import EmailService
from config.database import get_db

router = APIRouter(prefix="/api/v1", tags=["Exit Clearance & Settlement Operations"])


@router.get("/ndc-records", response_model=List[CommonNDCRecord])
async def get_all_ndc_records_for_common(db: AsyncSession = Depends(get_db), start_date: Optional[date] = Query(None), end_date: Optional[date] = Query(None)):
    try:
        return await CommonService.fetch_common_records(db, start_date, end_date)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/fnf-records", response_model=List[CommonNDCRecord])
async def get_all_fnf_records_for_common(db: AsyncSession = Depends(get_db)):
    try:
        return await CommonService.fetch_common_records(db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/analytics-records", response_model=List[CommonNDCRecord])
async def get_all_analytics_records_for_common(db: AsyncSession = Depends(get_db)):
    try:
        return await CommonService.fetch_common_records(db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.put("/ndc-records/{record_id}")
async def update_fnf_status_route(record_id: int, body: FnfUpdateRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Update F&F status for a record. Triggers department date propagation on completion."""
    try:
        record = await CommonService.update_fnf_status(record_id, body, db)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

        # Send instant email to F&F Team when revision is marked with a comment
        if body.is_fnf_revision and body.fnf_revision_comment:
            try:
                # Look up all F&F Team recipients from email_recipients table
                from config.database import async_session
                from sqlalchemy import func
                ff_recipients: list[str] = []
                async with async_session() as session:
                    result = await session.execute(
                        select(EmailRecipient).where(
                            func.lower(func.trim(EmailRecipient.department)).in_(["f&f team", "fnf team", "f&f", "fnf"])
                        )
                    )
                    rows = result.scalars().all()
                    for r in rows:
                        if r.email:
                            for addr in r.email.replace(";", ",").split(","):
                                clean = addr.strip()
                                if clean and clean not in ff_recipients:
                                    ff_recipients.append(clean)

                # Fallback to environment variables if no DB recipient configured
                if not ff_recipients:
                    import os
                    env_fallback = os.getenv("FNF_EMAIL_RECIPIENT") or os.getenv("EMAIL_RECIPIENT")
                    if env_fallback:
                        for addr in env_fallback.replace(";", ",").split(","):
                            clean = addr.strip()
                            if clean and clean not in ff_recipients:
                                ff_recipients.append(clean)

                if ff_recipients:
                    background_tasks.add_task(
                        EmailService.send_fnf_revision_comment_email,
                        record,
                        body.fnf_revision_comment,
                        ff_recipients
                    )
                    # Mark as email sent so the daily 10 AM cron won't re-send
                    async with async_session() as mark_session:
                        from app.models.ndc_record import NdcRecord
                        stmt = select(NdcRecord).where(NdcRecord.id == record_id)
                        db_res = await mark_session.execute(stmt)
                        db_rec = db_res.scalar_one_or_none()
                        if db_rec:
                            db_rec.is_fnf_revision_email_sent = True
                            await mark_session.commit()
                else:
                    import logging
                    logging.warning(
                        f"F&F Team email recipient is not configured (checked 'email_recipients' table and EMAIL_RECIPIENT env). "
                        f"Skipping revision comment email for record ID {record_id} ({getattr(record, 'person_number', 'N/A')})."
                    )
            except Exception as email_err:
                import logging
                logging.warning(f"Could not queue F&F revision comment email: {email_err}")

        return {"id": record_id, "message": "Record updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")

@router.post("/ndc-records/upload")
async def upload_ndc_records(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Manually upload an Excel file for ingestion."""
    try:
        return await UploadService.handle_ndc_upload(file, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")
