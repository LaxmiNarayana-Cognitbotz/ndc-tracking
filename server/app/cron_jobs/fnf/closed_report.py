from fastapi import HTTPException
import asyncio
import datetime
import logging
import os

from app.helpers.ff.sharepoint_sync_service import SharePointSyncService
from config.database import async_session

logger = logging.getLogger(__name__)

async def fnf_closed_report_loop():
    """
    Background polling loop that generates a FNF-Closed Excel report and uploads
    it to SharePoint at the same daily times as the SharePoint file-sync loop
    (controlled by SHAREPOINT_SYNC_SCHEDULED_TIMES env var).
    """
    try:
        enabled = os.getenv("SHAREPOINT_SYNC_BACKGROUND_POLL", "true").lower() == "true"
        if not enabled:
            logger.info("FNF Closed Report scheduler is disabled (SHAREPOINT_SYNC_BACKGROUND_POLL=false).")
            return

        # Re-use the same scheduled times as the main SharePoint sync
        times_str = os.getenv("SHAREPOINT_SYNC_SCHEDULED_TIMES", "10:10,13:10,16:10,19:10")
        scheduled_times = {t.strip() for t in times_str.split(",") if t.strip()}
        logger.info(
            f"Starting FNF Closed Report scheduler. Triggers daily at: {', '.join(sorted(scheduled_times))}"
        )

        sync_service = SharePointSyncService()
        last_trigger_key = None

        while True:
            try:
                now = datetime.datetime.now()
                time_str = now.strftime("%H:%M")
                date_str = now.strftime("%Y-%m-%d")
                current_trigger_key = f"{date_str}_{time_str}"

                if time_str in scheduled_times and current_trigger_key != last_trigger_key:
                    logger.info(
                        f"FNF Closed Report Scheduler: Time {time_str} reached. Generating & uploading report..."
                    )
                    last_trigger_key = current_trigger_key

                    async with async_session() as db:
                        result = await sync_service.generate_and_upload_fnf_closed_report(db)

                    if result["status"] == "success":
                        logger.info(
                            f"FNF Closed Report Scheduler: Report '{result['uploaded_file_name']}' uploaded "
                            f"with {result['records_exported']} record(s)."
                        )
                    else:
                        logger.error(
                            f"FNF Closed Report Scheduler: Report generation/upload failed. "
                            f"Errors: {result['errors']}"
                        )

            except asyncio.CancelledError:
                logger.info("FNF Closed Report Scheduler task cancelled.")
                break
            except Exception as e:
                logger.exception(f"FNF Closed Report Scheduler: Unexpected error: {e}")

            # Check every 30 seconds (same cadence as the main sync loop)
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                logger.info("FNF Closed Report Scheduler sleep cancelled.")
                break
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in fnf_closed_report_loop: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')
