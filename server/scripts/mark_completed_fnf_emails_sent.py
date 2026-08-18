# -*- coding: utf-8 -*-
"""
mark_completed_fnf_emails_sent.py
==================================
Updates `is_fnf_email_sent = True` (and optionally `is_fnf_revision_email_sent = True`)
for all existing/historical completed or closed F&F employee records in the database.

Purpose:
--------
When automated F&F email sending (`send_auto_fnf_emails`) is started, the background
engine scans for records matching:
    WHERE is_fnf_completed = True AND is_fnf_email_sent = False

By running this script prior to starting automation, all existing/historical completed
employees are marked as `is_fnf_email_sent = True`. Consequently:
  1. Historical completed employees will NOT receive redundant/retroactive emails.
  2. Future / newly completed F&F employees will have `is_fnf_email_sent = False` by
     default, so the automation engine will smoothly pick them up and send their emails.

Usage:
------
# 1. Preview changes (Dry Run - No database changes):
python scripts/mark_completed_fnf_emails_sent.py --dry-run
(or simply: python scripts/mark_completed_fnf_emails_sent.py)

# 2. Apply and commit changes to the database:
python scripts/mark_completed_fnf_emails_sent.py --apply

# 3. Apply with cutoff date (e.g. only records completed on or before 2026-08-18):
python scripts/mark_completed_fnf_emails_sent.py --apply --cutoff-date 2026-08-18

# 4. Target specific person numbers:
python scripts/mark_completed_fnf_emails_sent.py --apply --person-numbers 30022156,30130741

# 5. Also mark revision email sent flag:
python scripts/mark_completed_fnf_emails_sent.py --apply --include-revisions
"""

import argparse
import asyncio
import io
import os
import sys
from datetime import date, datetime
from pathlib import Path

# Add server root to sys.path
SERVER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_ROOT))

# Force UTF-8 output on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from sqlalchemy import select, or_, and_, func
from config.database import async_session
from app.models.ndc_record import NdcRecord


def parse_args():
    parser = argparse.ArgumentParser(
        description="Mark completed/closed F&F employee records as is_fnf_email_sent = True to prevent retroactive email blasts."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Commit changes to the database. (Default is dry-run preview if omitted)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run in preview mode without modifying database records.",
    )
    parser.add_argument(
        "--cutoff-date",
        type=str,
        default=None,
        help="Optional ISO cutoff date (YYYY-MM-DD). Only records with fnf_completed_date <= cutoff_date will be updated.",
    )
    parser.add_argument(
        "--person-numbers",
        type=str,
        default=None,
        help="Comma-separated list of person numbers to filter (e.g. '30022156,30130741').",
    )
    parser.add_argument(
        "--include-revisions",
        action="store_true",
        default=False,
        help="Also mark is_fnf_revision_email_sent = True for revision records.",
    )
    return parser.parse_args()


async def mark_emails_sent():
    args = parse_args()
    is_dry_run = not args.apply or args.dry_run

    print("=" * 80)
    print(" F&F EMAIL SENT STATUS UPDATE SCRIPT")
    print("=" * 80)
    print(f"Mode: {'[DRY RUN - PREVIEW ONLY]' if is_dry_run else '[APPLY - COMMITTING TO DATABASE]'}")
    if args.cutoff_date:
        print(f"Cutoff Date Filter: <= {args.cutoff_date}")
    if args.person_numbers:
        print(f"Person Numbers Filter: {args.person_numbers}")
    if args.include_revisions:
        print("Include Revisions: Yes (is_fnf_revision_email_sent will also be updated)")
    print("-" * 80)

    cutoff_d = None
    if args.cutoff_date:
        try:
            cutoff_d = datetime.strptime(args.cutoff_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            print(f"[ERROR] Invalid date format for --cutoff-date: '{args.cutoff_date}'. Expected YYYY-MM-DD.")
            sys.exit(1)

    target_person_numbers = None
    if args.person_numbers:
        try:
            target_person_numbers = [int(p.strip()) for p in args.person_numbers.split(",") if p.strip()]
        except ValueError:
            print(f"[ERROR] Invalid person number format in '{args.person_numbers}'. Must be comma-separated numbers.")
            sys.exit(1)

    async with async_session() as db:
        # Build base filter for completed or closed records where is_fnf_email_sent is False
        conditions = [
            or_(
                NdcRecord.is_fnf_completed == True,
                NdcRecord.is_fnf_closed == True,
                NdcRecord.fnf_completed_date.isnot(None),
            ),
            NdcRecord.is_fnf_email_sent == False,
        ]

        if cutoff_d:
            conditions.append(
                or_(
                    NdcRecord.fnf_completed_date <= cutoff_d,
                    and_(NdcRecord.fnf_completed_date.is_(None), NdcRecord.last_working_date <= cutoff_d)
                )
            )

        if target_person_numbers:
            conditions.append(NdcRecord.person_number.in_(target_person_numbers))

        stmt = select(NdcRecord).where(*conditions).order_by(NdcRecord.id)
        result = await db.execute(stmt)
        records_to_update = result.scalars().all()

        total_matching = len(records_to_update)

        # Also get total stats for context
        total_all = await db.scalar(select(func.count(NdcRecord.id)))
        total_completed = await db.scalar(select(func.count(NdcRecord.id)).where(
            or_(NdcRecord.is_fnf_completed == True, NdcRecord.is_fnf_closed == True)
        ))
        total_already_sent = await db.scalar(select(func.count(NdcRecord.id)).where(NdcRecord.is_fnf_email_sent == True))

        print(f"\n[DATABASE OVERVIEW]")
        print(f"  • Total NDC records in DB:                   {total_all}")
        print(f"  • Total F&F Completed / Closed records:     {total_completed}")
        print(f"  • Already marked with is_fnf_email_sent=True:{total_already_sent}")
        print(f"  • Unsent Completed/Closed records to update: {total_matching}")
        print("-" * 80)

        if total_matching == 0:
            print("\n[OK] No unsent completed records found matching the criteria.")
            print("All completed records already have is_fnf_email_sent = True.")
            print("=" * 80)
            return

        print(f"\n[RECORDS TO BE MARKED AS EMAIL SENT ({total_matching} total)]:")
        print(f"{'#':<4} | {'Person No':<12} | {'Employee Name':<28} | {'FnF Completed Date':<18} | {'Status':<12}")
        print("-" * 80)

        for idx, rec in enumerate(records_to_update, start=1):
            comp_date = rec.fnf_completed_date.strftime("%d-%b-%Y") if rec.fnf_completed_date else "—"
            status_desc = "Completed" if rec.is_fnf_completed else ("Closed" if rec.is_fnf_closed else "Done")
            print(f"{idx:<4} | {rec.person_number:<12} | {rec.employee_name[:26]:<28} | {comp_date:<18} | {status_desc:<12}")

        if is_dry_run:
            print("-" * 80)
            print(f"\n[DRY RUN SUMMARY]")
            print(f"  -> {total_matching} record(s) would be updated to is_fnf_email_sent = True.")
            print("  -> NO changes were made to the database.")
            print("\nTo apply and commit these changes, run with --apply:")
            print("  python scripts/mark_completed_fnf_emails_sent.py --apply")
            print("=" * 80)
            return

        # APPLY changes
        updated_count = 0
        revision_updated_count = 0
        for rec in records_to_update:
            rec.is_fnf_email_sent = True
            if args.include_revisions and (rec.is_fnf_revision or rec.is_fnf_revision_email_sent is False):
                rec.is_fnf_revision_email_sent = True
                revision_updated_count += 1
            updated_count += 1

        await db.commit()

        print("-" * 80)
        print(f"\n[SUCCESS] Successfully updated {updated_count} record(s) in the database!")
        print(f"  • is_fnf_email_sent set to True:           {updated_count}")
        if args.include_revisions:
            print(f"  • is_fnf_revision_email_sent set to True: {revision_updated_count}")
        print("\nWhen automated email sending starts:")
        print(f"  ✓ These {updated_count} historical/completed employees will be safely SKIPPED.")
        print("  ✓ Only newly completed F&F employees (is_fnf_email_sent=False) will receive automated emails.")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(mark_emails_sent())
