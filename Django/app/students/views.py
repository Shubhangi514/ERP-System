import json
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q, Count, Sum
from .models import (Student, Document, Assignment, LogEntry,
                     Teacher, Staff, UserProfile, Section, Announcement,
                     StudentMarks, TeacherSectionAssignment,
                     ROLE_STUDENT, ROLE_TEACHER, ROLE_PRINCIPAL, ROLE_STAFF)
from .google_sheets import (
    add_student_to_sheet, update_student_in_sheet, delete_student_from_sheet,
    add_teacher_to_sheet, update_teacher_in_sheet, delete_teacher_from_sheet,
    add_staff_to_sheet, update_staff_in_sheet, delete_staff_from_sheet,
    add_to_sheet, update_in_sheet, delete_from_sheet,
)

COURSE_OPTIONS = [
    "General", "Medical Science", "Non-Medical Science", "Commerce", "Arts",
]
CLASS_OPTIONS = [
    'Nursery', 'LKG', 'UKG', 'Class 1', 'Class 2', 'Class 3', 'Class 4', 
    'Class 5', 'Class 6', 'Class 7', 'Class 8', 'Class 9', 'Class 10', 
    'Class 11', 'Class 12'
]

# Curriculums
SUBJECTS_JUNIOR = ["English", "Hindi", "EVS", "Mathematics"]
SUBJECTS_MIDDLE = ["English", "Hindi", "Mathematics", "Science", "Social Science", "Sanskrit", "Computer", "Physical Education"]
SUBJECTS_MEDICAL = ["English", "Physics", "Chemistry", "Biology", "Physical Education"]
SUBJECTS_NON_MEDICAL = ["English", "Physics", "Chemistry", "Mathematics", "Computer Science"]
SUBJECTS_COMMERCE = ["English", "Accountancy", "Business Studies", "Economics", "Mathematics"]
SUBJECTS_ARTS = ["English", "History", "Geography", "Political Science", "Hindi"]

# Master list of unique subjects
SUBJECT_OPTIONS = sorted(list(set(
    SUBJECTS_JUNIOR + SUBJECTS_MIDDLE + SUBJECTS_MEDICAL + 
    SUBJECTS_NON_MEDICAL + SUBJECTS_COMMERCE + SUBJECTS_ARTS
)))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
def get_student_curriculum(student):
    if not student.class_name:
        return SUBJECT_OPTIONS
    c = student.class_name.lower()
    if c in ['nursery', 'lkg', 'ukg', 'class 1', 'class 2']:
        return SUBJECTS_JUNIOR
    elif c in ['class 3', 'class 4', 'class 5', 'class 6', 'class 7', 'class 8', 'class 9', 'class 10']:
        return SUBJECTS_MIDDLE
    elif c in ['class 11', 'class 12']:
        stream = student.course
        if stream == 'Medical Science': return SUBJECTS_MEDICAL
        elif stream == 'Non-Medical Science': return SUBJECTS_NON_MEDICAL
        elif stream == 'Commerce': return SUBJECTS_COMMERCE
        elif stream == 'Arts': return SUBJECTS_ARTS
        else: return SUBJECT_OPTIONS
    return SUBJECT_OPTIONS

def get_role(request):
    if request.user.is_authenticated:
        try:
            return request.user.profile.role
        except Exception:
            return None
    return None


def principal_required(view_fn):
    """Decorator: only principals (or superusers) may access the view."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('landing')
        role = get_role(request)
        if role != ROLE_PRINCIPAL and not request.user.is_superuser:
            messages.error(request, 'Access denied. Principal login required.')
            return redirect('landing')
        return view_fn(request, *args, **kwargs)
    wrapper.__name__ = view_fn.__name__
    return wrapper


def teacher_or_principal_required(view_fn):
    """Decorator: teachers and principals only."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('landing')
        role = get_role(request)
        if role not in [ROLE_TEACHER, ROLE_PRINCIPAL] and not request.user.is_superuser:
            messages.error(request, 'Access denied. Teacher or Principal login required.')
            return redirect('dashboard')
        return view_fn(request, *args, **kwargs)
    wrapper.__name__ = view_fn.__name__
    return wrapper


def get_teacher_for_user(user):
    """Return Teacher linked to this user, or None."""
    try:
        return user.teacher_profile
    except Exception:
        pass
    try:
        return Teacher.objects.get(email=user.email)
    except Teacher.DoesNotExist:
        return None


def get_admin_staff_for_user(user):
    """Return admin Staff linked to user, or None."""
    try:
        s = user.staff_profile
        return s if s.is_admin_staff else None
    except Exception:
        return None


def _announcement_qs_for_role(role):
    """Return announcements visible to a given role."""
    from django.db.models import Q as DQ
    qs = Announcement.objects.filter(is_active=True)
    if role == ROLE_STUDENT:
        return qs.filter(audience__in=['all', 'students'])
    elif role == ROLE_TEACHER:
        return qs.filter(audience__in=['all', 'teachers'])
    elif role == ROLE_STAFF:
        return qs.filter(audience__in=['all', 'staff'])
    elif role == ROLE_PRINCIPAL:
        return qs  # sees all
    return qs.filter(audience='all')


# ─────────────────────────────────────────────────────────────────────────────
# Public Landing Page
# ─────────────────────────────────────────────────────────────────────────────
def landing(request):
    if request.user.is_authenticated:
        role = get_role(request)
        if role == ROLE_PRINCIPAL or request.user.is_superuser:
            return redirect('principal_dashboard')
        return redirect('dashboard')
    stats = {
        'total_students': Student.objects.count(),
        'total_teachers': Teacher.objects.count(),
        'total_staff':    Staff.objects.count(),
    }
    return render(request, 'students/landing.html', {'stats': stats})


# ─────────────────────────────────────────────────────────────────────────────
# Auth – Login / Logout (Register removed – only principal can add users)
# ─────────────────────────────────────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('landing')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            role = ROLE_STUDENT
            try:
                role = user.profile.role
            except Exception:
                pass
            if role == ROLE_PRINCIPAL or user.is_superuser:
                return redirect('principal_dashboard')
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')

    return render(request, 'students/login.html')


def register_view(request):
    """Kept for internal use (principal redirect), but removed from public pages."""
    return redirect('login')


def logout_view(request):
    logout(request)
    return redirect('landing')


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard (student / teacher / staff view)
# ─────────────────────────────────────────────────────────────────────────────
def home(request):
    return redirect('landing')


@login_required(login_url='/login/')
def dashboard(request):
    role = get_role(request)

    # ── Student dashboard ────────────────────────────────────────────────────
    if role == ROLE_STUDENT:
        user = request.user
        student = None
        try:
            student = user.student_profile
        except Exception:
            pass
        if not student and user.email:
            student = Student.objects.filter(email=user.email).first()
        if not student and user.username.startswith('student_'):
            try:
                sid = int(user.username.split('_')[1])
                student = Student.objects.filter(id=sid).first()
            except Exception:
                pass
        if not student:
            student = Student.objects.first()

        # Marks per term for this student
        term_marks = {}
        if student:
            for mark in student.term_marks.order_by('term', 'subject'):
                term_marks.setdefault(mark.term, []).append(mark)

        announcements = _announcement_qs_for_role(ROLE_STUDENT)[:10]

        context = {
            'student':       student,
            'user_role':     role,
            'term_marks':    term_marks,
            'announcements': announcements,
        }
        return render(request, 'students/student_dashboard.html', context)

    # ── Staff dashboard – admin staff sees fee data ──────────────────────────
    if role == ROLE_STAFF:
        admin_staff = get_admin_staff_for_user(request.user)
        students_qs = Student.objects.all() if admin_staff else None
        fees_paid   = students_qs.filter(fees_paid=True).count() if students_qs else 0
        fees_unpaid = students_qs.filter(fees_paid=False).count() if students_qs else 0
        announcements = _announcement_qs_for_role(ROLE_STAFF)[:10]
        context = {
            'user_role':    role,
            'admin_staff':  admin_staff,
            'students_qs':  students_qs,
            'fees_paid':    fees_paid,
            'fees_unpaid':  fees_unpaid,
            'announcements': announcements,
        }
        return render(request, 'students/staff_dashboard.html', context)

    # ── Teacher dashboard ────────────────────────────────────────────────────
    teacher = get_teacher_for_user(request.user)
    sections = Section.objects.all()
    section_perf = []
    for sec in sections:
        section_perf.append({
            'section':       sec,
            'avg_marks':     sec.avg_marks,
            'avg_attendance':sec.avg_attendance,
            'student_count': sec.student_count,
        })

    # Section performance comparison (JSON for charts)
    perf_labels  = [str(s['section']) for s in section_perf]
    perf_marks   = [s['avg_marks'] for s in section_perf]
    perf_att     = [s['avg_attendance'] for s in section_perf]

    total_students = Student.objects.count()
    male_count   = Student.objects.filter(gender='M').count()
    female_count = Student.objects.filter(gender='F').count()
    other_count  = Student.objects.filter(gender='O').count()
    fees_paid_ct = Student.objects.filter(fees_paid=True).count()
    agg = Student.objects.aggregate(avg_marks=Avg('marks'), avg_att=Avg('attendance'))
    class_qs  = Student.objects.values('class_name').annotate(count=Count('id')).order_by('class_name')
    course_qs = Student.objects.values('course').annotate(count=Count('id')).order_by('-count')[:8]

    announcements = _announcement_qs_for_role(ROLE_TEACHER)[:10]

    context = {
        'total_students':    total_students,
        'total_documents':   Document.objects.count(),
        'total_assignments': Assignment.objects.count(),
        'total_logs':        LogEntry.objects.count(),
        'recent_logs':       LogEntry.objects.all().order_by('-timestamp')[:10],
        'avg_student_marks': round(agg['avg_marks'] or 0, 1),
        'avg_attendance':    round(agg['avg_att']   or 0, 1),
        'male_count':        male_count,
        'female_count':      female_count,
        'other_count':       other_count,
        'fees_paid_count':   fees_paid_ct,
        'fees_unpaid_count': total_students - fees_paid_ct,
        'class_labels':  json.dumps([d['class_name'] or 'Unassigned' for d in class_qs]),
        'class_counts':  json.dumps([d['count'] for d in class_qs]),
        'course_labels': json.dumps([d['course'] or 'N/A' for d in course_qs]),
        'course_counts': json.dumps([d['count'] for d in course_qs]),
        'user_role':     role,
        'teacher':       teacher,
        'my_class_sections': teacher.class_teacher_sections.all() if teacher else [],
        'my_subject_assignments': teacher.section_assignments.all() if teacher else [],
        'section_perf':  section_perf,
        'perf_labels':   json.dumps(perf_labels),
        'perf_marks':    json.dumps(perf_marks),
        'perf_att':      json.dumps(perf_att),
        'announcements': announcements,
    }
    return render(request, 'students/dashboard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Principal Dashboard
# ─────────────────────────────────────────────────────────────────────────────
@principal_required
def principal_dashboard(request):
    students = Student.objects.all()
    teachers = Teacher.objects.all()
    staff    = Staff.objects.all()
    agg = students.aggregate(avg_marks=Avg('marks'), avg_att=Avg('attendance'))
    sections = Section.objects.all()
    section_perf = []
    for sec in sections:
        section_perf.append({
            'section':       sec,
            'avg_marks':     sec.avg_marks,
            'avg_attendance':sec.avg_attendance,
            'student_count': sec.student_count,
        })
    perf_labels = [str(s['section']) for s in section_perf]
    perf_marks  = [s['avg_marks'] for s in section_perf]
    perf_att    = [s['avg_attendance'] for s in section_perf]

    # Payment method breakdown
    pay_cash   = students.filter(fees_paid=True, payment_method='cash').count()
    pay_check  = students.filter(fees_paid=True, payment_method='check').count()
    pay_online = students.filter(fees_paid=True, payment_method='online').count()

    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')[:10]

    context = {
        'total_students': students.count(),
        'total_teachers': teachers.count(),
        'total_staff':    staff.count(),
        'avg_marks':      round(agg['avg_marks'] or 0, 1),
        'avg_attendance': round(agg['avg_att']   or 0, 1),
        'fees_paid':      students.filter(fees_paid=True).count(),
        'fees_unpaid':    students.filter(fees_paid=False).count(),
        'pay_cash':       pay_cash,
        'pay_check':      pay_check,
        'pay_online':     pay_online,
        'recent_students': students.order_by('-created_at')[:5],
        'recent_teachers': teachers.order_by('-created_at')[:5],
        'recent_staff':    staff.order_by('-created_at')[:5],
        'recent_logs':     LogEntry.objects.all().order_by('-timestamp')[:8],
        'dept_counts': list(Staff.objects.values('department').annotate(count=Count('id')).order_by('-count')),
        'sections':       sections,
        'section_perf':   section_perf,
        'perf_labels':    json.dumps(perf_labels),
        'perf_marks':     json.dumps(perf_marks),
        'perf_att':       json.dumps(perf_att),
        'announcements':  announcements,
    }
    return render(request, 'students/principal_dashboard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Announcement CRUD (Principal + Teacher can create; students can view)
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='/login/')
def announcement_list(request):
    role = get_role(request)
    if role == ROLE_STUDENT:
        qs = _announcement_qs_for_role(ROLE_STUDENT)
    elif role == ROLE_TEACHER:
        qs = _announcement_qs_for_role(ROLE_TEACHER)
    elif role == ROLE_PRINCIPAL or request.user.is_superuser:
        qs = Announcement.objects.filter(is_active=True)
    else:
        qs = Announcement.objects.filter(is_active=True, audience__in=['all', 'staff'])
    return render(request, 'students/announcement_list.html', {
        'announcements': qs, 'user_role': role,
        'can_create': role in [ROLE_TEACHER, ROLE_PRINCIPAL] or request.user.is_superuser,
    })


@login_required(login_url='/login/')
def add_announcement(request):
    role = get_role(request)
    if role not in [ROLE_TEACHER, ROLE_PRINCIPAL] and not request.user.is_superuser:
        messages.error(request, 'Only teachers and principals can post announcements.')
        return redirect('announcement_list')
    if request.method == 'POST':
        title    = request.POST.get('title', '').strip()
        body     = request.POST.get('body', '').strip()
        audience = request.POST.get('audience', 'all')
        if title and body:
            Announcement.objects.create(
                title=title, body=body, audience=audience,
                created_by=request.user
            )
            messages.success(request, 'Announcement posted successfully.')
            if role == ROLE_PRINCIPAL:
                return redirect('principal_dashboard')
            return redirect('dashboard')
        messages.error(request, 'Title and body are required.')
    return render(request, 'students/announcement_form.html', {
        'user_role': role,
        'audiences': Announcement.AUDIENCE_CHOICES,
    })


@principal_required
def delete_announcement(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    ann.is_active = False
    ann.save()
    messages.success(request, 'Announcement removed.')
    return redirect('principal_dashboard')


# ─────────────────────────────────────────────────────────────────────────────
# Section Management
# ─────────────────────────────────────────────────────────────────────────────
@principal_required
def section_list(request):
    sections = Section.objects.all()
    perf = []
    for sec in sections:
        perf.append({
            'section':        sec,
            'avg_marks':      sec.avg_marks,
            'avg_attendance': sec.avg_attendance,
            'student_count':  sec.student_count,
            'teachers':       sec.teacher_assignments.select_related('teacher').all(),
        })
    return render(request, 'students/section_list.html', {
        'sections': sections,
        'perf':     perf,
    })


@principal_required
def add_section(request):
    if request.method == 'POST':
        class_name = request.POST.get('class_name', '').strip()
        section    = request.POST.get('section', '').strip()
        capacity   = int(request.POST.get('capacity', 40) or 40)
        if class_name and section:
            sec, created = Section.objects.get_or_create(
                class_name=class_name, section=section,
                defaults={'capacity': capacity}
            )
            if created:
                messages.success(request, f'Section {sec} created.')
            else:
                messages.warning(request, f'Section {sec} already exists.')
            return redirect('section_list')
        messages.error(request, 'Class and section are required.')
    from .models import SECTION_CHOICES
    return render(request, 'students/section_form.html', {
        'class_options':   [c[0] for c in Section._meta.get_field('class_name').choices],
        'section_choices': SECTION_CHOICES,
    })


@teacher_or_principal_required
def section_detail(request, pk):
    section  = get_object_or_404(Section, pk=pk)
    role = get_role(request)
    
    # Check if teacher is assigned here
    is_class_teacher = False
    is_subject_teacher = False
    my_subject = ""
    if role == ROLE_TEACHER:
        teacher = get_teacher_for_user(request.user)
        is_class_teacher = (section.class_teacher == teacher)
        assignment = TeacherSectionAssignment.objects.filter(section=section, teacher=teacher).first()
        if assignment:
            is_subject_teacher = True
            my_subject = assignment.subject
        # A principal can always view, a teacher must be linked somehow
        if not (is_class_teacher or is_subject_teacher or request.user.is_superuser):
            from django.contrib import messages
            messages.error(request, "You do not have permission to view other sections.")
            return redirect('dashboard')
            
    is_principal = (role == ROLE_PRINCIPAL or request.user.is_superuser)

    students = section.students.all()
    teachers = section.teacher_assignments.select_related('teacher').all()
    # Performance by term
    terms    = ['Q1','Q2','Q3','Q4','HY1','HY2','ANN']
    term_perf = {}
    for t in terms:
        marks = StudentMarks.objects.filter(student__section=section, term=t)
        if marks.exists():
            agg = marks.aggregate(avg=Avg('marks_obtained'))
            term_perf[t] = round(agg['avg'] or 0, 1)
            
    return render(request, 'students/section_detail.html', {
        'section':   section,
        'students':  students,
        'teachers':  teachers,
        'term_perf': term_perf,
        'is_class_teacher': is_class_teacher,
        'is_subject_teacher': is_subject_teacher,
        'my_subject': my_subject,
        'is_principal': is_principal,
        'user_role': role
    })


@principal_required
def assign_teacher_to_section(request, section_pk):
    section = get_object_or_404(Section, pk=section_pk)
    if request.method == 'POST':
        teacher_id = request.POST.get('teacher_id')
        subject    = request.POST.get('subject', '').strip()
        if teacher_id and subject:
            teacher = get_object_or_404(Teacher, pk=teacher_id)
            _, created = TeacherSectionAssignment.objects.get_or_create(
                teacher=teacher, section=section, subject=subject
            )
            if created:
                messages.success(request, f'{teacher.name} assigned to {section} for {subject}.')
            else:
                messages.info(request, 'This assignment already exists.')
            return redirect('section_detail', pk=section_pk)
        messages.error(request, 'Teacher and subject are required.')
    teachers = Teacher.objects.all()
    return render(request, 'students/assign_teacher_section.html', {
        'section':  section,
        'teachers': teachers,
        'subjects': SUBJECT_OPTIONS,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Student Marks (Teacher enters marks; Principal can also view)
# ─────────────────────────────────────────────────────────────────────────────
@teacher_or_principal_required
def enter_marks(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    teacher = get_teacher_for_user(request.user)
    role = get_role(request)
    # Determine allowed subjects
    student_curr = get_student_curriculum(student)
    allowed_subjects = student_curr
    if role == ROLE_TEACHER and teacher:
        # Teacher is class teacher?
        is_class_teacher = (student.section and student.section.class_teacher == teacher)
        # Find which subjects they are assigned to for this student's section
        assignments = TeacherSectionAssignment.objects.filter(teacher=teacher, section=student.section)
        allowed_subjects = [a.subject for a in assignments]
        
        # If they aren't assigned to any subject, and not a class teacher either
        if not allowed_subjects and not is_class_teacher:
            messages.error(request, 'You do not have permission to enter marks for this student.')
            return redirect('section_detail', pk=student.section.pk if student.section else 0)

    if request.method == 'POST':
        subject    = request.POST.get('subject', '').strip()
        term       = request.POST.get('term', '').strip()
        max_marks  = float(request.POST.get('max_marks', 100) or 100)
        obtained   = request.POST.get('marks_obtained', '').strip()
        remarks    = request.POST.get('remarks', '').strip() or None
        
        # Validation for subjects
        if role == ROLE_TEACHER and subject not in allowed_subjects:
            messages.error(request, f'You are not authorized to assign marks for {subject}.')
            return redirect('enter_marks', student_id=student_id)
            
        if subject and term and obtained:
            try:
                obtained = float(obtained)
                mark, created = StudentMarks.objects.update_or_create(
                    student=student, subject=subject, term=term,
                    defaults={
                        'max_marks': max_marks,
                        'marks_obtained': obtained,
                        'recorded_by': teacher,
                        'remarks': remarks,
                    }
                )
                messages.success(request, f'Marks for {student.name} – {subject} ({term}) saved.')
                # Update the aggregated marks on the student model
                _recalculate_student_marks(student)
            except (ValueError, TypeError) as e:
                messages.error(request, f'Invalid marks value: {e}')
        else:
            messages.error(request, 'Subject, term, and marks are required.')
        return redirect('enter_marks', student_id=student_id)

    existing_marks = student.term_marks.all().order_by('term', 'subject')
    return render(request, 'students/enter_marks.html', {
        'student':        student,
        'existing_marks': existing_marks,
        'subjects':       allowed_subjects,
        'terms':          StudentMarks.TERM_CHOICES,
        'user_role':      role,
        'is_class_teacher': (student.section and student.section.class_teacher == teacher) if teacher else False,
    })


def _recalculate_student_marks(student):
    """Update the aggregated marks field on the Student model."""
    agg = student.term_marks.aggregate(avg=Avg('marks_obtained'))
    if agg['avg'] is not None:
        student.marks = round(agg['avg'], 1)
        student.save(update_fields=['marks'])


@teacher_or_principal_required
def section_performance(request):
    """Compare sections' academic performance."""
    sections = Section.objects.all()
    perf = []
    for sec in sections:
        students  = sec.students.all()
        marks_agg = StudentMarks.objects.filter(student__section=sec).aggregate(avg=Avg('marks_obtained'))
        att_agg   = students.aggregate(avg=Avg('attendance'))
        term_data = {}
        for term_code, term_label in StudentMarks.TERM_CHOICES:
            t_agg = StudentMarks.objects.filter(student__section=sec, term=term_code).aggregate(avg=Avg('marks_obtained'))
            term_data[term_code] = round(t_agg['avg'] or 0, 1)
        perf.append({
            'section':       sec,
            'avg_marks':     round(marks_agg['avg'] or 0, 1),
            'avg_attendance':round(att_agg['avg'] or 0, 1),
            'student_count': students.count(),
            'term_data':     term_data,
        })

    # Chart data
    perf_labels   = [str(p['section']) for p in perf]
    perf_marks    = [p['avg_marks'] for p in perf]
    perf_att      = [p['avg_attendance'] for p in perf]

    # Best & worst section
    best   = max(perf, key=lambda x: x['avg_marks']) if perf else None
    worst  = min(perf, key=lambda x: x['avg_marks']) if perf else None

    return render(request, 'students/section_performance.html', {
        'perf':         perf,
        'perf_labels':  json.dumps(perf_labels),
        'perf_marks':   json.dumps(perf_marks),
        'perf_att':     json.dumps(perf_att),
        'best_section': best,
        'worst_section':worst,
        'terms':        StudentMarks.TERM_CHOICES,
        'user_role':    get_role(request),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Fee Management (Admin Staff only)
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='/login/')
def fee_management(request):
    role = get_role(request)
    # Allow admin staff and principal
    if role not in [ROLE_PRINCIPAL] and not request.user.is_superuser:
        if role == ROLE_STAFF:
            admin_staff = get_admin_staff_for_user(request.user)
            if not admin_staff:
                messages.error(request, 'Only administrative staff can access fee records.')
                return redirect('dashboard')
        else:
            messages.error(request, 'Access denied.')
            return redirect('dashboard')

    qs = Student.objects.all()
    q         = request.GET.get('q', '').strip()
    cls_f     = request.GET.get('class_name', '').strip()
    fee_f     = request.GET.get('fee_status', '').strip()
    method_f  = request.GET.get('payment_method', '').strip()
    if q:        qs = qs.filter(Q(name__icontains=q) | Q(admission_number__icontains=q))
    if cls_f:    qs = qs.filter(class_name=cls_f)
    if fee_f == 'paid':   qs = qs.filter(fees_paid=True)
    if fee_f == 'unpaid': qs = qs.filter(fees_paid=False)
    if method_f: qs = qs.filter(payment_method=method_f)

    total = qs.count()
    paid   = qs.filter(fees_paid=True).count()
    unpaid = qs.filter(fees_paid=False).count()
    cash_c   = qs.filter(fees_paid=True, payment_method='cash').count()
    check_c  = qs.filter(fees_paid=True, payment_method='check').count()
    online_c = qs.filter(fees_paid=True, payment_method='online').count()

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        paid_flag  = request.POST.get('fees_paid') == 'on'
        method     = request.POST.get('payment_method', '')
        student    = get_object_or_404(Student, id=student_id)
        student.fees_paid      = paid_flag
        student.payment_method = method if paid_flag else ''
        student.save(update_fields=['fees_paid', 'payment_method'])
        LogEntry.objects.create(
            action='UPDATE_FEE',
            description=f'Fee status updated for "{student.name}": {"Paid via " + method if paid_flag else "Unpaid"}',
            user_id=request.user.username
        )
        messages.success(request, f'Fee status updated for {student.name}.')
        return redirect('fee_management')

    return render(request, 'students/fee_management.html', {
        'students':    qs,
        'total':       total,
        'paid':        paid,
        'unpaid':      unpaid,
        'cash_count':  cash_c,
        'check_count': check_c,
        'online_count':online_c,
        'classes':     CLASS_OPTIONS,
        'user_role':   role,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Admission Workflow (Principal only)
# ─────────────────────────────────────────────────────────────────────────────
@principal_required
def admission_list(request):
    students = Student.objects.all().order_by('-created_at')
    # Filter by admission status (has admission_number = admitted)
    filter_f = request.GET.get('filter', '').strip()
    if filter_f == 'admitted':
        students = students.filter(admission_number__isnull=False)
    elif filter_f == 'pending':
        students = students.filter(admission_number__isnull=True)
    return render(request, 'students/admission_list.html', {
        'students': students,
        'filter': filter_f,
    })


@principal_required
def complete_admission(request, student_id):
    """Assign a section and generate admission number."""
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        section_id = request.POST.get('section_id')
        adm_number = request.POST.get('admission_number', '').strip()
        adm_date   = request.POST.get('admission_date') or None
        if section_id:
            section = get_object_or_404(Section, pk=section_id)
            student.section        = section
            student.class_name     = section.class_name
            student.admission_number = adm_number or f"ADM{student.id:04d}"
            student.admission_date  = adm_date
            student.save(update_fields=['section','class_name','admission_number','admission_date'])
            LogEntry.objects.create(
                action='ADMISSION_COMPLETE',
                description=f'Admitted "{student.name}" to {section} (#{student.admission_number})',
                user_id=request.user.username
            )
            messages.success(request, f'Admission complete for {student.name} – Admission No: {student.admission_number}')
            return redirect('admission_list')
        messages.error(request, 'Please select a section.')
    sections = Section.objects.all()
    return render(request, 'students/complete_admission.html', {
        'student':  student,
        'sections': sections,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Teacher Management (Principal only)
# ─────────────────────────────────────────────────────────────────────────────
@principal_required
def teacher_list(request):
    qs = Teacher.objects.all()
    q           = request.GET.get('q',      '').strip()
    subject_f   = request.GET.get('subject','').strip()
    emp_type    = request.GET.get('emp_type','').strip()
    gender_f    = request.GET.get('gender', '').strip()
    sort        = request.GET.get('sort',   'name').strip()

    if q:          qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(employee_id__icontains=q))
    if subject_f:  qs = qs.filter(subject__icontains=subject_f)
    if emp_type:   qs = qs.filter(employment_type=emp_type)
    if gender_f:   qs = qs.filter(gender=gender_f)

    allowed = {'name','-name','subject','-subject','experience_yrs','-experience_yrs','date_joined','-date_joined'}
    if sort not in allowed: sort = 'name'
    qs = qs.order_by(sort)

    subjects = Teacher.objects.values_list('subject', flat=True).distinct().order_by('subject')
    return render(request, 'students/teacher_list.html', {
        'teachers':         qs,
        'total_count':      Teacher.objects.count(),
        'shown_count':      qs.count(),
        'subjects':         subjects,
        'employment_types': Teacher.EMPLOYMENT_CHOICES,
    })


@principal_required
def teacher_detail(request, pk):
    teacher  = get_object_or_404(Teacher, pk=pk)
    sections = teacher.section_assignments.select_related('section').all()
    return render(request, 'students/teacher_detail.html', {
        'teacher': teacher,
        'sections': sections,
    })


@principal_required
def add_teacher(request):
    if request.method == 'POST':
        try:
            username   = request.POST.get('username', '').strip()
            password   = request.POST.get('password', '').strip()
            t = Teacher(
                employee_id    = request.POST.get('employee_id', '').strip(),
                name           = request.POST.get('name', '').strip(),
                email          = request.POST.get('email', '').strip(),
                phone          = request.POST.get('phone', '').strip() or None,
                gender         = request.POST.get('gender', 'M'),
                date_of_birth  = request.POST.get('date_of_birth') or None,
                address        = request.POST.get('address', '').strip() or None,
                subject        = request.POST.get('subject', '').strip(),
                classes_taught = request.POST.get('classes_taught', '').strip() or None,
                qualification  = request.POST.get('qualification', 'B.Ed'),
                experience_yrs = int(request.POST.get('experience_yrs', 0) or 0),
                specialization = request.POST.get('specialization', '').strip() or None,
                employment_type= request.POST.get('employment_type', 'permanent'),
                date_joined    = request.POST.get('date_joined') or None,
                salary         = request.POST.get('salary') or None,
                bio            = request.POST.get('bio', '').strip() or None,
                achievements   = request.POST.get('achievements', '').strip() or None,
            )
            if 'profile_picture' in request.FILES:
                t.profile_picture = request.FILES['profile_picture']
            # Create Django user account if username provided
            if username and password:
                if User.objects.filter(username=username).exists():
                    messages.error(request, f'Username "{username}" already taken.')
                    raise ValueError('duplicate username')
                user = User.objects.create_user(username=username, email=t.email, password=password)
                UserProfile.objects.create(user=user, role=ROLE_TEACHER)
                t.user = user
            t.save()
            try: add_teacher_to_sheet(t)
            except Exception: traceback.print_exc()
            log = LogEntry(action='ADD_TEACHER', description=f'Added teacher "{t.name}" (ID: {t.employee_id})', user_id=request.user.username)
            log.save()
            try: add_to_sheet(log, 'Log/History')
            except Exception: traceback.print_exc()
            messages.success(request, f'Teacher "{t.name}" added successfully.')
            return redirect('teacher_list')
        except Exception as e:
            if 'duplicate username' not in str(e):
                messages.error(request, f'Error: {e}')
    return render(request, 'students/teacher_form.html', {
        'form_title': 'Add New Teacher',
        'qualifications': Teacher.QUALIFICATION_CHOICES,
        'employment_types': Teacher.EMPLOYMENT_CHOICES,
        'class_options': CLASS_OPTIONS,
        'subject_options': SUBJECT_OPTIONS,
    })


@principal_required
def edit_teacher(request, pk):
    t = get_object_or_404(Teacher, pk=pk)
    if request.method == 'POST':
        try:
            t.name           = request.POST.get('name', t.name).strip()
            t.email          = request.POST.get('email', t.email).strip()
            t.phone          = request.POST.get('phone', '').strip() or None
            t.gender         = request.POST.get('gender', t.gender)
            t.date_of_birth  = request.POST.get('date_of_birth') or None
            t.address        = request.POST.get('address', '').strip() or None
            t.subject        = request.POST.get('subject', t.subject).strip()
            t.classes_taught = request.POST.get('classes_taught', '').strip() or None
            t.qualification  = request.POST.get('qualification', t.qualification)
            t.experience_yrs = int(request.POST.get('experience_yrs', t.experience_yrs) or 0)
            t.specialization = request.POST.get('specialization', '').strip() or None
            t.employment_type= request.POST.get('employment_type', t.employment_type)
            t.date_joined    = request.POST.get('date_joined') or None
            t.salary         = request.POST.get('salary') or None
            t.bio            = request.POST.get('bio', '').strip() or None
            t.achievements   = request.POST.get('achievements', '').strip() or None
            if 'profile_picture' in request.FILES:
                t.profile_picture = request.FILES['profile_picture']
            t.save()
            
            # Update roles
            new_class_section_id = request.POST.get('class_teacher_section')
            if new_class_section_id != None: # meaning it's in the form
                # clear old
                Section.objects.filter(class_teacher=t).update(class_teacher=None)
                if new_class_section_id:
                    new_sec = Section.objects.get(pk=new_class_section_id)
                    new_sec.class_teacher = t
                    new_sec.save()
            
            subject_sections = request.POST.getlist('subject_teacher_sections')
            if subject_sections or 'subject_teacher_sections' in request.POST:
                TeacherSectionAssignment.objects.filter(teacher=t).delete()
                for sec_id in subject_sections:
                    if sec_id:
                        sec = Section.objects.get(pk=sec_id)
                        TeacherSectionAssignment.objects.create(teacher=t, section=sec, subject=t.subject)

            try: update_teacher_in_sheet(t)
            except Exception: traceback.print_exc()
            messages.success(request, f'Teacher "{t.name}" updated.')
            return redirect('teacher_detail', pk=t.pk)
        except Exception as e:
            messages.error(request, f'Error: {e}')
    
    all_sections = Section.objects.all()
    current_class_section = Section.objects.filter(class_teacher=t).first()
    current_subject_sections = TeacherSectionAssignment.objects.filter(teacher=t).values_list('section_id', flat=True)
    
    return render(request, 'students/teacher_form.html', {
        'form_title': f'Edit Teacher – {t.name}',
        'teacher': t,
        'qualifications': Teacher.QUALIFICATION_CHOICES,
        'employment_types': Teacher.EMPLOYMENT_CHOICES,
        'class_options': CLASS_OPTIONS,
        'subject_options': SUBJECT_OPTIONS,
        'all_sections': all_sections,
        'current_class_section': current_class_section,
        'current_subject_sections': current_subject_sections,
        'is_edit': True,
    })


@principal_required
def delete_teacher(request, pk):
    t = get_object_or_404(Teacher, pk=pk)
    if request.method == 'POST':
        name = t.name
        eid  = t.employee_id
        try: delete_teacher_from_sheet(eid)
        except Exception: traceback.print_exc()
        t.delete()
        log = LogEntry(action='DELETE_TEACHER', description=f'Deleted teacher "{name}" ({eid})', user_id=request.user.username)
        log.save()
        try: add_to_sheet(log, 'Log/History')
        except Exception: traceback.print_exc()
        messages.success(request, f'Teacher "{name}" deleted.')
    return redirect('teacher_list')


# ─────────────────────────────────────────────────────────────────────────────
# Staff Management (Principal only)
# ─────────────────────────────────────────────────────────────────────────────
@principal_required
def staff_list(request):
    qs = Staff.objects.all()
    q        = request.GET.get('q',         '').strip()
    dept_f   = request.GET.get('department','').strip()
    emp_type = request.GET.get('emp_type',  '').strip()
    gender_f = request.GET.get('gender',    '').strip()
    sort     = request.GET.get('sort',      'name').strip()

    if q:          qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(employee_id__icontains=q) | Q(designation__icontains=q))
    if dept_f:     qs = qs.filter(department=dept_f)
    if emp_type:   qs = qs.filter(employment_type=emp_type)
    if gender_f:   qs = qs.filter(gender=gender_f)

    allowed = {'name','-name','department','-department','designation','-designation','date_joined','-date_joined'}
    if sort not in allowed: sort = 'name'
    qs = qs.order_by(sort)

    return render(request, 'students/staff_list.html', {
        'staff':            qs,
        'total_count':      Staff.objects.count(),
        'shown_count':      qs.count(),
        'departments':      Staff.DEPARTMENT_CHOICES,
        'employment_types': Staff.EMPLOYMENT_CHOICES,
    })


@principal_required
def staff_detail(request, pk):
    member = get_object_or_404(Staff, pk=pk)
    return render(request, 'students/staff_detail.html', {'member': member})


@principal_required
def add_staff(request):
    if request.method == 'POST':
        try:
            username   = request.POST.get('username', '').strip()
            password   = request.POST.get('password', '').strip()
            is_admin   = request.POST.get('is_admin_staff') == 'on'
            s = Staff(
                employee_id     = request.POST.get('employee_id', '').strip(),
                name            = request.POST.get('name', '').strip(),
                email           = request.POST.get('email', '').strip(),
                phone           = request.POST.get('phone', '').strip() or None,
                gender          = request.POST.get('gender', 'M'),
                date_of_birth   = request.POST.get('date_of_birth') or None,
                address         = request.POST.get('address', '').strip() or None,
                designation     = request.POST.get('designation', '').strip(),
                department      = request.POST.get('department', 'Administration'),
                work_description= request.POST.get('work_description', '').strip() or None,
                employment_type = request.POST.get('employment_type', 'permanent'),
                date_joined     = request.POST.get('date_joined') or None,
                salary          = request.POST.get('salary') or None,
                qualification   = request.POST.get('qualification', '').strip() or None,
                bio             = request.POST.get('bio', '').strip() or None,
                is_admin_staff  = is_admin,
            )
            if 'profile_picture' in request.FILES:
                s.profile_picture = request.FILES['profile_picture']
            if username and password:
                if User.objects.filter(username=username).exists():
                    messages.error(request, f'Username "{username}" already taken.')
                    raise ValueError('duplicate username')
                user = User.objects.create_user(username=username, email=s.email, password=password)
                UserProfile.objects.create(user=user, role=ROLE_STAFF)
                s.user = user
            s.save()
            try: add_staff_to_sheet(s)
            except Exception: traceback.print_exc()
            log = LogEntry(action='ADD_STAFF', description=f'Added staff "{s.name}" ({s.employee_id})', user_id=request.user.username)
            log.save()
            try: add_to_sheet(log, 'Log/History')
            except Exception: traceback.print_exc()
            messages.success(request, f'Staff member "{s.name}" added successfully.')
            return redirect('staff_list')
        except Exception as e:
            if 'duplicate username' not in str(e):
                messages.error(request, f'Error: {e}')
    return render(request, 'students/staff_form.html', {
        'form_title':       'Add New Staff Member',
        'departments':      Staff.DEPARTMENT_CHOICES,
        'employment_types': Staff.EMPLOYMENT_CHOICES,
    })


@principal_required
def edit_staff(request, pk):
    s = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        try:
            s.name             = request.POST.get('name', s.name).strip()
            s.email            = request.POST.get('email', s.email).strip()
            s.phone            = request.POST.get('phone', '').strip() or None
            s.gender           = request.POST.get('gender', s.gender)
            s.date_of_birth    = request.POST.get('date_of_birth') or None
            s.address          = request.POST.get('address', '').strip() or None
            s.designation      = request.POST.get('designation', s.designation).strip()
            s.department       = request.POST.get('department', s.department)
            s.work_description = request.POST.get('work_description', '').strip() or None
            s.employment_type  = request.POST.get('employment_type', s.employment_type)
            s.date_joined      = request.POST.get('date_joined') or None
            s.salary           = request.POST.get('salary') or None
            s.qualification    = request.POST.get('qualification', '').strip() or None
            s.bio              = request.POST.get('bio', '').strip() or None
            s.is_admin_staff   = request.POST.get('is_admin_staff') == 'on'
            if 'profile_picture' in request.FILES:
                s.profile_picture = request.FILES['profile_picture']
            s.save()
            try: update_staff_in_sheet(s)
            except Exception: traceback.print_exc()
            messages.success(request, f'Staff member "{s.name}" updated.')
            return redirect('staff_detail', pk=s.pk)
        except Exception as e:
            messages.error(request, f'Error: {e}')
    return render(request, 'students/staff_form.html', {
        'form_title':       f'Edit Staff – {s.name}',
        'member':           s,
        'departments':      Staff.DEPARTMENT_CHOICES,
        'employment_types': Staff.EMPLOYMENT_CHOICES,
    })


@principal_required
def delete_staff(request, pk):
    s = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        name = s.name
        eid  = s.employee_id
        try: delete_staff_from_sheet(eid)
        except Exception: traceback.print_exc()
        s.delete()
        log = LogEntry(action='DELETE_STAFF', description=f'Deleted staff "{name}" ({eid})', user_id=request.user.username)
        log.save()
        try: add_to_sheet(log, 'Log/History')
        except Exception: traceback.print_exc()
        messages.success(request, f'Staff member "{name}" deleted.')
    return redirect('staff_list')


# ─────────────────────────────────────────────────────────────────────────────
# Student CRUD
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='/login/')
def student_list(request):
    role = get_role(request)
    qs = Student.objects.all()
    total_count    = qs.count()
    agg            = qs.aggregate(avg_marks=Avg('marks'), avg_attendance=Avg('attendance'))
    avg_marks      = agg['avg_marks']      or 0
    avg_attendance = agg['avg_attendance'] or 0
    courses = Student.objects.values_list('course',     flat=True).distinct().order_by('course')
    classes = Student.objects.values_list('class_name', flat=True).distinct().order_by('class_name')
    q             = request.GET.get('q',          '').strip()
    age_min       = request.GET.get('age_min',    '').strip()
    age_max       = request.GET.get('age_max',    '').strip()
    marks_min     = request.GET.get('marks_min',  '').strip()
    marks_max     = request.GET.get('marks_max',  '').strip()
    att_min       = request.GET.get('att_min',    '').strip()
    att_max       = request.GET.get('att_max',    '').strip()
    course        = request.GET.get('course',     '').strip()
    class_filter  = request.GET.get('class_name', '').strip()
    gender_filter = request.GET.get('gender',     '').strip()
    fees_filter   = request.GET.get('fees_paid',  '').strip()
    date_from     = request.GET.get('date_from',  '').strip()
    date_to       = request.GET.get('date_to',    '').strip()
    sort          = request.GET.get('sort',       '-created_at').strip()
    if q:             qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q))
    if age_min:       qs = qs.filter(age__gte=age_min)
    if age_max:       qs = qs.filter(age__lte=age_max)
    if marks_min:     qs = qs.filter(marks__gte=marks_min)
    if marks_max:     qs = qs.filter(marks__lte=marks_max)
    if att_min:       qs = qs.filter(attendance__gte=att_min)
    if att_max:       qs = qs.filter(attendance__lte=att_max)
    if course:        qs = qs.filter(course=course)
    if class_filter:  qs = qs.filter(class_name=class_filter)
    if gender_filter: qs = qs.filter(gender=gender_filter)
    if fees_filter == 'paid':   qs = qs.filter(fees_paid=True)
    if fees_filter == 'unpaid': qs = qs.filter(fees_paid=False)
    if date_from:     qs = qs.filter(created_at__date__gte=date_from)
    if date_to:       qs = qs.filter(created_at__date__lte=date_to)
    allowed_sorts = {'name','-name','age','-age','marks','-marks','attendance','-attendance','created_at','-created_at'}
    if sort not in allowed_sorts: sort = '-created_at'
    qs = qs.order_by(sort)
    return render(request, 'students/list.html', {
        'students': qs, 'total_count': total_count,
        'avg_marks': avg_marks, 'avg_attendance': avg_attendance,
        'shown_count': qs.count(), 'courses': courses, 'classes': classes,
        'user_role': role,
    })


@principal_required
def add_student(request):
    """Only principal can add students."""
    if request.method == 'POST':
        name       = request.POST.get('name',       '').strip()
        age        = request.POST.get('age',        '').strip()
        email      = request.POST.get('email',      '').strip()
        gender     = request.POST.get('gender',     'M').strip()
        course     = request.POST.get('course',     '').strip()
        class_name = request.POST.get('class_name', '').strip() or None
        section_id = request.POST.get('section_id', '').strip() or None
        address    = request.POST.get('address',    '').strip() or None
        attendance = request.POST.get('attendance', '0').strip()
        marks      = request.POST.get('marks',      '0').strip()
        phone      = request.POST.get('phone',      '').strip() or None
        username   = request.POST.get('username',   '').strip()
        password   = request.POST.get('password',   '').strip()
        admission_number = request.POST.get('admission_number', '').strip() or None
        admission_date   = request.POST.get('admission_date') or None

        profile_picture = request.FILES.get('profile_picture')
        resume          = request.FILES.get('resume')
        if not all([name, age, email, course]):
            return render(request, 'students/add.html', {
                'error_message': 'Name, Age, Email and Course are required.',
                'course_options': COURSE_OPTIONS, 'class_options': CLASS_OPTIONS,
                'sections': Section.objects.all(),
            })
        section_obj = None
        if section_id:
            section_obj = Section.objects.filter(pk=section_id).first()
            if section_obj:
                class_name = section_obj.class_name

        # Create Django user account for student
        user_obj = None
        if username and password:
            if User.objects.filter(username=username).exists():
                messages.error(request, f'Username "{username}" already taken.')
                return render(request, 'students/add.html', {
                    'course_options': COURSE_OPTIONS, 'class_options': CLASS_OPTIONS,
                    'sections': Section.objects.all(),
                })
            user_obj = User.objects.create_user(username=username, email=email, password=password)
            UserProfile.objects.create(user=user_obj, role=ROLE_STUDENT)

        student = Student(name=name, age=age, email=email, gender=gender,
            course=course, class_name=class_name, section=section_obj, address=address,
            fees_paid=False, attendance=attendance, marks=marks,
            phone=phone, profile_picture=profile_picture, resume=resume,
            admission_number=admission_number, admission_date=admission_date,
            user=user_obj)
        student.save()
        if not admission_number:
            student.admission_number = f"ADM{student.id:04d}"
            student.save(update_fields=['admission_number'])
        try: add_student_to_sheet(student)
        except Exception: traceback.print_exc()
        log = LogEntry(action='ADD_STUDENT', description=f'Added student "{name}" (ID: {student.id})', user_id=request.user.username)
        log.save()
        try: add_to_sheet(log, 'Log/History')
        except Exception: traceback.print_exc()
        messages.success(request, f'Student "{name}" admitted successfully. Admission No: {student.admission_number}')
        return redirect('students_list')
    return render(request, 'students/add.html', {
        'class_options': CLASS_OPTIONS,
        'course_options': COURSE_OPTIONS,
        'sections': Section.objects.all(),
    })


@login_required(login_url='/login/')
def edit_student(request, student_id):
    role = get_role(request)
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        student.name       = request.POST.get('name',       student.name).strip()
        student.age        = request.POST.get('age',        student.age)
        student.email      = request.POST.get('email',      student.email).strip()
        student.gender     = request.POST.get('gender',     student.gender)
        student.course     = request.POST.get('course',     student.course).strip()
        student.class_name = request.POST.get('class_name', student.class_name) or None
        student.address    = request.POST.get('address',    student.address or '').strip() or None
        student.attendance = request.POST.get('attendance', student.attendance)
        student.marks      = request.POST.get('marks',      student.marks)
        student.phone      = request.POST.get('phone',      student.phone or '').strip() or None
        # Only principal/admin-staff can change fee status
        if role in [ROLE_PRINCIPAL] or request.user.is_superuser:
            student.fees_paid  = request.POST.get('fees_paid') == 'on'
            student.payment_method = request.POST.get('payment_method', '')
        if 'profile_picture' in request.FILES:
            student.profile_picture = request.FILES['profile_picture']
        if 'resume' in request.FILES:
            student.resume = request.FILES['resume']
        student.save()
        try: update_student_in_sheet(student)
        except Exception: traceback.print_exc()
        log = LogEntry(action='UPDATE_STUDENT', description=f'Updated student "{student.name}" (ID: {student.id})', user_id=request.user.username)
        log.save()
        try: add_to_sheet(log, 'Log/History')
        except Exception: traceback.print_exc()
        messages.success(request, f'Student "{student.name}" updated successfully.')
        return redirect('students_list')
    return render(request, 'students/edit.html', {
        'student': student, 'course_options': COURSE_OPTIONS, 'class_options': CLASS_OPTIONS,
        'sections': Section.objects.all(), 'user_role': role,
    })


@login_required(login_url='/login/')
def partial_update(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        updated_fields = []
        checks = [
            ('update_name','name','Name',lambda v: setattr(student,'name',v)),
            ('update_age','age','Age',lambda v: setattr(student,'age',v)),
            ('update_email','email','Email',lambda v: setattr(student,'email',v)),
            ('update_course','course','Course',lambda v: setattr(student,'course',v)),
            ('update_attendance','attendance','Attendance',lambda v: setattr(student,'attendance',v)),
            ('update_marks','marks','Marks',lambda v: setattr(student,'marks',v)),
        ]
        for flag, field_name, label, setter in checks:
            if request.POST.get(flag) == '1':
                val = request.POST.get(field_name, '').strip()
                if val:
                    setter(val)
                    updated_fields.append(label)
        if request.POST.get('update_gender') == '1':
            val = request.POST.get('gender', '').strip()
            if val: student.gender = val; updated_fields.append('Gender')
        if request.POST.get('update_class') == '1':
            student.class_name = request.POST.get('class_name', '').strip() or None
            updated_fields.append('Class')
        if updated_fields:
            student.save()
            try: update_student_in_sheet(student)
            except Exception: traceback.print_exc()
            log = LogEntry(action='UPDATE_PARTIAL_STUDENT',
                           description=f'Partial update "{student.name}": {", ".join(updated_fields)} (ID: {student.id})',
                           user_id=request.user.username)
            log.save()
            try: add_to_sheet(log, 'Log/History')
            except Exception: traceback.print_exc()
            messages.success(request, f'Updated {", ".join(updated_fields)} for "{student.name}".')
        else:
            messages.warning(request, 'No fields were selected to update.')
        return redirect('students_list')
    return render(request, 'students/partial_update.html', {
        'student': student, 'course_options': COURSE_OPTIONS, 'class_options': CLASS_OPTIONS,
    })


@principal_required
def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        name = student.name
        sid  = student.id
        try: delete_from_sheet(sid, 'Students')
        except Exception: traceback.print_exc()
        student.delete()
        log = LogEntry(action='DELETE_STUDENT', description=f'Deleted student "{name}" (ID: {sid})', user_id=request.user.username)
        log.save()
        try: add_to_sheet(log, 'Log/History')
        except Exception: traceback.print_exc()
        messages.success(request, f'Student "{name}" deleted successfully.')
    return redirect('students_list')


# ─────────────────────────────────────────────────────────────────────────────
# Documents / Assignments / Logs
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='/login/')
def documents_list(request):
    qs = Document.objects.select_related('student').all()
    total_count  = qs.count()
    q            = request.GET.get('q',          '').strip()
    doc_type     = request.GET.get('doc_type',   '').strip()
    class_filter = request.GET.get('class_name', '').strip()
    sort         = request.GET.get('sort',       '-upload_date').strip()
    if q:         qs = qs.filter(Q(student__name__icontains=q) | Q(doc_type__icontains=q))
    if doc_type:  qs = qs.filter(doc_type=doc_type)
    if class_filter: qs = qs.filter(student__class_name=class_filter)
    allowed_sorts = {'student__name','-student__name','doc_type','-doc_type','upload_date','-upload_date'}
    if sort not in allowed_sorts: sort = '-upload_date'
    qs = qs.order_by('student__class_name', sort)
    classes = Student.objects.values_list('class_name', flat=True).distinct().order_by('class_name')
    return render(request, 'students/documents_list.html', {
        'documents': qs, 'total_count': total_count,
        'shown_count': qs.count(), 'doc_types': Document.DOC_TYPES, 'classes': classes,
    })


@login_required(login_url='/login/')
def add_document(request):
    students = Student.objects.all().order_by('class_name', 'name')
    if request.method == 'POST':
        student_id    = request.POST.get('student_id')
        doc_type      = request.POST.get('doc_type')
        document_file = request.FILES.get('document_file')
        if student_id and doc_type and document_file:
            student  = get_object_or_404(Student, id=student_id)
            document = Document(student=student, doc_type=doc_type, document_file=document_file)
            document.save()
            try: add_to_sheet(document, 'Documents')
            except Exception: traceback.print_exc()
            log = LogEntry(action='ADD_DOCUMENT',
                           description=f'Added {doc_type} for "{student.name}" (DocID: {document.doc_id})',
                           user_id=request.user.username)
            log.save()
            try: add_to_sheet(log, 'Log/History')
            except Exception: traceback.print_exc()
            messages.success(request, f'Document added for {student.name}.')
            return redirect('documents_list')
        else:
            messages.error(request, 'Student, document type, and PDF file are all required.')
    return render(request, 'students/documents_add.html', {'students': students})


@login_required(login_url='/login/')
def assignments_list(request):
    qs = Assignment.objects.select_related('student').all()
    total_count = qs.count()
    q      = request.GET.get('q',      '').strip()
    status = request.GET.get('status', '').strip()
    sort   = request.GET.get('sort',   '-assign_id').strip()
    if q:      qs = qs.filter(Q(student__name__icontains=q) | Q(subject__icontains=q))
    if status: qs = qs.filter(status=status)
    allowed_sorts = {'student__name','-student__name','subject','-subject','status','score','-score','assign_id'}
    if sort not in allowed_sorts: sort = '-assign_id'
    qs = qs.order_by(sort)
    return render(request, 'students/assignments_list.html', {
        'assignments': qs, 'total_count': total_count,
        'shown_count': qs.count(), 'statuses': Assignment.STATUS_CHOICES,
    })


@login_required(login_url='/login/')
def add_assignment(request):
    students = Student.objects.all()
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        subject    = request.POST.get('subject',   '').strip()
        file_link  = request.POST.get('file_link', '').strip()
        status     = request.POST.get('status', 'PENDING')
        if student_id and subject:
            student    = get_object_or_404(Student, id=student_id)
            
            # Validate teacher subject
            if get_role(request) == ROLE_TEACHER:
                teacher = get_teacher_for_user(request.user)
                if teacher:
                    assignments = TeacherSectionAssignment.objects.filter(teacher=teacher, section=student.section)
                    allowed_subjects = [a.subject for a in assignments]
                    if subject not in allowed_subjects:
                        messages.error(request, f'You are not authorized to assign {subject} to this section.')
                        return redirect('add_assignment')
                        
            assignment = Assignment(student=student, subject=subject, file_link=file_link, status=status)
            if get_role(request) == ROLE_TEACHER:
                teacher = get_teacher_for_user(request.user)
                if teacher:
                    assignment.teacher = teacher
            assignment.save()
            try: add_to_sheet(assignment, 'Assignments')
            except Exception: traceback.print_exc()
            log = LogEntry(action='ADD_ASSIGNMENT',
                           description=f'Added {subject} for "{student.name}" (AssignID: {assignment.assign_id})',
                           user_id=request.user.username)
            log.save()
            try: add_to_sheet(log, 'Log/History')
            except Exception: traceback.print_exc()
            messages.success(request, f'Assignment added for {student.name}.')
            return redirect('assignments_list')
        else:
            messages.error(request, 'Student and subject are required.')
    return render(request, 'students/assignments_add.html', {
        'students': students, 
        'subject_options': SUBJECT_OPTIONS
    })


@login_required(login_url='/login/')
def submit_assignment(request, assign_id):
    assignment = get_object_or_404(Assignment, assign_id=assign_id)
    if get_role(request) == ROLE_STUDENT:
        if request.method == 'POST':
            file = request.FILES.get('submission_file')
            if file:
                assignment.submission_file = file
                assignment.status = 'SUBMITTED'
                assignment.save()
                messages.success(request, f'Assignment "{assignment.subject}" submitted successfully.')
            else:
                messages.error(request, 'No file was uploaded. Please select a PDF or image.')
    return redirect('dashboard')


@login_required(login_url='/login/')
def update_assignment_result(request, assign_id):
    assignment = get_object_or_404(Assignment, assign_id=assign_id)
    role = get_role(request)
    if role not in [ROLE_TEACHER, ROLE_PRINCIPAL] and not request.user.is_superuser:
        messages.error(request, 'Only teachers or principals can update assignments.')
        return redirect('dashboard')
        
    if role == ROLE_TEACHER:
        teacher = get_teacher_for_user(request.user)
        if teacher:
            assignments = TeacherSectionAssignment.objects.filter(teacher=teacher, section=assignment.student.section)
            allowed_subjects = [a.subject for a in assignments]
            if assignment.subject not in allowed_subjects:
                messages.error(request, f'You are not authorized to evaluate {assignment.subject} assignments for this section.')
                return redirect('assignments_list')

    if request.method == 'POST':
        assignment.status = request.POST.get('status', assignment.status)
        assignment.remark = request.POST.get('remark', '').strip() or None
        score_val = request.POST.get('score', '').strip()
        if score_val:
            try: assignment.score = float(score_val)
            except: pass
        assignment.save()
        try: update_in_sheet(assignment, 'Assignments')
        except Exception: traceback.print_exc()
        messages.success(request, f'Assignment for {assignment.student.name} updated.')
        return redirect('assignments_list')
    return render(request, 'students/assignments_update.html', {
        'assign': assignment,
        'statuses': Assignment.STATUS_CHOICES
    })


@login_required(login_url='/login/')
def student_assignments_view(request):
    role = get_role(request)
    if role != ROLE_STUDENT:
        return redirect('dashboard')
    user = request.user
    student = None
    try:
        student = user.student_profile
    except Exception:
        pass
    if not student and user.email:
        student = Student.objects.filter(email=user.email).first()
    if not student and user.username.startswith('student_'):
        try:
            sid = int(user.username.split('_')[1])
            student = Student.objects.filter(id=sid).first()
        except: pass
    if not student: student = Student.objects.first()
    assignments = Assignment.objects.filter(student=student).order_by('-assign_id') if student else []
    return render(request, 'students/student_assignments.html', {
        'student': student, 'assignments': assignments, 'user_role': role
    })


@login_required(login_url='/login/')
def student_documents_view(request):
    role = get_role(request)
    if role != ROLE_STUDENT:
        return redirect('dashboard')
    user = request.user
    student = None
    try:
        student = user.student_profile
    except Exception:
        pass
    if not student and user.email:
        student = Student.objects.filter(email=user.email).first()
    if not student and user.username.startswith('student_'):
        try:
            sid = int(user.username.split('_')[1])
            student = Student.objects.filter(id=sid).first()
        except: pass
    if not student: student = Student.objects.first()
    documents = Document.objects.filter(student=student).order_by('-upload_date') if student else []
    return render(request, 'students/student_documents.html', {
        'student': student, 'documents': documents, 'user_role': role
    })


@login_required(login_url='/login/')
def logs_list(request):
    qs = LogEntry.objects.all().order_by('-timestamp')
    q  = request.GET.get('q', '').strip()
    if q: qs = qs.filter(description__icontains=q)
    return render(request, 'students/logs.html', {'logs': qs, 'total_count': qs.count()})


# ─────────────────────────────────────────────────────────────────────────────
# Principal: Create User Accounts for students / teachers / staff
# ─────────────────────────────────────────────────────────────────────────────
@principal_required
def create_user_account(request):
    """Principal-only: create login accounts for any role."""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email    = request.POST.get('email',    '').strip()
        password = request.POST.get('password', '').strip()
        role     = request.POST.get('role', ROLE_STUDENT)
        if not username or not password:
            messages.error(request, 'Username and password are required.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already taken.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            UserProfile.objects.create(user=user, role=role)
            messages.success(request, f'Account created for {username} with role {role}.')
            return redirect('principal_dashboard')
    return render(request, 'students/create_user.html', {'roles': ROLE_CHOICES})
