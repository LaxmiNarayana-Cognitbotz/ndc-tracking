from fastapi import HTTPException
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.employee_email_master import EmployeeEmailCreate, EmployeeEmailUpdate
from app.modules.employee_email.service import EmployeeEmailService
from config.database import get_db

router = APIRouter(prefix="/api/v1", tags=["Employee Email Master"])


@router.post("/employee-email-master")
async def create_employee_email_configuration(config: EmployeeEmailCreate, db: AsyncSession = Depends(get_db)):
    try:
        await EmployeeEmailService.create_employee_email(config, db)
        return {"message": "Employee added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/employee-email-master")
async def get_employee_email_configurations(page: int = 1, limit: int = 20, search: str = "", db: AsyncSession = Depends(get_db)):
    try:
        result = await EmployeeEmailService.get_employee_emails_paginated(page, limit, search, db)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.post("/employee-email-master/import")
async def import_employee_email_configurations(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    try:
        result = await EmployeeEmailService.import_employee_emails_excel(file, db)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/employee-email-master/sample")
async def download_sample():
    try:
        output = EmployeeEmailService.generate_sample_excel()
        headers = {"Content-Disposition": 'attachment; filename="sample_employee_email_master.xlsx"'}
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.delete("/employee-email-master/{id}")
async def delete_employee_email_configuration(id: int, db: AsyncSession = Depends(get_db)):
    try:
        success = await EmployeeEmailService.delete_employee_email(id, db)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee email master record not found")
        return {"message": "Record deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.put("/employee-email-master/{id}")
async def update_employee_email_configuration(id: int, config: EmployeeEmailUpdate, db: AsyncSession = Depends(get_db)):
    try:
        updated = await EmployeeEmailService.update_employee_email(id, config, db)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee email master record not found")
        return {"message": "Employee updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")
