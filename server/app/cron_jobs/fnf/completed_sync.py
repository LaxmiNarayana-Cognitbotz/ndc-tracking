from fastapi import HTTPException
import asyncio
import logging
import os

from app.helpers.ff.sharepoint_sync_service import SharePointSyncService
from app.modules.email.service import EmailService
from config.database import async_session

logger = logging.getLogger(__name__)

async def fnf_completed_sync_loop():
    """
    Background polling loop to sync F&F completed status from SharePoint every 30 minutes.
    """
    try:
        enabled = os.getenv("SHAREPOINT_SYNC_BACKGROUND_POLL", "true").lower() == "true"
        if not enabled:
            logger.info("F&F SharePoint background sync is disabled (SHAREPOINT_SYNC_BACKGROUND_POLL=false).")
            return

        logger.info("Starting F&F SharePoint completed sync scheduler. Triggers every 30 minutes.")
        sync_service = SharePointSyncService()
    
        while True:
            try:
                logger.info("Background F&F Scheduler: Initiating sync...")
                async with async_session() as db:
                    fnf_result = await sync_service.sync_fnf_completed_records(db)
                    try:
                        await EmailService.send_auto_fnf_emails(db)
                    except Exception as ex:
                        logger.exception(f"Background F&F Scheduler: Error during auto email sending: {ex}")
                
                if fnf_result["records_updated"] > 0 or fnf_result.get("records_reverted", 0) > 0:
                    logger.info(f"Background F&F Scheduler: Successfully synced F&F status - Completed: {fnf_result['records_updated']}, Reverted: {fnf_result.get('records_reverted', 0)}.")
                elif fnf_result["status"] == "failed":
                    logger.error(f"Background F&F Scheduler: Sync failed. Errors: {fnf_result['errors']}")
                else:
                    logger.info("Background F&F Scheduler: No F&F status changes detected.")
                
            except asyncio.CancelledError:
                logger.info("Background F&F Scheduler task cancelled.")
                break
            except Exception as e:
                logger.exception(f"Background F&F Scheduler: Error during sync: {e}")
            
            # Sleep for 30 minutes (30 * 60 = 1800 seconds)
            try:
                await asyncio.sleep(1800)
            except asyncio.CancelledError:
                logger.info("Background F&F Scheduler sleep cancelled.")
                break
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in fnf_completed_sync_loop: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')
