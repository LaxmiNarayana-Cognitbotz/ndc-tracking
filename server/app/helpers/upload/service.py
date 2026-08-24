import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers.upload.ingest_service import IngestService


class UploadService:
    @staticmethod
    async def handle_ndc_upload(file: UploadFile, db: AsyncSession) -> dict:
        """Handle the upload and ingestion of an NDC Excel file.
        
        Validates file type, writes to temp file, processes via ingest_service,
        and cleans up the temp file.
        """
        try:
            if not file.filename.endswith((".xlsx", ".xlsb", ".xls")):
                raise HTTPException(status_code=400, detail="Invalid file type. Only Excel files are supported.")
            
            temp_path = None
            try:
                # Create a temporary file to hold the uploaded content
                with NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
                    content = await file.read()
                    tmp.write(content)
                    temp_path = tmp.name

                # Process the file
                result = await IngestService.ingest_excel_file(
                    file_path=temp_path,
                    file_name=file.filename,
                    uploaded_by="manual_api_upload",
                    db=db,
                    source_type="manual"
                )
            
                if result["status"] == "failed":
                    raise HTTPException(status_code=400, detail={"message": "Ingestion failed", "errors": result["errors"]})
                
                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")
            finally:
                # Clean up the temp file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in handle_ndc_upload: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')
