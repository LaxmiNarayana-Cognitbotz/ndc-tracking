# -*- coding: utf-8 -*-
"""
update_fnf_dms_dates.py
=======================
Updates `fnf_completed_date` and `is_fnf_completed` for historical employee
records using actual F&F DMS dates pre-resolved from F_F Completed (1).xlsx.

Data is embedded directly in this script — no Excel file needed on the server.

Priority rule applied (already resolved at source):
    F&F DMS Date-3  →  F&F DMS Date-2  →  F&F DMS Date-1

Fields updated:
    - fnf_completed_date  →  resolved DMS date
    - is_fnf_completed    →  True

Fields NOT touched:
    - is_fnf_closed                  (user-managed)
    - Department approval dates      (untouched)
    - fnf_revision_* dates           (untouched)
    - All other columns              (untouched)

Usage:
    # Preview only (no DB changes):
    python scripts/update_fnf_dms_dates.py --dry-run

    # Write to production DB:
    python scripts/update_fnf_dms_dates.py
"""

import asyncio
import io
import datetime
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

# ── Embedded F&F DMS Data ─────────────────────────────────────────────────────
# Source: F_F Completed (1).xlsx
# Priority: Date-3 → Date-2 → Date-1
# Rows with no valid DMS date are excluded (1 record: 30149355 Yaganesh Joshi)
FNF_DMS_DATA = {
    30213962: {"name": "Bhargav Pandya",               "date": "2026-08-06", "source": "Date-1"},
    30128270: {"name": "Laxman Kumar",                 "date": "2026-07-15", "source": "Date-1"},
    30128403: {"name": "Vikash Kumar",                 "date": "2026-07-22", "source": "Date-1"},
    30193478: {"name": "Navin Kushwaha",               "date": "2026-07-15", "source": "Date-1"},
    30128166: {"name": "Ankush Yadav",                 "date": "2026-07-15", "source": "Date-1"},
    30193403: {"name": "Abhishek Kumar Gupta",         "date": "2026-07-28", "source": "Date-1"},
    30119894: {"name": "Anubhab Paul",                 "date": "2026-07-15", "source": "Date-1"},
    30128118: {"name": "Lokesh Suman",                 "date": "2026-06-10", "source": "Date-1"},
    30062222: {"name": "Chintarapu Vijayakumar Reddy", "date": "2026-06-10", "source": "Date-1"},
    30139629: {"name": "P. Siddhartha Sarathi",        "date": "2026-07-03", "source": "Date-1"},
    30184452: {"name": "Athira T M",                   "date": "2026-06-01", "source": "Date-1"},
    30156114: {"name": "Manas Vashistha",              "date": "2026-06-20", "source": "Date-2"},
    30199076: {"name": "Ketan Gojiya",                 "date": "2026-05-08", "source": "Date-1"},
    30136244: {"name": "Piyush Raj",                   "date": "2026-06-24", "source": "Date-1"},
    30141080: {"name": "Ashish Kumar Singh",           "date": "2026-05-22", "source": "Date-1"},
    30131377: {"name": "Parth Trivedi",                "date": "2026-05-08", "source": "Date-1"},
    30122622: {"name": "Sudheer Singh",                "date": "2026-04-27", "source": "Date-1"},
    30068110: {"name": "Tarnish Panchal",              "date": "2026-05-28", "source": "Date-1"},
    30095651: {"name": "Ashok Negi",                   "date": "2026-05-08", "source": "Date-1"},
    30136022: {"name": "Prince Agravat",               "date": "2026-06-10", "source": "Date-1"},
    30115934: {"name": "Fulchand Ukey",                "date": "2026-05-29", "source": "Date-2"},
    30131657: {"name": "Arpan Sahu",                   "date": "2026-06-10", "source": "Date-1"},
    30132990: {"name": "ArunKumar Ojha",               "date": "2026-05-22", "source": "Date-1"},
    30144704: {"name": "Jaswant Rajpurohit",           "date": "2026-05-28", "source": "Date-3"},
    30137820: {"name": "Ravishankar Kumar",            "date": "2026-04-21", "source": "Date-1"},
    30132307: {"name": "Sushil Kumar",                 "date": "2026-05-22", "source": "Date-1"},
    30193418: {"name": "Vishal Singh Jodha",           "date": "2026-04-21", "source": "Date-1"},
    30054376: {"name": "Dhaval Patel",                 "date": "2026-05-29", "source": "Date-3"},
    30061897: {"name": "Bharat Kumar Joshi",           "date": "2026-07-03", "source": "Date-1"},
    30073951: {"name": "Rohit Singh",                  "date": "2026-05-22", "source": "Date-1"},
    30138821: {"name": "Rahul Kumar",                  "date": "2026-05-29", "source": "Date-3"},
    30081658: {"name": "Kiran Kumar Pilli",            "date": "2026-05-29", "source": "Date-3"},
    30135759: {"name": "Pankaj Kumar",                 "date": "2026-06-20", "source": "Date-3"},
    30122463: {"name": "Niranjan Kumar Panchal",       "date": "2026-06-24", "source": "Date-1"},
    30182163: {"name": "Yogesh Tripathi",              "date": "2026-06-16", "source": "Date-3"},
    30128248: {"name": "Rakesh Beniwal",               "date": "2026-04-16", "source": "Date-1"},
    30017177: {"name": "Ankit Velani",                 "date": "2026-06-07", "source": "Date-2"},
    30142467: {"name": "Abhishek Pradhan",             "date": "2026-05-28", "source": "Date-2"},
    30140549: {"name": "Anand Jagdale",                "date": "2026-05-28", "source": "Date-3"},
    30128167: {"name": "Sukhveer .",                   "date": "2026-04-16", "source": "Date-1"},
    30124627: {"name": "Nasib Singh Kadian",           "date": "2026-06-07", "source": "Date-3"},
    30045476: {"name": "Mohammad Shamsuddin Ansari",   "date": "2026-05-29", "source": "Date-3"},
    30143990: {"name": "Nitish Kumar",                 "date": "2026-06-07", "source": "Date-3"},
    30079124: {"name": "Uday Singh",                   "date": "2026-05-22", "source": "Date-1"},
    30008672: {"name": "Alap Patel",                   "date": "2026-04-30", "source": "Date-2"},
    30132287: {"name": "Arun Kumar Singh",             "date": "2026-06-10", "source": "Date-1"},
    30119152: {"name": "Rajnish Mishra",               "date": "2026-05-22", "source": "Date-1"},
    30130503: {"name": "Kiran A",                      "date": "2026-05-22", "source": "Date-1"},
    30149287: {"name": "Nilesh Bhalgamiya",            "date": "2026-03-30", "source": "Date-1"},
    30144818: {"name": "Sathishkumar M",               "date": "2026-04-09", "source": "Date-1"},
    30147168: {"name": "Rajesh Jangid",                "date": "2026-06-10", "source": "Date-1"},
    30115935: {"name": "Kumararaja Sankaran",          "date": "2026-06-07", "source": "Date-2"},
    30165032: {"name": "Shambhu Gupta",                "date": "2026-05-06", "source": "Date-1"},
    30125168: {"name": "Ramesh R",                     "date": "2026-04-11", "source": "Date-1"},
    30066491: {"name": "Ankit Badwaik",                "date": "2026-05-22", "source": "Date-1"},
    30073541: {"name": "Karan Hingrajia",              "date": "2026-06-07", "source": "Date-3"},
    30134432: {"name": "Mallesh Gangarapu",            "date": "2026-05-28", "source": "Date-1"},
    30144882: {"name": "Sravan Kumar Vadlakonda",      "date": "2026-06-20", "source": "Date-2"},
    30149192: {"name": "Kancharla Ramu",               "date": "2026-04-09", "source": "Date-1"},
    30146461: {"name": "Nikunjkumar Gohil",            "date": "2026-04-09", "source": "Date-1"},
    30148752: {"name": "Debashis Mallick",             "date": "2026-05-29", "source": "Date-2"},
    30146460: {"name": "Abhishek Kumar Singh",         "date": "2026-05-22", "source": "Date-1"},
    30143608: {"name": "Romank Joshi",                 "date": "2026-06-07", "source": "Date-3"},
    30015728: {"name": "Ashish Vijaywargi",            "date": "2026-05-22", "source": "Date-1"},
    30132979: {"name": "Subhash Chouhan",              "date": "2026-05-22", "source": "Date-1"},
    30055113: {"name": "Prakhar Bhardwaj",             "date": "2026-04-09", "source": "Date-2"},
    30166392: {"name": "Ananth Raju",                  "date": "2026-04-09", "source": "Date-2"},
    30175638: {"name": "Naveen Kumar Singh",           "date": "2026-04-09", "source": "Date-1"},
    30020705: {"name": "Deepsingh Rajput",             "date": "2026-06-07", "source": "Date-3"},
    30121463: {"name": "Dinesh Chahar",                "date": "2026-04-09", "source": "Date-1"},
    30141689: {"name": "Anil Kumar",                   "date": "2026-05-28", "source": "Date-2"},
    30031097: {"name": "Sharad Singh",                 "date": "2026-03-19", "source": "Date-1"},
    30126438: {"name": "Annavarapu Srikanth",          "date": "2026-04-09", "source": "Date-1"},
    30146965: {"name": "Atul Mishra",                  "date": "2026-04-09", "source": "Date-1"},
    30121931: {"name": "Vipin Gaur",                   "date": "2026-03-24", "source": "Date-1"},
    30135169: {"name": "Manoj Kumar Singh",            "date": "2026-05-06", "source": "Date-1"},
    30127989: {"name": "Bhupendra Kumar Suman",        "date": "2026-03-19", "source": "Date-1"},
    30062812: {"name": "Devendrakumar Parihar",        "date": "2026-05-22", "source": "Date-1"},
    30143609: {"name": "G Pullapuraju",                "date": "2026-06-07", "source": "Date-3"},
    30148093: {"name": "Narendra Kumar Mahanta",       "date": "2026-05-22", "source": "Date-1"},
    30018452: {"name": "Maunank Darji",                "date": "2026-05-28", "source": "Date-2"},
    30054007: {"name": "AJAY MISHRA",                  "date": "2026-04-09", "source": "Date-1"},
    30140601: {"name": "Mukul Dabhi",                  "date": "2026-04-02", "source": "Date-2"},
    30128262: {"name": "Pradyuman Singh",              "date": "2026-04-09", "source": "Date-2"},
    30176105: {"name": "Shiva Mishra",                 "date": "2026-05-06", "source": "Date-1"},
    30199478: {"name": "Vikas Deep Sisodiya",          "date": "2026-04-10", "source": "Date-1"},
    30132980: {"name": "LokeshKumar Sharma",           "date": "2026-04-09", "source": "Date-2"},
    30115522: {"name": "Dhaval Bhatti",                "date": "2026-05-06", "source": "Date-1"},
    30092312: {"name": "Rishabh Pareek",               "date": "2026-03-18", "source": "Date-1"},
    30028616: {"name": "Vinod Gundawar",               "date": "2026-03-17", "source": "Date-1"},
    30151967: {"name": "Rishabh Saxena",               "date": "2026-05-08", "source": "Date-3"},
    30126118: {"name": "Sagar Parmar",                 "date": "2026-03-18", "source": "Date-1"},
    30119040: {"name": "Kishan Meghnathi",             "date": "2026-04-02", "source": "Date-2"},
    30128006: {"name": "Devanshu Agarwal",             "date": "2026-03-25", "source": "Date-1"},
    30079146: {"name": "Shailendra Kumar",             "date": "2026-03-18", "source": "Date-1"},
    30015403: {"name": "Ravi Bhushan",                 "date": "2026-07-11", "source": "Date-1"},
    30016834: {"name": "Ravindra Prajapati",           "date": "2026-07-18", "source": "Date-1"},
    30033303: {"name": "Jaydip Talaviya",              "date": "2026-06-18", "source": "Date-1"},
    30067117: {"name": "Aditya Gupta",                 "date": "2026-07-22", "source": "Date-1"},
    30132851: {"name": "Soumya Ranjan Rout",           "date": "2026-07-28", "source": "Date-1"},
    30203140: {"name": "Prakash Chand Garg",           "date": "2026-06-20", "source": "Date-1"},
    30133866: {"name": "Siddhivinayak Chinchalkar",    "date": "2026-07-15", "source": "Date-1"},
    30119899: {"name": "Gaurav Kumar",                 "date": "2026-06-07", "source": "Date-1"},
    30128250: {"name": "Mahipal Singh",                "date": "2026-06-07", "source": "Date-1"},
    30128328: {"name": "Rakesh Kumar",                 "date": "2026-06-10", "source": "Date-1"},
    30130741: {"name": "Mehul Hadiya",                 "date": "2026-07-03", "source": "Date-1"},
    30133030: {"name": "Keyur Trivedi",                "date": "2026-07-15", "source": "Date-1"},
    30193310: {"name": "Bhupendra Singh",              "date": "2026-07-03", "source": "Date-1"},
    30022156: {"name": "Sachitra Swain",               "date": "2026-07-22", "source": "Date-1"},
    30193401: {"name": "Sudhanshu Shukla",             "date": "2026-07-15", "source": "Date-1"},
    30193403: {"name": "Abhishek Kumar Gupta",         "date": "2026-07-28", "source": "Date-1"},
}
# ─────────────────────────────────────────────────────────────────────────────


async def run_update(dry_run: bool = False):
    """Main async function: match DB records and update fnf_completed_date."""
    print()
    print("=" * 70)
    print(" F&F DMS Date Update Script")
    if dry_run:
        print(" MODE: DRY RUN — No changes will be written to the database")
    else:
        print(" MODE: LIVE — Changes WILL be written to the database")
    print("=" * 70)
    print(f" Total embedded records : {len(FNF_DMS_DATA)}")
    print()

    person_numbers = list(FNF_DMS_DATA.keys())

    # ── 1. Fetch DB records ──────────────────────────────────────────────────
    print("Fetching records from database...")
    async with async_session() as db:
        res = await db.execute(
            select(NdcRecord).where(NdcRecord.person_number.in_(person_numbers))
        )
        records = res.scalars().all()
        db_map = {r.person_number: r for r in records}

    print(f"  Matched {len(db_map)} of {len(FNF_DMS_DATA)} records in the database.")
    print()

    # ── 2. Compute update plan ───────────────────────────────────────────────
    to_update       = []
    already_correct = []
    not_in_db       = []

    for pn, info in FNF_DMS_DATA.items():
        if pn not in db_map:
            not_in_db.append((pn, info))
            continue

        record       = db_map[pn]
        new_date     = datetime.date.fromisoformat(info["date"])
        source_label = info["source"]

        if record.fnf_completed_date == new_date and record.is_fnf_completed:
            already_correct.append((pn, info, record))
            continue

        to_update.append((record, new_date, source_label, info))

    # ── 3. Print change table ────────────────────────────────────────────────
    print("-" * 72)
    print(f"{'Person No':<12} {'Name':<30} {'Old Date':<12} {'New Date':<12} Source")
    print("-" * 72)

    for record, new_date, source_label, info in to_update:
        old = str(record.fnf_completed_date) if record.fnf_completed_date else "NULL"
        marker = "[UPDATE]" if old != str(new_date) else "[SET FLAG]"
        print(
            f"{record.person_number:<12} "
            f"{record.employee_name:<30} "
            f"{old:<12} "
            f"{str(new_date):<12} "
            f"[{source_label}]  {marker}"
        )

    for pn, info, record in already_correct:
        print(f"{pn:<12} {info['name']:<30} {str(record.fnf_completed_date):<12} {'—':<12} [OK — already correct]")

    for pn, info in not_in_db:
        print(f"{pn:<12} {info['name']:<30} {'—':<12} {'—':<12} [SKIP — not found in DB]")

    print("-" * 72)
    print()

    # ── 4. Summary ───────────────────────────────────────────────────────────
    print("SUMMARY")
    print(f"  Total embedded records     : {len(FNF_DMS_DATA)}")
    print(f"  Matched in DB              : {len(db_map)}")
    print(f"  Records to update          : {len(to_update)}")
    print(f"  Already correct (skipped)  : {len(already_correct)}")
    print(f"  Not found in DB (skipped)  : {len(not_in_db)}")
    print()

    if not to_update:
        print("Nothing to update. Exiting.")
        return

    # ── 5. Apply updates ─────────────────────────────────────────────────────
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
            for record_ref, new_date, source_label, info in to_update:
                pn = record_ref.person_number
                record = db_records.get(pn)
                if record is None:
                    print(f"  [WARN] PN {pn} not found in refresh query — skipping.")
                    continue

                record.fnf_completed_date = new_date
                record.is_fnf_completed   = True
                # is_fnf_closed is NOT touched — user-managed only
                updated_count += 1

            await db.commit()
            print(f"  OK: Successfully committed {updated_count} record(s).")

        except Exception as e:
            await db.rollback()
            print(f"  ERROR: Transaction rolled back: {e}")
            raise

    print()
    print("Done.")
    print("=" * 70)


def main():
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run_update(dry_run=dry_run))


if __name__ == "__main__":
    main()
