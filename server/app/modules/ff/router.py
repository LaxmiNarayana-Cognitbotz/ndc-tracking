import logging

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse

from app.helpers.ff.sharepoint_service import SharePointService, get_httpx_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ff", tags=["Settlement Documents (SharePoint)"])

# Create SharePoint Service instance
sharepoint_service = SharePointService()


@router.get("/download/{person_number}")
async def download_ff_document(person_number: str):
    """
    Downloads the F&F document for a given employee from SharePoint.
    If no file exists, returns 404.
    If multiple files exist, streams a zip archive.
    """
    try:
        logger.info(f"Received SharePoint document download request for person: {person_number}")
    
        async with get_httpx_client() as client:
            try:
                result = await sharepoint_service.download_employee_documents(client, person_number)
                if not result:
                    logger.warning(f"No files found for person: {person_number} in SharePoint.")
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
                
                if result["type"] == "redirect":
                    return RedirectResponse(url=result["url"])
                
                stream = result["stream"]
                filename = result["filename"]
                mime_type = result["mime_type"]
            
                logger.info(f"Successfully located file '{filename}' for person {person_number}. Initiating stream.")
            
                headers = {
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Access-Control-Expose-Headers": "Content-Disposition"  # Allows Axios to access the filename header
                }
            
                return StreamingResponse(stream, media_type=mime_type, headers=headers)
            
            except Exception as e:
                logger.exception(f"SharePoint download failed for person {person_number} due to exception: {str(e)}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"SharePoint server error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in download_ff_document: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')
