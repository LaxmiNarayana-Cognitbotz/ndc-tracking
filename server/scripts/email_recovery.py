# email_recovery.py
# -----------------
# Run this script manually after a server/VM restart to re-send all emails
# that the background automation missed.
#
# Execution order (same as application logic):
#   1. 10am job  — RM pending notifications + all department clearance emails
#                  (resolves emails from rm_email_configuration + email_recipient tables)
#   2. Tomorrow   — IT & Security alerts for employees whose last working date is tomorrow
#   3. F&F        — F&F settlement emails to employees from employee_email_master
#                  (only sent if F&F is completed + document exists + not already sent)
#
# Usage:
#   python scripts/email_recovery.py                   # Send everything missed (recommended after restart)
#   python scripts/email_recovery.py --dry-run         # Preview only — no emails sent, no DB changes
#   python scripts/email_recovery.py --job fnf         # Only F&F settlement emails
#   python scripts/email_recovery.py --job 10am        # Only RM + department pending emails
#   python scripts/email_recovery.py --job tomorrow    # Only IT & Security tomorrow alerts

import argparse
import asyncio
import io
import logging
import sys
from datetime import datetime
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_ROOT))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("email_recovery")

from sqlalchemy import select
from app.models.employee_email_master import EmployeeEmailMaster
from app.models.ndc_record import NdcRecord
from app.modules.email.service import EmailService
from config.database import BASE_DIR, async_session


def parse_args():
    parser = argparse.ArgumentParser(description="NDC Email Recovery Script")
    parser.add_argument(
        "--job",
        default="all",
        choices=["all", "fnf", "10am", "tomorrow"],
        help="Which job to run (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview only — no emails sent, no DB changes",
    )
    return parser.parse_args()


async def recover_fnf_emails(dry_run: bool):
    print("\n" + "-" * 60)
    print("JOB: F&F Settlement Emails")
    print("-" * 60)

    async with async_session() as db:
        res = await db.execute(
            select(NdcRecord).where(
                NdcRecord.is_fnf_completed == True,
                NdcRecord.is_fnf_email_sent == False,
            )
        )
        records = res.scalars().all()

        if not records:
            logger.info("No pending F&F settlement emails found. All caught up.")
            return

        logger.info("Found %d record(s) with unsent F&F emails.", len(records))

        sendable = []

        for record in records:
            person_number = record.person_number
            if not person_number:
                continue

            has_doc = bool(record.fnf_document_count and record.fnf_document_count > 0)
            if not has_doc:
                for ext in [".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".xls"]:
                    if (BASE_DIR / "uploads" / f"{person_number}{ext}").exists():
                        has_doc = True
                        break

            emp_email = None
            try:
                emp_email = (
                    await db.execute(
                        select(EmployeeEmailMaster.email).where(
                            EmployeeEmailMaster.person_number == int(person_number)
                        )
                    )
                ).scalar_one_or_none()
            except Exception as e:
                logger.warning("Could not look up email for %s: %s", person_number, e)

            if not has_doc:
                logger.info("Skipping %s (%s) — no document found.", record.employee_name, person_number)
                continue
            if not emp_email:
                logger.info("Skipping %s (%s) — not in employee_email_master.", record.employee_name, person_number)
                continue

            sendable.append((record, emp_email))

        if not sendable:
            logger.info("Nothing to send.")
            return

        logger.info("Records to send (%d):", len(sendable))
        for rec, email in sendable:
            logger.info("  %s (%s) -> %s", rec.employee_name, rec.person_number, email)

        if dry_run:
            logger.info("[DRY RUN] No emails sent.")
            return

        sent, failed = 0, 0
        for record, emp_email in sendable:
            try:
                logger.info("Sending to %s for %s (%s)...", emp_email, record.employee_name, record.person_number)
                outcome = await EmailService.send_fnf_email_service(
                    record_id=record.id,
                    email_to=emp_email,
                    db=db,
                )
                if outcome.get("success"):
                    logger.info("Sent successfully.")
                    sent += 1
                else:
                    logger.error("Failed: %s", outcome.get("message"))
                    failed += 1
            except Exception as e:
                logger.exception("Exception for %s: %s", record.person_number, e)
                failed += 1
            await asyncio.sleep(2)

        logger.info("F&F Email Recovery done — Sent: %d | Failed: %d", sent, failed)


async def recover_10am_job(dry_run: bool):
    print("\n" + "-" * 60)
    print("JOB: 10am Emails — RM + Departments")
    print("-" * 60)

    if dry_run:
        logger.info("[DRY RUN] Skipping 10am job. Remove --dry-run to send.")
        return

    logger.info("Running EmailService.run_10am_job()...")
    try:
        await EmailService.run_10am_job()
        logger.info("10am job completed.")
    except Exception as e:
        logger.exception("10am job failed: %s", e)


async def recover_tomorrow_alerts(dry_run: bool):
    print("\n" + "-" * 60)
    print("JOB: Tomorrow IT & Security Alerts")
    print("-" * 60)

    if dry_run:
        logger.info("[DRY RUN] Skipping tomorrow alerts. Remove --dry-run to send.")
        return

    logger.info("Running EmailService.run_tomorrow_alert_job()...")
    try:
        await EmailService.run_tomorrow_alert_job()
        logger.info("Tomorrow alert job completed.")
    except Exception as e:
        logger.exception("Tomorrow alert job failed: %s", e)


async def main():
    args = parse_args()

    print("\n" + "=" * 60)
    print("NDC TRACKING — EMAIL RECOVERY SCRIPT")
    print("=" * 60)
    print("Time :", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("Job  :", args.job)
    print("Mode :", "DRY RUN" if args.dry_run else "LIVE")
    print("=" * 60)

    if args.job in ("all", "10am"):
        await recover_10am_job(dry_run=args.dry_run)

    if args.job in ("all", "tomorrow"):
        await asyncio.sleep(2)
        await recover_tomorrow_alerts(dry_run=args.dry_run)

    if args.job in ("all", "fnf"):
        await asyncio.sleep(2)
        await recover_fnf_emails(dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
