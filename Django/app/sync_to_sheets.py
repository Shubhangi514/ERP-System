import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from students.models import Student, Teacher, Staff, Document, Assignment, LogEntry
from students.google_sheets import (
    get_client, get_or_create_sheet, _build_row,
    STUDENTS_HEADERS, TEACHERS_HEADERS, STAFF_HEADERS,
    DOCUMENTS_HEADERS, ASSIGNMENTS_HEADERS, LOGS_HEADERS
)

print("Starting FULL sync of Django Database to Google Sheets in bulk...")

client = get_client()

def bulk_sync(model_class, headers, sheet_name):
    print(f"Syncing {sheet_name}...")
    sheet = get_or_create_sheet(client, sheet_name=sheet_name, headers=headers)
    
    # Get all items from DB
    items = list(model_class.objects.all())
    
    if not items:
        print(f"  No data for {sheet_name}. Skipping.")
        return
        
    # Build all rows
    rows = [_build_row(item) for item in items]
    
    # 1. Clear existing data below header (row 2 onwards)
    # 2. Upload everything in one API call
    try:
        # worksheet.clear() is slow/removes headers format, safer to clear content only
        sheet.batch_clear([f"A2:Z1000"]) 
        # Update using list of lists
        sheet.update([headers] + rows)
        print(f"✅ Synced {len(rows)} items to '{sheet_name}'.")
    except Exception as e:
        # Fallback to older gspread signature if list of list fails
        try:
            sheet.update(f"A1", [headers] + rows)
            print(f"✅ Synced {len(rows)} items to '{sheet_name}'.")
        except Exception as inner_e:
            print(f"❌ Failed to sync '{sheet_name}': {inner_e}")

bulk_sync(Student, STUDENTS_HEADERS, 'Students')
bulk_sync(Teacher, TEACHERS_HEADERS, 'Teachers')
bulk_sync(Staff, STAFF_HEADERS, 'Staff')
bulk_sync(Document, DOCUMENTS_HEADERS, 'Documents')
bulk_sync(Assignment, ASSIGNMENTS_HEADERS, 'Assignments')
bulk_sync(LogEntry, LOGS_HEADERS, 'Log/History')

print("Sync completed!")
