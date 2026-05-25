import os
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


def get_credentials():
    """Load Google service-account credentials (google-auth library)."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    creds_path = os.path.join(BASE_DIR, "credentials.json")
    return Credentials.from_service_account_file(creds_path, scopes=scope)


def get_client():
    return gspread.authorize(get_credentials())


def get_or_create_sheet(client, spreadsheet_name="StudentsDB", sheet_name="Students", headers=None):
    try:
        spreadsheet = client.open(spreadsheet_name)
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(spreadsheet_name)
        spreadsheet.share(None, perm_type='anyone', role='reader')

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=500, cols=30)

    if headers:
        current_headers = worksheet.row_values(1)
        if current_headers != headers:
            worksheet.update([headers], "A1")

    # Tab colour (non-critical – failure is silenced)
    try:
        service = build('sheets', 'v4', credentials=get_credentials())
        colours = {
            'Students':    {'red': 0,    'green': 0.2, 'blue': 0.8},
            'Teachers':    {'red': 0.07, 'green': 0.53,'blue': 0.33},
            'Staff':       {'red': 0.6,  'green': 0.2, 'blue': 0.7},
            'Documents':   {'red': 0.2,  'green': 0.8, 'blue': 0.2},
            'Assignments': {'red': 1,    'green': 0.6, 'blue': 0},
            'Log/History': {'red': 0.4,  'green': 0.4, 'blue': 0.4},
        }
        colour = colours.get(sheet_name, {'red': 1, 'green': 1, 'blue': 1})
        body   = {'requests': [{'updateSheetProperties': {
            'properties': {'sheetId': worksheet.id, 'title': sheet_name, 'tabColor': colour},
            'fields': 'tabColor',
        }}]}
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet.id, body=body).execute()
    except Exception as e:
        print(f"⚠️  Tab colour skipped: {e}")

    return worksheet


# ── Headers ────────────────────────────────────────────────────────────────────
STUDENTS_HEADERS = [
    "StudentID", "Name", "Email", "Phone",
    "Gender", "Class", "Fees_Paid", "Address",
    "Course", "Attendance", "Marks",
]
TEACHERS_HEADERS = [
    "EmployeeID", "Name", "Email", "Phone", "Gender", "DateOfBirth",
    "Subject", "ClassesTaught", "Qualification", "ExperienceYears",
    "Specialization", "EmploymentType", "DateJoined", "Salary",
    "Bio", "Achievements", "Address",
]
STAFF_HEADERS = [
    "EmployeeID", "Name", "Email", "Phone", "Gender", "DateOfBirth",
    "Designation", "Department", "WorkDescription", "EmploymentType",
    "DateJoined", "Salary", "Qualification", "Bio", "Address",
]
DOCUMENTS_HEADERS = [
    "DocID", "StudentID", "Student_Name", "Student_Class",
    "Doc_Type", "File_URL", "Upload_Date",
]
ASSIGNMENTS_HEADERS = ["AssignID", "StudentID", "Subject", "File_Link", "Status", "Score"]
LOGS_HEADERS        = ["Action", "UserID", "Timestamp", "Description"]


# ── Row builders ───────────────────────────────────────────────────────────────
def _build_row(entity):
    name = entity.__class__.__name__

    if name == 'Student':
        gender_map = {'M': 'Male', 'F': 'Female', 'O': 'Other'}
        return [
            str(entity.id),
            entity.name,
            entity.email,
            entity.phone or '',
            gender_map.get(entity.gender, entity.gender),
            entity.class_name or '',
            'Yes' if entity.fees_paid else 'No',
            entity.address or '',
            entity.course,
            str(entity.attendance),
            str(entity.marks),
        ]

    if name == 'Teacher':
        gender_map = {'M': 'Male', 'F': 'Female', 'O': 'Other'}
        return [
            entity.employee_id,
            entity.name,
            entity.email,
            entity.phone or '',
            gender_map.get(entity.gender, entity.gender),
            str(entity.date_of_birth) if entity.date_of_birth else '',
            entity.subject,
            entity.classes_taught or '',
            entity.qualification,
            str(entity.experience_yrs),
            entity.specialization or '',
            entity.employment_type,
            str(entity.date_joined) if entity.date_joined else '',
            str(entity.salary) if entity.salary else '',
            entity.bio or '',
            entity.achievements or '',
            entity.address or '',
        ]

    if name == 'Staff':
        gender_map = {'M': 'Male', 'F': 'Female', 'O': 'Other'}
        return [
            entity.employee_id,
            entity.name,
            entity.email,
            entity.phone or '',
            gender_map.get(entity.gender, entity.gender),
            str(entity.date_of_birth) if entity.date_of_birth else '',
            entity.designation,
            entity.department,
            entity.work_description or '',
            entity.employment_type,
            str(entity.date_joined) if entity.date_joined else '',
            str(entity.salary) if entity.salary else '',
            entity.qualification or '',
            entity.bio or '',
            entity.address or '',
        ]

    if name == 'Document':
        file_url = ''
        if entity.document_file:
            try:    file_url = entity.document_file.url
            except: file_url = str(entity.document_file)
        elif entity.drive_link:
            file_url = entity.drive_link
        return [
            str(entity.doc_id),
            str(entity.student.id),
            entity.student.name,
            entity.student.class_name or '',
            entity.doc_type,
            file_url,
            str(entity.upload_date),
        ]

    if name == 'Assignment':
        return [
            str(entity.assign_id),
            str(entity.student.id),
            entity.subject,
            entity.file_link,
            entity.status,
            str(entity.score) if entity.score is not None else '',
        ]

    if name == 'LogEntry':
        return [
            entity.action,
            str(entity.user_id),
            str(entity.timestamp),
            entity.description,
        ]

    return []


def _get_pk_val(entity):
    name = entity.__class__.__name__
    if name == 'Student':    return str(entity.id)
    if name == 'Teacher':    return entity.employee_id
    if name == 'Staff':      return entity.employee_id
    if name == 'Document':   return str(entity.doc_id)
    if name == 'Assignment': return str(entity.assign_id)
    if name == 'LogEntry':   return str(entity.id)
    return str(getattr(entity, 'id', ''))


def _get_headers(entity):
    name = entity.__class__.__name__
    return {
        'Student':    STUDENTS_HEADERS,
        'Teacher':    TEACHERS_HEADERS,
        'Staff':      STAFF_HEADERS,
        'Document':   DOCUMENTS_HEADERS,
        'Assignment': ASSIGNMENTS_HEADERS,
        'LogEntry':   LOGS_HEADERS,
    }.get(name)


# ── Public API ─────────────────────────────────────────────────────────────────
def add_to_sheet(entity, sheet_name):
    """Append a new row for a model instance."""
    client  = get_client()
    headers = _get_headers(entity)
    sheet   = get_or_create_sheet(client, sheet_name=sheet_name, headers=headers)
    sheet.append_row(_build_row(entity), value_input_option="USER_ENTERED",
                     insert_data_option="INSERT_ROWS")
    return True


def update_in_sheet(entity, sheet_name):
    """Find and update an existing row by PK (column A). Falls back to append."""
    client   = get_client()
    headers  = _get_headers(entity)
    num_cols = len(headers)
    sheet    = get_or_create_sheet(client, sheet_name=sheet_name, headers=headers)

    pk_val   = _get_pk_val(entity)
    row_data = _build_row(entity)
    col_end  = chr(64 + num_cols)

    print(f"🔍 update_in_sheet: looking for PK={pk_val} in '{sheet_name}'")

    try:
        col1 = sheet.col_values(1)
        for idx, cell_val in enumerate(col1):
            if idx == 0:
                continue
            if str(cell_val) == pk_val:
                row_num = idx + 1
                sheet.update([row_data], f"A{row_num}:{col_end}{row_num}",
                             value_input_option="USER_ENTERED")
                print(f"✅ Row {row_num} updated in '{sheet_name}'")
                return True
    except Exception as e:
        print(f"⚠️  Error reading col1: {e}")

    print(f"⚠️  PK={pk_val} not found in '{sheet_name}'. Appending.")
    sheet.append_row(row_data, value_input_option="USER_ENTERED",
                     insert_data_option="INSERT_ROWS")
    return False


def delete_from_sheet(entity_id, sheet_name):
    """Delete the row whose column-A value matches entity_id."""
    client = get_client()
    sheet  = get_or_create_sheet(client, sheet_name=sheet_name)
    try:
        col1 = sheet.col_values(1)
        for idx, val in enumerate(col1):
            if idx == 0:
                continue
            if str(val) == str(entity_id):
                sheet.delete_rows(idx + 1)
                return True
    except Exception as e:
        print(f"⚠️  Error in delete_from_sheet: {e}")
    return False


# ── Backwards-compat wrappers ──────────────────────────────────────────────────
def add_student_to_sheet(student):
    return add_to_sheet(student, 'Students')

def update_student_in_sheet(student):
    return update_in_sheet(student, 'Students')

def delete_student_from_sheet(student_id):
    return delete_from_sheet(student_id, 'Students')

def add_teacher_to_sheet(teacher):
    return add_to_sheet(teacher, 'Teachers')

def update_teacher_in_sheet(teacher):
    return update_in_sheet(teacher, 'Teachers')

def delete_teacher_from_sheet(employee_id):
    return delete_from_sheet(employee_id, 'Teachers')

def add_staff_to_sheet(staff):
    return add_to_sheet(staff, 'Staff')

def update_staff_in_sheet(staff):
    return update_in_sheet(staff, 'Staff')

def delete_staff_from_sheet(employee_id):
    return delete_from_sheet(employee_id, 'Staff')
