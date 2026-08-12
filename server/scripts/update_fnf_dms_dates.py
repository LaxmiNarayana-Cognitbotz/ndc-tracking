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
    - fnf_completed_date  →  resolved DMS date (ALWAYS updated, no skip)
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
# Source: F_F Completed (1).xlsx  |  Total: 148 records
# Priority applied: Date-3 → Date-2 → Date-1
# 1 record excluded (30149355 Yaganesh Joshi — no valid DMS date in Excel)
FNF_DMS_DATA = {
    30213962: {"name": "Bhargav Pandya",                    "date": "2026-08-06", "source": "Date-1"},
    30128270: {"name": "Laxman Kumar",                      "date": "2026-07-15", "source": "Date-1"},
    30128403: {"name": "Vikash Kumar",                      "date": "2026-07-22", "source": "Date-1"},
    30193478: {"name": "Navin Kushwaha",                    "date": "2026-07-15", "source": "Date-1"},
    30128166: {"name": "Ankush Yadav",                      "date": "2026-07-15", "source": "Date-1"},
    30193403: {"name": "Abhishek Kumar Gupta",              "date": "2026-07-28", "source": "Date-1"},
    30119894: {"name": "Anubhab Paul",                      "date": "2026-07-15", "source": "Date-1"},
    30122299: {"name": "Sachin Datt Sen",                   "date": "2026-07-09", "source": "Date-1"},
    30106855: {"name": "Saurav Rohit",                      "date": "2026-07-09", "source": "Date-1"},
    30193409: {"name": "Anuj Kumar",                        "date": "2026-07-28", "source": "Date-1"},
    30016834: {"name": "Ravindra Prajapati",                "date": "2026-07-18", "source": "Date-1"},
    30126226: {"name": "Akash Deep Kumawat",                "date": "2026-07-09", "source": "Date-1"},
    30015403: {"name": "Ravi Bhushan",                      "date": "2026-07-11", "source": "Date-1"},
    30104956: {"name": "Neeraj Kumar Saini",                "date": "2026-07-15", "source": "Date-1"},
    30128795: {"name": "Animesh Kanrar",                    "date": "2026-07-15", "source": "Date-1"},
    30138816: {"name": "Nripendra Vikram Singh",            "date": "2026-07-15", "source": "Date-1"},
    30088330: {"name": "Sumay Keshanakurthy",               "date": "2026-07-18", "source": "Date-1"},
    30174776: {"name": "Ravi R",                            "date": "2026-07-10", "source": "Date-1"},
    30193388: {"name": "Pawan Kumar Suman",                 "date": "2026-07-01", "source": "Date-1"},
    30128289: {"name": "Mukesh Kumar",                      "date": "2026-07-01", "source": "Date-1"},
    30133225: {"name": "Darshan Mokariya",                  "date": "2026-07-01", "source": "Date-1"},
    30134305: {"name": "Jaydev Joshi",                      "date": "2026-06-18", "source": "Date-1"},
    30214650: {"name": "Prodip Mondal",                     "date": "2026-07-03", "source": "Date-1"},
    30193405: {"name": "Aditya Giri",                       "date": "2026-06-24", "source": "Date-1"},
    30135997: {"name": "Abhay Trivedi",                     "date": "2026-07-15", "source": "Date-1"},
    30211905: {"name": "Sonu Kumar Sharma",                 "date": "2026-07-22", "source": "Date-1"},
    30193431: {"name": "Shreyash Maddeshiya",               "date": "2026-07-18", "source": "Date-1"},
    30124073: {"name": "Debashis Biswas",                   "date": "2026-07-03", "source": "Date-1"},
    30193374: {"name": "Pritosh Kumar Rav",                 "date": "2026-07-01", "source": "Date-1"},
    30193398: {"name": "Nikhil Gupta",                      "date": "2026-06-24", "source": "Date-1"},
    30122796: {"name": "Chaitanya Paun",                    "date": "2026-07-10", "source": "Date-1"},
    30128203: {"name": "Dishant Sharma",                    "date": "2026-07-09", "source": "Date-1"},
    30132999: {"name": "Shashikant Mishra",                 "date": "2026-06-24", "source": "Date-1"},
    30138604: {"name": "Shashikant Kumar",                  "date": "2026-07-01", "source": "Date-1"},
    30185300: {"name": "Mayurkumar Dulera",                 "date": "2026-06-24", "source": "Date-1"},
    30193326: {"name": "Vikas Kumar",                       "date": "2026-07-01", "source": "Date-1"},
    30132851: {"name": "Soumya Ranjan Rout",                "date": "2026-07-01", "source": "Date-1"},
    30055143: {"name": "Konreddy Prasad Reddy",             "date": "2026-06-24", "source": "Date-1"},
    30079127: {"name": "Shubham Kumar",                     "date": "2026-06-10", "source": "Date-1"},
    30121400: {"name": "Roop Chand",                        "date": "2026-07-10", "source": "Date-1"},
    30153662: {"name": "Rohit Kumar",                       "date": "2026-06-10", "source": "Date-1"},
    30079622: {"name": "Rituraj Jha",                       "date": "2026-07-18", "source": "Date-1"},
    30138823: {"name": "Deepesh Nigam",                     "date": "2026-07-22", "source": "Date-1"},
    30128868: {"name": "Harvansh Gour",                     "date": "2026-07-22", "source": "Date-1"},
    30104955: {"name": "Yogeswara Rao",                     "date": "2026-06-10", "source": "Date-1"},
    30141685: {"name": "Ashwini Saraswat",                  "date": "2026-07-15", "source": "Date-1"},
    30107279: {"name": "Sairaj Mulange",                    "date": "2026-06-10", "source": "Date-1"},
    30136026: {"name": "Akshar Bumatariya",                 "date": "2026-06-10", "source": "Date-1"},
    30150942: {"name": "Rohit Asthana",                     "date": "2026-07-18", "source": "Date-1"},
    30128233: {"name": "Amrit Lal",                         "date": "2026-06-24", "source": "Date-1"},
    30121426: {"name": "Kedar Raval",                       "date": "2026-06-24", "source": "Date-1"},
    30124522: {"name": "Alok Kumar",                        "date": "2026-07-11", "source": "Date-1"},
    30055010: {"name": "Vinay Thumbalam",                   "date": "2026-06-10", "source": "Date-1"},
    30094498: {"name": "Ranbahadur Singh",                  "date": "2026-06-24", "source": "Date-1"},
    30133632: {"name": "Munandra Singh",                    "date": "2026-07-18", "source": "Date-2"},
    30121947: {"name": "Mukesh Pal",                        "date": "2026-06-11", "source": "Date-1"},
    30033303: {"name": "Jaydip Talaviya",                   "date": "2026-06-18", "source": "Date-1"},
    30130531: {"name": "Rajan Kamboj",                      "date": "2026-07-18", "source": "Date-1"},
    30125554: {"name": "Hardik Vadiya",                     "date": "2026-06-20", "source": "Date-2"},
    30067117: {"name": "Aditya Gupta",                      "date": "2026-06-20", "source": "Date-2"},
    30128118: {"name": "Lokesh Suman",                      "date": "2026-06-10", "source": "Date-1"},
    30062222: {"name": "Chintarapu Vijayakumar Reddy",      "date": "2026-06-10", "source": "Date-1"},
    30139629: {"name": "P. Siddhartha Sarathi",             "date": "2026-07-03", "source": "Date-1"},
    30184452: {"name": "Athira T M",                        "date": "2026-06-01", "source": "Date-1"},
    30156114: {"name": "Manas Vashistha",                   "date": "2026-06-20", "source": "Date-2"},
    30199076: {"name": "Ketan Gojiya",                      "date": "2026-05-08", "source": "Date-1"},
    30136244: {"name": "Piyush Raj",                        "date": "2026-06-24", "source": "Date-1"},
    30141080: {"name": "Ashish Kumar Singh",                "date": "2026-05-22", "source": "Date-1"},
    30131377: {"name": "Parth Trivedi",                     "date": "2026-05-08", "source": "Date-1"},
    30122622: {"name": "Sudheer Singh",                     "date": "2026-04-27", "source": "Date-1"},
    30068110: {"name": "Tarnish Panchal",                   "date": "2026-05-28", "source": "Date-1"},
    30095651: {"name": "Ashok Negi",                        "date": "2026-05-08", "source": "Date-1"},
    30136022: {"name": "Prince Agravat",                    "date": "2026-06-10", "source": "Date-1"},
    30115934: {"name": "Fulchand Ukey",                     "date": "2026-05-29", "source": "Date-2"},
    30131657: {"name": "Arpan Sahu",                        "date": "2026-06-10", "source": "Date-1"},
    30132990: {"name": "ArunKumar Ojha",                    "date": "2026-05-22", "source": "Date-1"},
    30144704: {"name": "Jaswant Rajpurohit",                "date": "2026-05-28", "source": "Date-3"},
    30137820: {"name": "Ravishankar Kumar",                 "date": "2026-04-21", "source": "Date-1"},
    30132307: {"name": "Sushil Kumar",                      "date": "2026-05-22", "source": "Date-1"},
    30193418: {"name": "Vishal Singh Jodha",                "date": "2026-04-21", "source": "Date-1"},
    30054376: {"name": "Dhaval Patel",                      "date": "2026-05-29", "source": "Date-3"},
    30061897: {"name": "Bharat Kumar Joshi",                "date": "2026-07-03", "source": "Date-1"},
    30073951: {"name": "Rohit Singh",                       "date": "2026-05-22", "source": "Date-1"},
    30138821: {"name": "Rahul Kumar",                       "date": "2026-05-29", "source": "Date-3"},
    30081658: {"name": "Kiran Kumar Pilli",                 "date": "2026-05-29", "source": "Date-3"},
    30135759: {"name": "Pankaj Kumar",                      "date": "2026-06-20", "source": "Date-3"},
    30122463: {"name": "Niranjan Kumar Panchal",            "date": "2026-06-24", "source": "Date-1"},
    30182163: {"name": "Yogesh Tripathi",                   "date": "2026-06-16", "source": "Date-3"},
    30128248: {"name": "Rakesh Beniwal",                    "date": "2026-04-16", "source": "Date-1"},
    30017177: {"name": "Ankit Velani",                      "date": "2026-06-07", "source": "Date-2"},
    30142467: {"name": "Abhishek Pradhan",                  "date": "2026-05-28", "source": "Date-2"},
    30140549: {"name": "Anand Jagdale",                     "date": "2026-05-28", "source": "Date-3"},
    30128167: {"name": "Sukhveer .",                        "date": "2026-04-16", "source": "Date-1"},
    30124627: {"name": "Nasib Singh Kadian",                "date": "2026-06-07", "source": "Date-3"},
    30045476: {"name": "Mohammad Shamsuddin Ansari",        "date": "2026-05-29", "source": "Date-3"},
    30143990: {"name": "Nitish Kumar",                      "date": "2026-06-07", "source": "Date-3"},
    30079124: {"name": "Uday Singh",                        "date": "2026-05-22", "source": "Date-1"},
    30008672: {"name": "Alap Patel",                        "date": "2026-04-30", "source": "Date-2"},
    30132287: {"name": "Arun Kumar Singh",                  "date": "2026-06-10", "source": "Date-1"},
    30119152: {"name": "Rajnish Mishra",                    "date": "2026-05-22", "source": "Date-1"},
    30130503: {"name": "Kiran A",                           "date": "2026-05-22", "source": "Date-1"},
    30149287: {"name": "Nilesh Bhalgamiya",                 "date": "2026-03-30", "source": "Date-1"},
    30144818: {"name": "Sathishkumar M",                    "date": "2026-04-09", "source": "Date-1"},
    30147168: {"name": "Rajesh Jangid",                     "date": "2026-06-10", "source": "Date-1"},
    30115935: {"name": "Kumararaja Sankaran",               "date": "2026-06-07", "source": "Date-2"},
    30165032: {"name": "Shambhu Gupta",                     "date": "2026-05-06", "source": "Date-1"},
    30125168: {"name": "Ramesh R",                          "date": "2026-04-11", "source": "Date-1"},
    30066491: {"name": "Ankit Badwaik",                     "date": "2026-05-22", "source": "Date-1"},
    30073541: {"name": "Karan Hingrajia",                   "date": "2026-06-07", "source": "Date-3"},
    30134432: {"name": "Mallesh Gangarapu",                 "date": "2026-05-28", "source": "Date-1"},
    30144882: {"name": "Sravan Kumar Vadlakonda",           "date": "2026-06-20", "source": "Date-2"},
    30149192: {"name": "Kancharla Ramu",                    "date": "2026-04-09", "source": "Date-1"},
    30146461: {"name": "Nikunjkumar Gohil",                 "date": "2026-04-09", "source": "Date-1"},
    30148752: {"name": "Debashis Mallick",                  "date": "2026-05-29", "source": "Date-2"},
    30146460: {"name": "Abhishek Kumar Singh",              "date": "2026-05-22", "source": "Date-1"},
    30143608: {"name": "Romank Joshi",                      "date": "2026-06-07", "source": "Date-3"},
    30015728: {"name": "Ashish Vijaywargi",                 "date": "2026-05-22", "source": "Date-1"},
    30132979: {"name": "Subhash Chouhan",                   "date": "2026-05-22", "source": "Date-1"},
    30055113: {"name": "Prakhar Bhardwaj",                  "date": "2026-04-09", "source": "Date-2"},
    30166392: {"name": "Ananth Raju",                       "date": "2026-04-09", "source": "Date-2"},
    30175638: {"name": "Naveen Kumar Singh",                "date": "2026-04-09", "source": "Date-1"},
    30020705: {"name": "Deepsingh Rajput",                  "date": "2026-06-07", "source": "Date-3"},
    30121463: {"name": "Dinesh Chahar",                     "date": "2026-04-09", "source": "Date-1"},
    30141689: {"name": "Anil Kumar",                        "date": "2026-05-28", "source": "Date-2"},
    30031097: {"name": "Sharad Singh",                      "date": "2026-03-19", "source": "Date-1"},
    30126438: {"name": "Annavarapu Srikanth",               "date": "2026-04-09", "source": "Date-1"},
    30146965: {"name": "Atul Mishra",                       "date": "2026-04-09", "source": "Date-1"},
    30121931: {"name": "Vipin Gaur",                        "date": "2026-03-24", "source": "Date-1"},
    30135169: {"name": "Manoj Kumar Singh",                 "date": "2026-05-06", "source": "Date-1"},
    30127989: {"name": "Bhupendra Kumar Suman",             "date": "2026-03-19", "source": "Date-1"},
    30062812: {"name": "Devendrakumar Parihar",             "date": "2026-05-22", "source": "Date-1"},
    30143609: {"name": "G Pullapuraju",                     "date": "2026-06-07", "source": "Date-3"},
    30148093: {"name": "Narendra Kumar Mahanta",            "date": "2026-05-22", "source": "Date-1"},
    30018452: {"name": "Maunank Darji",                     "date": "2026-05-28", "source": "Date-2"},
    30054007: {"name": "AJAY MISHRA",                       "date": "2026-04-09", "source": "Date-1"},
    30140601: {"name": "Mukul Dabhi",                       "date": "2026-04-02", "source": "Date-2"},
    30128262: {"name": "Pradyuman Singh",                   "date": "2026-04-09", "source": "Date-2"},
    30176105: {"name": "Shiva Mishra",                      "date": "2026-05-06", "source": "Date-1"},
    30199478: {"name": "Vikas Deep Sisodiya",               "date": "2026-04-10", "source": "Date-1"},
    30132980: {"name": "LokeshKumar Sharma",                "date": "2026-04-09", "source": "Date-2"},
    30115522: {"name": "Dhaval Bhatti",                     "date": "2026-05-06", "source": "Date-1"},
    30092312: {"name": "Rishabh Pareek",                    "date": "2026-03-18", "source": "Date-1"},
    30028616: {"name": "Vinod Gundawar",                    "date": "2026-03-17", "source": "Date-1"},
    30151967: {"name": "Rishabh Saxena",                    "date": "2026-05-08", "source": "Date-3"},
    30126118: {"name": "Sagar Parmar",                      "date": "2026-03-18", "source": "Date-1"},
    30119040: {"name": "Kishan Meghnathi",                  "date": "2026-04-02", "source": "Date-2"},
    30128006: {"name": "Devanshu Agarwal",                  "date": "2026-03-25", "source": "Date-1"},
    30079146: {"name": "Shailendra Kumar",                  "date": "2026-03-18", "source": "Date-1"},
}
# ─────────────────────────────────────────────────────────────────────────────


async def run_update(dry_run: bool = False):
    """Main async function: match DB records and update fnf_completed_date."""
    print()
    print("=" * 72)
    print(" F&F DMS Date Update Script")
    if dry_run:
        print(" MODE: DRY RUN — No changes will be written to the database")
    else:
        print(" MODE: LIVE — Changes WILL be written to the database")
    print("=" * 72)
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
    # NOTE: ALL matched records are updated regardless of existing date.
    # This ensures the DMS date always wins and overwrites any old default date.
    to_update   = []
    not_in_db   = []

    for pn, info in FNF_DMS_DATA.items():
        if pn not in db_map:
            not_in_db.append((pn, info))
            continue
        record       = db_map[pn]
        new_date     = datetime.date.fromisoformat(info["date"])
        source_label = info["source"]
        to_update.append((record, new_date, source_label, info))

    # ── 3. Print change table ────────────────────────────────────────────────
    print("-" * 74)
    print(f"{'Person No':<12} {'Name':<32} {'Old Date':<12} {'New Date':<12} Source")
    print("-" * 74)

    for record, new_date, source_label, info in to_update:
        old = str(record.fnf_completed_date) if record.fnf_completed_date else "NULL"
        changed = "[UPDATE]" if old != str(new_date) else "[SAME DATE — force set]"
        print(
            f"{record.person_number:<12} "
            f"{record.employee_name:<32} "
            f"{old:<12} "
            f"{str(new_date):<12} "
            f"[{source_label}]  {changed}"
        )

    for pn, info in not_in_db:
        print(f"{pn:<12} {info['name']:<32} {'—':<12} {'—':<12} [SKIP — not found in DB]")

    print("-" * 74)
    print()

    # ── 4. Summary ───────────────────────────────────────────────────────────
    same_date_count = sum(
        1 for r, d, _, __ in to_update if r.fnf_completed_date == d
    )
    print("SUMMARY")
    print(f"  Total embedded records     : {len(FNF_DMS_DATA)}")
    print(f"  Matched in DB              : {len(db_map)}")
    print(f"  Records to update          : {len(to_update)}")
    print(f"    - Date will change       : {len(to_update) - same_date_count}")
    print(f"    - Same date (force-set)  : {same_date_count}")
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
    print("=" * 72)


def main():
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run_update(dry_run=dry_run))


if __name__ == "__main__":
    main()
