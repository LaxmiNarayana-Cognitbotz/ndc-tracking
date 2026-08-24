from fastapi import HTTPException
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.cron_jobs.email.automation import email_automation_loop
from app.cron_jobs.fnf.closed_report import fnf_closed_report_loop
from app.cron_jobs.fnf.completed_sync import fnf_completed_sync_loop
from app.cron_jobs.sharepoint.sync import sharepoint_sync_loop
from config.database import async_session
from app.helpers.startup.service import StartupService


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with async_session() as session:
            await StartupService.run_migrations(session)
            await StartupService.seed_super_admins(session)
            await StartupService.seed_demo_admin(session)
            await session.commit()

        # Start the background tasks
        bg_task = asyncio.create_task(sharepoint_sync_loop())
        fnf_bg_task = asyncio.create_task(fnf_completed_sync_loop())
        fnf_closed_task = asyncio.create_task(fnf_closed_report_loop())
        email_task = asyncio.create_task(email_automation_loop())
    
        yield
    
        # Cancel the background tasks on shutdown
        bg_task.cancel()
        fnf_bg_task.cancel()
        fnf_closed_task.cancel()
        email_task.cancel()
        try:
            await bg_task
        except asyncio.CancelledError:
            pass
        try:
            await fnf_bg_task
        except asyncio.CancelledError:
            pass
        try:
            await fnf_closed_task
        except asyncio.CancelledError:
            pass
        try:
            await email_task
        except asyncio.CancelledError:
            pass
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in lifespan: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')
