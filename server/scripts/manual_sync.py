import asyncio
import os
import sys
import logging

# Disable all internal loggers so they don't mess up our clean console output
logging.getLogger().setLevel(logging.CRITICAL)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.database import async_session
from app.helpers.ff.sharepoint_sync_service import SharePointSyncService

async def manual_sync():
    print("Connecting to SharePoint...")

    try:
        sync_service = SharePointSyncService()
    except Exception as e:
        print(f"Error: Failed to initialize SharePoint service: {e}")
        sys.exit(1)

    async with async_session() as db:
        try:
            print("Syncing NDC_Reports Excel files...")
            results = await sync_service.check_and_ingest_new_files(db)
            
            if results["status"] != "success":
                print("Error: Excel Sync failed.")
            else:
                if results["files_ingested"] == 0:
                    print("No new files found on SharePoint.")
                else:
                    for d in results.get("details", []):
                        if d['status'] == 'ingested':
                            records = d.get('records_processed', 0)
                            print(f"Ingested: {d['file_name']} ({records} records)")

            print("Syncing F&F Document Presence...")
            doc_result = await sync_service.sync_fnf_document_presence(db)
            if doc_result["status"] == "failed":
                print(f"Error: F&F Document presence sync failed: {doc_result.get('errors')}")
            else:
                print(f"Document presence sync completed. Found {doc_result.get('folders_found', 0)} folders.")

            print("Syncing F&F Completed Status...")
            fnf_result = await sync_service.sync_fnf_completed_records(db)
            if fnf_result["status"] == "failed":
                print(f"Error: F&F Completed status sync failed: {fnf_result.get('errors')}")
            else:
                print(f"F&F Completed sync completed. Completed: {fnf_result.get('records_updated', 0)}, Reverted: {fnf_result.get('records_reverted', 0)}")
                    
            print("\nSync Success")
                    
        except Exception as e:
            print(f"Error: The sync process crashed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(manual_sync())
