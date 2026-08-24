from fastapi import HTTPException
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Ensure the server directory is in sys.path so app imports work
utils_dir = Path(__file__).parent.resolve()
server_dir = utils_dir.parent.parent.resolve()
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

import logging

from app.modules.email.service import EmailService

# Configure basic logging to stdout for CLI visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def main():
    try:
        parser = argparse.ArgumentParser(description="NDC Tracking Email Notification CLI")
        parser.add_argument(
            "--job",
            type=str,
            default="both",
            choices=["10am", "tomorrow", "both"],
            help="Specify which email job to run: 10am (daily consolidated reports), tomorrow (IT & Security next-day alerts), or both (runs both sequentially)"
        )
        args = parser.parse_args()
    
        print(f"Executing email script at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    
        if args.job == "10am":
            await EmailService.run_10am_job()
        elif args.job == "tomorrow":
            await EmailService.run_tomorrow_alert_job()
        else:
            # Run both sequentially
            await EmailService.run_10am_job()
            # Brief pause between tasks to avoid SMTP throttling
            await asyncio.sleep(5)
            await EmailService.run_tomorrow_alert_job()
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in main: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')

if __name__ == "__main__":
    asyncio.run(main())
