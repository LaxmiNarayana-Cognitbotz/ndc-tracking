from fastapi import HTTPException
import asyncio
import datetime
import logging
import os

from app.modules.email.service import EmailService

logger = logging.getLogger(__name__)

async def email_automation_loop():
    """
    Background polling loop that triggers consolidated daily emails and tomorrow alerts at 10:00 AM.
    """
    try:
        enabled = os.getenv("EMAIL_AUTOMATION_BACKGROUND_POLL", "true").lower() == "true"
        if not enabled:
            logger.info("Email automation background sync is disabled (EMAIL_AUTOMATION_BACKGROUND_POLL=false).")
            return

        logger.info("Starting Daily Email Automation scheduler. Triggers daily at 10:00 AM.")

        # Store the last successfully triggered date
        last_trigger_date = None

        while True:
            try:
                now = datetime.datetime.now()
                time_str = now.strftime("%H:%M")
                date_str = now.strftime("%Y-%m-%d")

                if time_str == "10:00" and date_str != last_trigger_date:
                    logger.info("Background Email Scheduler: 10:00 AM reached. Initiating daily email jobs...")
                    last_trigger_date = date_str

                    await EmailService.run_10am_job()
                    await asyncio.sleep(5)
                    await EmailService.run_tomorrow_alert_job()
                    logger.info("Background Email Scheduler: Daily email jobs completed successfully.")

            except asyncio.CancelledError:
                logger.info("Background Email Scheduler task cancelled.")
                break
            except Exception as e:
                logger.exception(f"Background Email Scheduler: Unexpected error: {e}")

            # Check every 30 seconds
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                logger.info("Background Email Scheduler sleep cancelled.")
                break
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in email_automation_loop: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')
