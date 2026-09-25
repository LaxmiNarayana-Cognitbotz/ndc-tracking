# -*- coding: utf-8 -*-
"""
update_fnf_completed_dates.py
=============================
Updates `fnf_completed_date` and `is_fnf_completed` for:
    30211073 - 31 Aug 2026
    30215259 - 03 Sept 2026
    30200484 - 20 Sept 2026
    30170168 - 14 Aug 2026
    30211499 - 19 Aug 2026

Usage:
    # Preview only (no DB changes):
    python scripts/update_fnf_completed_dates.py --dry-run

    # Write to DB:
    python scripts/update_fnf_completed_dates.py
"""

import asyncio
import datetime
import io
import sys
from pathlib import Path

# Add server root to path
SERVER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_ROOT))

# Force UTF-8 output on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from sqlalchemy import select
from config.database import async_session
from app.models.ndc_record import NdcRecord

FNF_DATA = {
    30211073: {"name": "Akash Raja",              "date": "2026-08-31"},
    30215259: {"name": "Ravindra Singh",          "date": "2026-09-03"},
    30200484: {"name": "Vijay Singh",             "date": "2026-09-20"},
    30170168: {"name": "Shatrughan Kumar Singh",  "date": "2026-08-14"},
    30211499: {"name": "Chandramani Pal",         "date": "2026-08-19"},
}


async def run_update(dry_run: bool = False):
    print()
    print("=" * 72)
    print(" F&F Completed Date Update Script")
    if dry_run:
        print(" MODE: DRY RUN — No changes will be written to the database")
    else:
        print(" MODE: LIVE — Changes WILL be written to the database")
    print("=" * 72)
    print(f" Total records: {len(FNF_DATA)}")
    print()

    person_numbers = list(FNF_DATA.keys())

    # 1. Fetch DB records
    print("Fetching records from database...")
    async with async_session() as db:
        res = await db.execute(
            select(NdcRecord).where(NdcRecord.person_number.in_(person_numbers))
        )
        records = res.scalars().all()
        db_map = {r.person_number: r for r in records}

    print(f"  Matched {len(db_map)} of {len(FNF_DATA)} records in database.")
    print()

    # 2. Plan updates
    to_update = []
    not_in_db = []

    for pn, info in FNF_DATA.items():
        if pn not in db_map:
            not_in_db.append((pn, info))
            continue
        record = db_map[pn]
        new_date = datetime.date.fromisoformat(info["date"])
        to_update.append((record, new_date, info))

    # 3. Print change table
    print("-" * 72)
    print(f"{'Person No':<12} {'Name':<28} {'Old Date':<12} {'New Date':<12} Status")
    print("-" * 72)

    for record, new_date, info in to_update:
        old = str(record.fnf_completed_date) if record.fnf_completed_date else "NULL"
        print(
            f"{record.person_number:<12} "
            f"{record.employee_name:<28} "
            f"{old:<12} "
            f"{str(new_date):<12} "
            f"[UPDATE]"
        )

    for pn, info in not_in_db:
        print(f"{pn:<12} {info['name']:<28} {'—':<12} {'—':<12} [SKIP — not found in DB]")

    print("-" * 72)
    print()

    if not to_update:
        print("Nothing to update. Exiting.")
        return

    # 4. Apply updates
    if dry_run:
        print("[DRY RUN] No changes written to the database.")
        return

    print(f"Applying {len(to_update)} update(s) to the database...")
    async with async_session() as db:
        try:
            res = await db.execute(
                select(NdcRecord).where(NdcRecord.person_number.in_(person_numbers))
            )
            db_records = {r.person_number: r for r in res.scalars().all()}

            updated_count = 0
            for record_ref, new_date, info in to_update:
                pn = record_ref.person_number
                record = db_records.get(pn)
                if record is None:
                    continue

                record.fnf_completed_date = new_date
                record.is_fnf_completed = True
                updated_count += 1

            await db.commit()
            print(f"  OK: Successfully committed {updated_count} record(s).")

        except Exception as e:
            await db.rollback()
            print(f"  ERROR: Transaction rolled back: {e}")
            raise

    print()
    print("Done.")
    print("=" * 72)


def main():
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run_update(dry_run=dry_run))


if __name__ == "__main__":
    main()
