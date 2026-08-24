from fastapi import HTTPException
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.rm_email_configuration import RmEmailCreate, RmEmailUpdate
from app.modules.rm_email.service import RMEmailService
from config.database import get_db

router = APIRouter(prefix="/api/v1", tags=["Reporting Manager Email Configurations"])


@router.post("/rm-email-configuration")
async def create_rm_email_configuration(config: RmEmailCreate, db: AsyncSession = Depends(get_db)):
    try:
        await RMEmailService.create_rm_email(config, db)
        return {"message": "RM added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/rm-email-configuration")
async def get_rm_email_configurations(page: int = 1, limit: int = 20, search: str = "", db: AsyncSession = Depends(get_db)):
    try:
        result = await RMEmailService.get_rm_emails_paginated(page, limit, search, db)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.post("/rm-email-configuration/import")
async def import_rm_email_configurations(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    try:
        result = await RMEmailService.import_rm_emails_excel(file, db)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/rm-email-configuration/sample")
async def download_sample():
    try:
        output = RMEmailService.generate_sample_excel()
        headers = {"Content-Disposition": 'attachment; filename="sample_rm_email_configuration.xlsx"'}
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.delete("/rm-email-configuration/{id}")
async def delete_rm_email_configuration(id: int, db: AsyncSession = Depends(get_db)):
    try:
        success = await RMEmailService.delete_rm_email(id, db)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RM email configuration not found")
        return {"message": "Record deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.put("/rm-email-configuration/{id}")
async def update_rm_email_configuration(id: int, config: RmEmailUpdate, db: AsyncSession = Depends(get_db)):
    try:
        updated = await RMEmailService.update_rm_email(id, config, db)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RM email configuration not found")
        return {"message": "RM updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")
