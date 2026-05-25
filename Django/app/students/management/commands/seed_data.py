"""
Management command: seed_data
Usage: python manage.py seed_data

Creates:
  - 5 Sections (Class 9–11, A/B/C)
  - 10 Teachers (via randomuser.me API)
  - 5 Staff members
  - 30+ Students distributed across sections
  - StudentMarks for multiple terms
  - 3 Announcements
  - Assigns teachers to sections
"""
import random
import requests
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from students.models import (
    Student, Teacher, Staff, Section, Announcement,
    StudentMarks, TeacherSectionAssignment,
    UserProfile, LogEntry,
    ROLE_TEACHER, ROLE_STAFF, ROLE_STUDENT, ROLE_PRINCIPAL,
)
from students.views import CLASS_OPTIONS, COURSE_OPTIONS, SUBJECT_OPTIONS, get_student_curriculum

SECTIONS_TO_CREATE = [(c, s) for c in CLASS_OPTIONS for s in ['A', 'B', 'C', 'D', 'E']]

STAFF_DATA = [
    {"employee_id": "STF001", "name": "Ramesh Gupta",    "email": "ramesh.gupta@school.edu",    "designation": "Accountant",        "department": "Accounts",       "is_admin": True},
    {"employee_id": "STF002", "name": "Sunita Verma",    "email": "sunita.verma@school.edu",    "designation": "Librarian",         "department": "Library",        "is_admin": False},
    {"employee_id": "STF003", "name": "Mohan Das",       "email": "mohan.das@school.edu",       "designation": "Security Guard",    "department": "Security",       "is_admin": False},
    {"employee_id": "STF004", "name": "Priya Singh",     "email": "priya.singh@school.edu",     "designation": "Admin Coordinator", "department": "Administration", "is_admin": True},
    {"employee_id": "STF005", "name": "Arjun Mehta",     "email": "arjun.mehta@school.edu",     "designation": "IT Support",        "department": "IT Support",     "is_admin": False},
]

STUDENT_NAMES = [
    ("Aarav Sharma",     "M"), ("Priya Patel",      "F"), ("Rohan Gupta",      "M"),
    ("Ananya Reddy",     "F"), ("Karan Mehta",      "M"), ("Sneha Joshi",      "F"),
    ("Arjun Kumar",      "M"), ("Divya Nair",       "F"), ("Rahul Singh",      "M"),
    ("Pooja Verma",      "F"), ("Vikram Rao",       "M"), ("Meera Iyer",       "F"),
    ("Aditya Bose",      "M"), ("Kavya Menon",      "F"), ("Siddharth Shah",   "M"),
    ("Riya Chatterjee",  "F"), ("Nikhil Tiwari",    "M"), ("Ishaan Malhotra",  "M"),
    ("Simran Kaur",      "F"), ("Varun Bhatt",      "M"), ("Tanvi Desai",      "F"),
    ("Neeraj Pandey",    "M"), ("Anjali Srivastava","F"), ("Harsh Agarwal",    "M"),
    ("Deepika Pillai",   "F"), ("Ankit Jain",       "M"), ("Neha Saxena",      "F"),
    ("Chirag Bansal",    "M"), ("Shruti Mishra",    "F"), ("Kunal Kapoor",     "M"),
]

TERMS = ['Q1', 'Q2', 'HY1', 'HY2', 'ANN']

ANNOUNCEMENTS = [
    {
        "title": "Annual Sports Day – 15 May 2026",
        "body": "The Annual Sports Day will be held on 15 May 2026 at the school grounds from 9:00 AM. All students must participate in at least one event. Detailed schedule to follow.",
        "audience": "all",
    },
    {
        "title": "Half-Yearly Examination Schedule Released",
        "body": "Half-Yearly examinations will commence from 1 June 2026. Timetables have been shared via teachers. Students are advised to refer to their section notice boards for subject-wise schedules.",
        "audience": "students",
    },
    {
        "title": "Teacher Professional Development – 30 April",
        "body": "A mandatory professional development session will be conducted on 30 April 2026 for all teaching staff. Attendance is compulsory. Substitute arrangements will be made for affected classes.",
        "audience": "teachers",
    },
]


class Command(BaseCommand):
    help = "Seed the database with demo sections, teachers, staff, students, marks, and announcements."

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Delete existing seeded data before creating new.')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write("Clearing existing data…")
            StudentMarks.objects.all().delete()
            TeacherSectionAssignment.objects.all().delete()
            Announcement.objects.filter(created_by__isnull=True).delete()
            Section.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared marks, sections, and announcements."))

        # ── 1. Sections ──────────────────────────────────────────────────────
        self.stdout.write("\n📦  Creating sections…")
        sections = []
        for class_name, sec in SECTIONS_TO_CREATE:
            obj, created = Section.objects.get_or_create(
                class_name=class_name, section=sec,
                defaults={"capacity": 40}
            )
            sections.append(obj)
            tag = "✓ Created" if created else "  Exists"
            self.stdout.write(f"  {tag}  {obj}")

        # ── 2. Teachers from API ─────────────────────────────────────────────
        self.stdout.write("\n👨‍🏫  Fetching teachers from randomuser.me API…")
        api_teachers = []
        try:
            resp = requests.get("https://randomuser.me/api/?results=40&nat=in&seed=edutrack2026", timeout=10)
            api_teachers = resp.json().get("results", [])
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  API failed: {e}. Using fallback teacher data."))

        # Make sure we have exactly 40 subjects to match 40 teachers
        teacher_subjects = (SUBJECT_OPTIONS * 10)[:len(api_teachers) or 40]
        random.shuffle(teacher_subjects)
        created_teachers = []

        for i, subject in enumerate(teacher_subjects):
            emp_id = f"TCH{str(i+1).zfill(3)}"
            if Teacher.objects.filter(employee_id=emp_id).exists():
                t = Teacher.objects.get(employee_id=emp_id)
                created_teachers.append(t)
                self.stdout.write(f"    Exists  {t.name} – {t.subject}")
                continue

            # Build name from API or fallback
            if i < len(api_teachers):
                u = api_teachers[i]
                name = f"{u['name']['first']} {u['name']['last']}"
                email = u['email']
                gender = 'M' if u['gender'] == 'male' else 'F'
                dob = u['dob']['date'][:10]
            else:
                name = f"Teacher {i+1}"
                email = f"teacher{i+1}@school.edu"
                gender = random.choice(['M', 'F'])
                dob = None

            # Ensure unique email
            if Teacher.objects.filter(email=email).exists():
                email = f"teacher_{emp_id}@school.edu"

            # Create Django user for teacher
            username = f"teacher_{emp_id.lower()}"
            user_obj = None
            if not User.objects.filter(username=username).exists():
                user_obj = User.objects.create_user(
                    username=username,
                    email=email,
                    password="teacher@123",
                )
                UserProfile.objects.create(user=user_obj, role=ROLE_TEACHER)

            t = Teacher.objects.create(
                employee_id=emp_id,
                name=name,
                email=email,
                gender=gender,
                date_of_birth=dob,
                subject=subject,
                qualification=random.choice(['B.Ed','M.Ed','PhD','M.Sc']),
                experience_yrs=random.randint(2, 20),
                employment_type=random.choice(['permanent','contract','visiting']),
                date_joined=date.today() - timedelta(days=random.randint(30, 1200)),
                salary=round(random.uniform(25000, 80000), 2),
                user=user_obj,
            )
            created_teachers.append(t)
            self.stdout.write(f"  ✓ Created  {t.name} – {t.subject} (login: {username}/teacher@123)")

        # ── 3. Staff ─────────────────────────────────────────────────────────
        self.stdout.write("\n👷  Creating staff…")
        for sd in STAFF_DATA:
            if Staff.objects.filter(employee_id=sd['employee_id']).exists():
                self.stdout.write(f"    Exists  {sd['name']}")
                continue
            username = f"staff_{sd['employee_id'].lower()}"
            user_obj = None
            if not User.objects.filter(username=username).exists():
                user_obj = User.objects.create_user(
                    username=username, email=sd['email'], password="staff@123"
                )
                UserProfile.objects.create(user=user_obj, role=ROLE_STAFF)
            Staff.objects.create(
                employee_id=sd['employee_id'],
                name=sd['name'],
                email=sd['email'],
                designation=sd['designation'],
                department=sd['department'],
                is_admin_staff=sd['is_admin'],
                employment_type='permanent',
                date_joined=date.today() - timedelta(days=random.randint(60, 900)),
                salary=round(random.uniform(15000, 40000), 2),
                user=user_obj,
            )
            self.stdout.write(f"  ✓ Created  {sd['name']} ({sd['department']}) – login: {username}/staff@123")

        # ── 4. Students distributed across sections ──────────────────────────
        self.stdout.write("\n🎓  Creating students…")
        
        api_students = []
        try:
            resp = requests.get("https://randomuser.me/api/?results=150&nat=in,us,gb&seed=edutrack_students", timeout=10)
            api_students = resp.json().get("results", [])
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  API failed: {e}. Cannot fetch 150 students."))

        created_students = []
        num_students = 150 if api_students else len(STUDENT_NAMES)
        
        for i in range(num_students):
            if api_students:
                u = api_students[i]
                s_name = f"{u['name']['first']} {u['name']['last']}"
                s_gender = 'M' if u['gender'] == 'male' else 'F'
            else:
                s_name, s_gender = STUDENT_NAMES[i % len(STUDENT_NAMES)]

            email = f"{s_name.replace(' ','_').lower()}{i}@student.edu"
            
            # Avoid duplicate emails
            if Student.objects.filter(email=email).exists():
                qs = Student.objects.filter(email=email)
                created_students.append(qs.first())
                self.stdout.write(f"    Exists  {s_name}")
                continue

            section = sections[i % len(sections)]
            marks    = round(random.uniform(40, 98), 1)
            attendance = round(random.uniform(55, 99), 1)
            paid   = random.choice([True, False])
            method = random.choice(['cash','check','online']) if paid else ''
            
            c_name = section.class_name.lower()
            if c_name in ['class 11', 'class 12']:
                course = random.choice(["Medical Science", "Non-Medical Science", "Commerce", "Arts"])
            else:
                course = "General"
                
            adm_no = f"ADM{str(i+1).zfill(4)}"

            username = f"student_{adm_no.lower()}"
            user_obj = None
            if not User.objects.filter(username=username).exists():
                user_obj = User.objects.create_user(
                    username=username, email=email, password="student@123"
                )
                UserProfile.objects.create(user=user_obj, role=ROLE_STUDENT)

            s = Student.objects.create(
                name=s_name,
                age=random.randint(4, 18),
                email=email,
                gender=s_gender,
                course=course,
                class_name=section.class_name,
                section=section,
                fees_paid=paid,
                payment_method=method,
                attendance=attendance,
                marks=marks,
                admission_number=adm_no,
                admission_date=date.today() - timedelta(days=random.randint(30, 365)),
                phone=f"+91 9{random.randint(100000000, 999999999)}",
                user=user_obj,
            )
            created_students.append(s)
            self.stdout.write(f"  ✓ {s.name} → {section} | Marks:{marks}% Att:{attendance}% Fees:{'✓' if paid else '✗'} (login: {username}/student@123)")

        # ── 5. Assign teachers to sections and set class teachers ───────────────────
        self.stdout.write("\n🔗  Assigning teachers to sections…")
        unassigned_teachers = list(created_teachers)
        random.shuffle(unassigned_teachers)
        for sec in sections:
            # Assign a class teacher
            if unassigned_teachers:
                class_teacher = unassigned_teachers.pop(0)
                sec.class_teacher = class_teacher
                sec.save()
                self.stdout.write(f"  👨‍🏫 {class_teacher.name} is now Class Teacher for {sec}")
                # And the class teacher teaches their subject to their class
                TeacherSectionAssignment.objects.get_or_create(teacher=class_teacher, section=sec, subject=class_teacher.subject)
            
            # Assign other subject teachers so the section gets all its subjects
            # But just assign random 2-3 teachers for now simulation
            sample = random.sample(created_teachers, min(3, len(created_teachers)))
            for t in sample:
                obj, created = TeacherSectionAssignment.objects.get_or_create(
                    teacher=t, section=sec, subject=t.subject
                )
                if created:
                    self.stdout.write(f"  ✓ {t.name} → {sec} ({t.subject})")

        # ── 6. Student Marks ──────────────────────────────────────────────────
        self.stdout.write("\n📊  Adding term marks for students…")
        for student in created_students:
            student_curr = get_student_curriculum(student)
            subjects_for_student = student_curr
            terms_for_student    = random.sample(TERMS, min(4, len(TERMS)))
            for subject in subjects_for_student:
                for term in terms_for_student:
                    if StudentMarks.objects.filter(student=student, subject=subject, term=term).exists():
                        continue
                    obtained = round(random.uniform(30, 100), 1)
                    # Find a teacher who teaches this section
                    ta = TeacherSectionAssignment.objects.filter(section=student.section).first()
                    teacher_obj = ta.teacher if ta else None
                    StudentMarks.objects.create(
                        student=student,
                        subject=subject,
                        term=term,
                        max_marks=100,
                        marks_obtained=obtained,
                        recorded_by=teacher_obj,
                    )
            # Recalculate aggregate marks
            from django.db.models import Avg
            agg = student.term_marks.aggregate(avg=Avg('marks_obtained'))
            if agg['avg']:
                student.marks = round(agg['avg'], 1)
                student.save(update_fields=['marks'])
        self.stdout.write(f"  ✓ Marks added for {len(created_students)} students")

        # ── 7. Announcements ──────────────────────────────────────────────────
        self.stdout.write("\n📢  Creating announcements…")
        # Try to get a principal user, or use superuser
        principal_user = User.objects.filter(is_superuser=True).first()
        for ad in ANNOUNCEMENTS:
            if not Announcement.objects.filter(title=ad['title']).exists():
                Announcement.objects.create(
                    title=ad['title'],
                    body=ad['body'],
                    audience=ad['audience'],
                    created_by=principal_user,
                    is_active=True,
                )
                self.stdout.write(f"  ✓ {ad['title']} [{ad['audience']}]")

        # ── 8. Log Entry ──────────────────────────────────────────────────────
        LogEntry.objects.create(
            action='SEED_DATA',
            description=f"Database seeded: {len(sections)} sections, {len(created_teachers)} teachers, {len(created_students)} students.",
            user_id='system',
        )

        self.stdout.write(self.style.SUCCESS(
            f"\n✅  Seeding complete!\n"
            f"   Sections  : {len(sections)}\n"
            f"   Teachers  : {len(created_teachers)}\n"
            f"   Students  : {len(created_students)}\n"
            f"   Staff     : {len(STAFF_DATA)}\n\n"
            f"   Teacher login : teacher_tch001 / teacher@123\n"
            f"   Staff login   : staff_stf001   / staff@123\n"
            f"   Student login : student_adm0001/ student@123\n"
        ))
