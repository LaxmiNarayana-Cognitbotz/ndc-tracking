# -*- coding: utf-8 -*-
"""
update_fnf_revision_dates.py
============================
Updates `fnf_revision_start_date`, `fnf_revision_completed_date`, and `is_fnf_revision`
for all historical employee records where F&F Revisions took place:

1. Records with Date-2 and Date-3 (15 records):
   - Revision Start Date      = F&F DMS Date-2
   - Revision Completed Date  = F&F DMS Date-3
   - is_fnf_revision          = False

2. Records with Date-2 only (Date-3 is blank) (19 records):
   - Revision Start Date      = F&F DMS Date-1 (initial settlement / revision initiated)
   - Revision Completed Date  = F&F DMS Date-2 (revised settlement finalized)
   - is_fnf_revision          = False

Total records: 34

Usage:
------
    # Preview changes (dry run):
    python scripts/update_fnf_revision_dates.py --dry-run

    # Apply changes to database:
    python scripts/update_fnf_revision_dates.py
"""

import argparse
import asyncio
import datetime
import io
import sys
from pathlib import Path

# ── Add server root to path so config/app imports work ───────────────────────
SERVER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_ROOT))

# Force UTF-8 output on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from sqlalchemy import select
from config.database import async_session
from app.models.ndc_record import NdcRecord

# ── Embedded F&F Revision DMS Data ───────────────────────────────────────────
# Source: F_F Completed (2).xlsx | Total: 34 records
FNF_REVISION_DATA = {
    # ── Group 1: 2-Cycle Revisions (Date-2 Start -> Date-3 Completed) [15 records] ──
    30144704: {"name": "Jaswant Rajpurohit",         "start_date": "2026-05-18", "completed_date": "2026-05-28", "stage": "Date-2 -> Date-3"},
    30054376: {"name": "Dhaval Patel",               "start_date": "2026-05-28", "completed_date": "2026-05-29", "stage": "Date-2 -> Date-3"},
    30138821: {"name": "Rahul Kumar",                "start_date": "2026-05-28", "completed_date": "2026-05-29", "stage": "Date-2 -> Date-3"},
    30081658: {"name": "Kiran Kumar Pilli",          "start_date": "2026-05-28", "completed_date": "2026-05-29", "stage": "Date-2 -> Date-3"},
    30135759: {"name": "Pankaj Kumar",               "start_date": "2026-06-16", "completed_date": "2026-06-20", "stage": "Date-2 -> Date-3"},
    30182163: {"name": "Yogesh Tripathi",            "start_date": "2026-06-08", "completed_date": "2026-06-16", "stage": "Date-2 -> Date-3"},
    30140549: {"name": "Anand Jagdale",              "start_date": "2026-05-18", "completed_date": "2026-05-28", "stage": "Date-2 -> Date-3"},
    30124627: {"name": "Nasib Singh Kadian",         "start_date": "2026-05-19", "completed_date": "2026-06-07", "stage": "Date-2 -> Date-3"},
    30045476: {"name": "Mohammad Shamsuddin Ansari", "start_date": "2026-05-28", "completed_date": "2026-05-29", "stage": "Date-2 -> Date-3"},
    30143990: {"name": "Nitish Kumar",               "start_date": "2026-05-28", "completed_date": "2026-06-07", "stage": "Date-2 -> Date-3"},
    30073541: {"name": "Karan Hingrajia",            "start_date": "2026-05-28", "completed_date": "2026-06-07", "stage": "Date-2 -> Date-3"},
    30143608: {"name": "Romank Joshi",               "start_date": "2026-05-28", "completed_date": "2026-06-07", "stage": "Date-2 -> Date-3"},
    30020705: {"name": "Deepsingh Rajput",           "start_date": "2026-05-28", "completed_date": "2026-06-07", "stage": "Date-2 -> Date-3"},
    30143609: {"name": "G Pullapuraju",              "start_date": "2026-05-28", "completed_date": "2026-06-07", "stage": "Date-2 -> Date-3"},
    30151967: {"name": "Rishabh Saxena",             "start_date": "2026-04-09", "completed_date": "2026-05-08", "stage": "Date-2 -> Date-3"},

    # ── Group 2: 1-Cycle Revisions (Date-1 Start -> Date-2 Completed, Date-3 blank) [19 records] ──
    30133632: {"name": "Munandra Singh",             "start_date": "2026-07-09", "completed_date": "2026-07-18", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30125554: {"name": "Hardik Vadiya",              "start_date": "2026-06-16", "completed_date": "2026-06-20", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30067117: {"name": "Aditya Gupta",               "start_date": "2026-06-16", "completed_date": "2026-06-20", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30156114: {"name": "Manas Vashistha",            "start_date": "2026-06-16", "completed_date": "2026-06-20", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30115934: {"name": "Fulchand Ukey",              "start_date": "2026-04-30", "completed_date": "2026-05-29", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30017177: {"name": "Ankit Velani",               "start_date": "2026-04-21", "completed_date": "2026-06-07", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30142467: {"name": "Abhishek Pradhan",           "start_date": "2026-04-30", "completed_date": "2026-05-28", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30008672: {"name": "Alap Patel",                 "start_date": "2026-04-23", "completed_date": "2026-04-30", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30115935: {"name": "Kumararaja Sankaran",        "start_date": "2026-05-18", "completed_date": "2026-06-07", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30144882: {"name": "Sravan Kumar Vadlakonda",    "start_date": "2026-06-16", "completed_date": "2026-06-20", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30148752: {"name": "Debashis Mallick",           "start_date": "2026-04-30", "completed_date": "2026-05-29", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30055113: {"name": "Prakhar Bhardwaj",           "start_date": "2026-03-23", "completed_date": "2026-04-09", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30166392: {"name": "Ananth Raju",                "start_date": "2026-03-24", "completed_date": "2026-04-09", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30141689: {"name": "Anil Kumar",                 "start_date": "2026-04-30", "completed_date": "2026-05-28", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30018452: {"name": "Maunank Darji",              "start_date": "2026-05-08", "completed_date": "2026-05-28", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30140601: {"name": "Mukul Dabhi",                "start_date": "2026-03-24", "completed_date": "2026-04-02", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30128262: {"name": "Pradyuman Singh",            "start_date": "2026-03-24", "completed_date": "2026-04-09", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30132980: {"name": "LokeshKumar Sharma",         "start_date": "2026-03-24", "completed_date": "2026-04-09", "stage": "Date-1 -> Date-2 (D3 blank)"},
    30119040: {"name": "Kishan Meghnathi",           "start_date": "2026-03-24", "completed_date": "2026-04-02", "stage": "Date-1 -> Date-2 (D3 blank)"},
}


def get_tat_category(days: int) -> str:
    """Categorize TAT days into Analytics chart buckets."""
    if days <= 0:
        return "On or due date"
    elif days <= 2:
        return "Within 2 days"
    elif days <= 7:
        return "3–7 days"
    elif days <= 30:
        return "7–30 days"
    else:
        return "More than 30 day"


async def run_update(dry_run: bool = False):
    """Main async function: match DB records and update revision dates."""
    print()
    print("=" * 80)
    print(" F&F Revision TAT DMS Date Update Script")
    if dry_run:
        print(" MODE: DRY RUN — No changes will be written to the database")
    else:
        print(" MODE: LIVE — Changes WILL be written to the database")
    print("=" * 80)
    print(f" Total records to update : {len(FNF_REVISION_DATA)}")
    print("   • 15 records with Date-2 -> Date-3 (2-Cycle Revisions)")
    print("   • 19 records with Date-1 -> Date-2 (1-Cycle Revisions, Date-3 blank)")
    print()

    person_numbers = list(FNF_REVISION_DATA.keys())

    # ── 1. Fetch DB records ──────────────────────────────────────────────────
    print("Fetching records from database...")
    async with async_session() as db:
        res = await db.execute(
            select(NdcRecord).where(NdcRecord.person_number.in_(person_numbers))
        )
        records = res.scalars().all()
        db_map = {r.person_number: r for r in records}

    print(f"  Matched {len(db_map)} of {len(FNF_REVISION_DATA)} records in database.")
    print()

    # ── 2. Compute update plan & TAT ─────────────────────────────────────────
    to_update = []
    not_in_db = []
    category_counts = {
        "On or due date": 0,
        "Within 2 days": 0,
        "3–7 days": 0,
        "7–30 days": 0,
        "More than 30 day": 0,
    }

    for pn, info in FNF_REVISION_DATA.items():
        if pn not in db_map:
            not_in_db.append((pn, info))
            continue
        record = db_map[pn]
        new_start = datetime.date.fromisoformat(info["start_date"])
        new_completed = datetime.date.fromisoformat(info["completed_date"])
        tat_days = (new_completed - new_start).days
        cat = get_tat_category(tat_days)
        category_counts[cat] += 1
        to_update.append((record, new_start, new_completed, tat_days, cat, info))

    # ── 3. Print change table ────────────────────────────────────────────────
    print("-" * 80)
    print(f"{'Person No':<10} {'Name':<24} {'Rev Start':<11} {'Rev End':<11} {'Days':<5} {'Category'}")
    print("-" * 80)

    for record, new_start, new_completed, tat_days, cat, info in to_update:
        print(
            f"{record.person_number:<10} "
            f"{record.employee_name[:23]:<24} "
            f"{str(new_start):<11} "
            f"{str(new_completed):<11} "
            f"{tat_days:<5} "
            f"{cat}"
        )

    for pn, info in not_in_db:
        print(f"{pn:<10} {info['name'][:23]:<24} {'—':<11} {'—':<11} {'—':<5} [SKIP - NOT FOUND]")

    print("-" * 80)
    print()

    # ── 4. Summary & Distribution ────────────────────────────────────────────
    print("TAT DISTRIBUTION FOR F&F REVISION CHART:")
    total_valid = len(to_update)
    for cat_name, count in category_counts.items():
        pct = round((count / total_valid) * 100) if total_valid > 0 else 0
        print(f"  • {cat_name:<18} : {count:>2} ({pct:>2}%)")
    print()
    print("SUMMARY:")
    print(f"  Total target records       : {len(FNF_REVISION_DATA)}")
    print(f"  Matched in DB              : {len(db_map)}")
    print(f"  Records to update          : {len(to_update)}")
    print(f"  Not found in DB (skipped)  : {len(not_in_db)}")
    print()

    if not to_update:
        print("Nothing to update. Exiting.")
        return

    # ── 5. Apply updates ─────────────────────────────────────────────────────
    if dry_run:
        print("[DRY RUN] No changes written to the database.")
        print("=" * 80)
        return

    print(f"Applying {len(to_update)} update(s) to the database...")
    async with async_session() as db:
        try:
            res = await db.execute(
                select(NdcRecord).where(NdcRecord.person_number.in_(person_numbers))
            )
            db_records = {r.person_number: r for r in res.scalars().all()}

            updated_count = 0
            for record_ref, new_start, new_completed, tat_days, cat, info in to_update:
                pn = record_ref.person_number
                record = db_records.get(pn)
                if record is None:
                    print(f"  [WARN] PN {pn} not found in refresh query — skipping.")
                    continue

                record.fnf_revision_start_date     = new_start
                record.fnf_revision_completed_date = new_completed
                record.is_fnf_revision             = False  # historical revision resolved
                updated_count += 1

            await db.commit()
            print(f"  OK: Successfully committed {updated_count} record(s).")

        except Exception as e:
            await db.rollback()
            print(f"  ERROR: Transaction rolled back: {e}")
            raise

    print()
    print("Done.")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Update F&F revision dates for all historical revisions.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing to DB.")
    args = parser.parse_args()

    asyncio.run(run_update(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
