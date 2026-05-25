from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ── Role Choices ───────────────────────────────────────────────────────────────
ROLE_STUDENT   = 'student'
ROLE_TEACHER   = 'teacher'
ROLE_PRINCIPAL = 'principal'
ROLE_STAFF     = 'staff'

ROLE_CHOICES = [
    (ROLE_STUDENT,   'Student'),
    (ROLE_TEACHER,   'Teacher'),
    (ROLE_STAFF,     'Staff'),
    (ROLE_PRINCIPAL, 'Principal'),
]

CLASS_CHOICES = [
    ('Class 1', 'Class 1'),   ('Class 2', 'Class 2'),   ('Class 3', 'Class 3'),
    ('Class 4', 'Class 4'),   ('Class 5', 'Class 5'),   ('Class 6', 'Class 6'),
    ('Class 7', 'Class 7'),   ('Class 8', 'Class 8'),   ('Class 9', 'Class 9'),
    ('Class 10', 'Class 10'), ('Class 11', 'Class 11'), ('Class 12', 'Class 12'),
    ('UG-1', 'UG Year 1'),    ('UG-2', 'UG Year 2'),    ('UG-3', 'UG Year 3'),
    ('PG-1', 'PG Year 1'),    ('PG-2', 'PG Year 2'),
]

SECTION_CHOICES = [
    ('A', 'Section A'),
    ('B', 'Section B'),
    ('C', 'Section C'),
    ('D', 'Section D'),
    ('E', 'Section E'),
]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


# ── Section ─────────────────────────────────────────────────────────────────────
class Section(models.Model):
    """A named section within a class, e.g. Class 9 – Section A"""
    class_name = models.CharField(max_length=50, choices=CLASS_CHOICES)
    section    = models.CharField(max_length=1, choices=SECTION_CHOICES)
    capacity   = models.IntegerField(default=40)
    class_teacher = models.ForeignKey('Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='class_teacher_sections')
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        unique_together = ('class_name', 'section')
        ordering = ['class_name', 'section']

    def __str__(self):
        return f"{self.class_name} – Section {self.section}"

    @property
    def student_count(self):
        return self.students.count()

    @property
    def avg_marks(self):
        from django.db.models import Avg
        result = self.students.aggregate(avg=Avg('marks'))
        return round(result['avg'] or 0, 1)

    @property
    def avg_attendance(self):
        from django.db.models import Avg
        result = self.students.aggregate(avg=Avg('attendance'))
        return round(result['avg'] or 0, 1)


# ── Teacher ────────────────────────────────────────────────────────────────────
class Teacher(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    QUALIFICATION_CHOICES = [
        ('B.Ed',  'B.Ed'),
        ('M.Ed',  'M.Ed'),
        ('PhD',   'PhD'),
        ('B.Sc',  'B.Sc'),
        ('M.Sc',  'M.Sc'),
        ('B.A',   'B.A'),
        ('M.A',   'M.A'),
        ('Other', 'Other'),
    ]
    EMPLOYMENT_CHOICES = [
        ('permanent',  'Permanent'),
        ('contract',   'Contract'),
        ('visiting',   'Visiting'),
        ('probation',  'Probation'),
    ]

    employee_id   = models.CharField(max_length=20, unique=True)
    name          = models.CharField(max_length=200)
    email         = models.EmailField(unique=True)
    phone         = models.CharField(max_length=15, blank=True, null=True)
    gender        = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    date_of_birth = models.DateField(null=True, blank=True)
    address       = models.TextField(blank=True, null=True)

    # Academic
    subject       = models.CharField(max_length=200)
    classes_taught= models.CharField(max_length=500, blank=True, null=True,
                                     help_text='Comma-separated class names')
    qualification = models.CharField(max_length=20, choices=QUALIFICATION_CHOICES, default='B.Ed')
    experience_yrs= models.IntegerField(default=0, help_text='Years of experience')
    specialization= models.CharField(max_length=300, blank=True, null=True)

    # Employment
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES, default='permanent')
    date_joined     = models.DateField(null=True, blank=True)
    salary          = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Bio / extra
    bio             = models.TextField(blank=True, null=True)
    achievements    = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='teacher_profiles/', null=True, blank=True)

    # Django User link (for login)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='teacher_profile')

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.subject})"

    @property
    def gender_label(self):
        return dict(self.GENDER_CHOICES).get(self.gender, self.gender)


# ── Teacher-Section Assignment ──────────────────────────────────────────────────
class TeacherSectionAssignment(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='section_assignments')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='teacher_assignments')
    subject = models.CharField(max_length=200)
    assigned_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        unique_together = ('teacher', 'section', 'subject')

    def __str__(self):
        return f"{self.teacher.name} → {self.section} ({self.subject})"


# ── Student ────────────────────────────────────────────────────────────────────
class Student(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash',   'Cash'),
        ('check',  'Check'),
        ('online', 'Online'),
        ('',       'Pending'),
    ]

    # Admission info
    admission_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    admission_date   = models.DateField(null=True, blank=True)

    name       = models.CharField(max_length=200)
    age        = models.IntegerField()
    email      = models.EmailField()
    phone      = models.CharField(max_length=15, blank=True, null=True)
    gender     = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    address    = models.TextField(blank=True, null=True)
    class_name = models.CharField(max_length=50, choices=CLASS_CHOICES, blank=True, null=True)
    section    = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')

    fees_paid  = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, blank=True, default='')

    course     = models.CharField(max_length=200)
    attendance = models.FloatField()
    marks      = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    profile_picture = models.ImageField(upload_to='student_profiles/', null=True, blank=True)
    resume          = models.FileField(upload_to='student_resumes/', null=True, blank=True)

    # Django User link
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_profile')

    def __str__(self):
        return self.name

    @property
    def gender_label(self):
        return dict(self.GENDER_CHOICES).get(self.gender, self.gender)

    @property
    def section_label(self):
        if self.section:
            return str(self.section)
        return '—'


# ── Staff ──────────────────────────────────────────────────────────────────────
class Staff(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    DEPARTMENT_CHOICES = [
        ('Administration', 'Administration'),
        ('Accounts',       'Accounts'),
        ('Library',        'Library'),
        ('Security',       'Security'),
        ('Housekeeping',   'Housekeeping'),
        ('IT Support',     'IT Support'),
        ('Transport',      'Transport'),
        ('Medical',        'Medical'),
        ('Sports',         'Sports'),
        ('Canteen',        'Canteen'),
        ('Other',          'Other'),
    ]
    EMPLOYMENT_CHOICES = [
        ('permanent', 'Permanent'),
        ('contract',  'Contract'),
        ('part-time', 'Part-Time'),
        ('temporary', 'Temporary'),
    ]

    employee_id     = models.CharField(max_length=20, unique=True)
    name            = models.CharField(max_length=200)
    email           = models.EmailField(unique=True)
    phone           = models.CharField(max_length=15, blank=True, null=True)
    gender          = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    date_of_birth   = models.DateField(null=True, blank=True)
    address         = models.TextField(blank=True, null=True)

    # Work info
    designation     = models.CharField(max_length=200)
    department      = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, default='Administration')
    work_description= models.TextField(blank=True, null=True)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES, default='permanent')
    date_joined     = models.DateField(null=True, blank=True)
    salary          = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Only Administration staff can see fee details
    is_admin_staff  = models.BooleanField(default=False, help_text='Administrative staff with access to fee records')

    # Bio / Qualifications
    qualification   = models.CharField(max_length=300, blank=True, null=True)
    bio             = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='staff_profiles/', null=True, blank=True)

    # Django User link
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profile')

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.name} – {self.designation}"

    @property
    def gender_label(self):
        return dict(self.GENDER_CHOICES).get(self.gender, self.gender)

    class Meta:
        verbose_name_plural = "Staff"


# ── Announcement ───────────────────────────────────────────────────────────────
class Announcement(models.Model):
    AUDIENCE_CHOICES = [
        ('all',       'Everyone'),
        ('teachers',  'Teachers Only'),
        ('students',  'Students Only'),
        ('staff',     'Staff Only'),
        ('principal', 'Principal Only'),
    ]

    title      = models.CharField(max_length=300)
    body       = models.TextField()
    audience   = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active  = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.audience})"


# ── Student Marks (Quarterly / Half-Yearly / Annual) ──────────────────────────
class StudentMarks(models.Model):
    TERM_CHOICES = [
        ('Q1',  'First Quarter'),
        ('Q2',  'Second Quarter'),
        ('Q3',  'Third Quarter'),
        ('Q4',  'Fourth Quarter'),
        ('HY1', 'First Half-Yearly'),
        ('HY2', 'Second Half-Yearly'),
        ('ANN', 'Annual'),
    ]

    student    = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='term_marks')
    subject    = models.CharField(max_length=200)
    term       = models.CharField(max_length=5, choices=TERM_CHOICES)
    max_marks  = models.FloatField(default=100)
    marks_obtained = models.FloatField()
    recorded_by= models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_at= models.DateTimeField(auto_now_add=True)
    remarks    = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'subject', 'term')
        ordering = ['student', 'term', 'subject']

    def __str__(self):
        return f"{self.student.name} – {self.subject} – {self.term}: {self.marks_obtained}/{self.max_marks}"

    @property
    def percentage(self):
        if self.max_marks:
            return round((self.marks_obtained / self.max_marks) * 100, 1)
        return 0

    @property
    def grade(self):
        p = self.percentage
        if p >= 90: return 'A+'
        if p >= 80: return 'A'
        if p >= 70: return 'B+'
        if p >= 60: return 'B'
        if p >= 50: return 'C'
        if p >= 40: return 'D'
        return 'F'


# ── Document ───────────────────────────────────────────────────────────────────
class Document(models.Model):
    DOC_TYPES = [
        ('ID',          'ID Proof'),
        ('FORM',        'Admission Form'),
        ('MEDICAL',     'Medical Record'),
        ('CERTIFICATE', 'Certificate'),
        ('FEE',         'Fee Receipt'),
        ('ASSIGNMENT',  'Assignment'),
        ('OTHER',       'Other'),
    ]
    doc_id        = models.AutoField(primary_key=True)
    student       = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    doc_type      = models.CharField(max_length=20, choices=DOC_TYPES)
    document_file = models.FileField(upload_to='student_documents/', null=True, blank=True)
    drive_link    = models.URLField(max_length=500, blank=True, null=True)
    upload_date   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.doc_type} - {self.student.name}"

    @property
    def file_url(self):
        if self.document_file:
            try:
                return self.document_file.url
            except Exception:
                pass
        return self.drive_link or ''


# ── Assignment ─────────────────────────────────────────────────────────────────
class Assignment(models.Model):
    STATUS_CHOICES = [
        ('PENDING',   'Pending'),
        ('SUBMITTED', 'Submitted'),
        ('WRONG',     'Wrong'),
        ('COMPLETE',  'Complete'),
    ]
    assign_id = models.AutoField(primary_key=True)
    student   = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assignments')
    teacher   = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    subject   = models.CharField(max_length=100)
    file_link = models.URLField(max_length=500, blank=True, null=True)
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    score     = models.FloatField(null=True, blank=True)
    remark    = models.TextField(blank=True, null=True)
    submission_file = models.FileField(upload_to='assignment_submissions/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.subject} - {self.student.name}"


# ── LogEntry ───────────────────────────────────────────────────────────────────
class LogEntry(models.Model):
    action      = models.CharField(max_length=50)
    user_id     = models.CharField(max_length=50, default='system')
    timestamp   = models.DateTimeField(auto_now_add=True)
    description = models.TextField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} - {self.description[:50]}"
