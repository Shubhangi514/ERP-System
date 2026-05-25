import os
import django
import random
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from students.models import Student, Teacher, Staff, Assignment, ROLE_TEACHER
from django.contrib.auth.models import User

# List of some fake subjects, courses
SUBJECTS = ['Mathematics', 'Physics', 'Computer Science', 'Chemistry', 'English', 'History', 'Biology']
STAFF_DEPT = ['Administration', 'Security', 'Library', 'IT Support', 'Housekeeping']
STAFF_ROLES = ['Clerk', 'Security Guard', 'Librarian', 'Network Admin', 'Janitor']

print("Seeding random assignments, teachers, and staff...")

# 1. Add assignments for students
students = list(Student.objects.all())
statuses = ['Pending', 'Submitted', 'Graded']

for student in students:
    # ensure they have some random assignments
    if student.assignments.count() < 3:
        for _ in range(random.randint(2, 5)):
            subject = random.choice(SUBJECTS)
            status = random.choice(statuses)
            score = random.randint(40, 100) if status == 'Graded' else None
            Assignment.objects.create(
                student=student,
                subject=subject,
                status=status,
                score=score
            )
print("Finished adding random assignments to students.")

# 2. Add couple of Teachers
for i in range(3):
    t_id = f"TCH-90{i}"
    if not Teacher.objects.filter(employee_id=t_id).exists():
        sub = random.choice(SUBJECTS)
        name = f"Demo Teacher {sub}"
        email = f"teacher{i}@school.com"
        
        t = Teacher.objects.create(
            employee_id=t_id,
            name=name,
            email=email,
            subject=sub,
            experience_yrs=random.randint(1, 15),
            salary=50000 + random.randint(1000, 20000)
        )
        # Create user account for them
        u, _ = User.objects.get_or_create(username=email)
        u.set_password('password123')
        u.save()
        from students.models import UserProfile
        prof, _ = UserProfile.objects.get_or_create(user=u)
        prof.role = 'teacher'
        prof.save()

# 3. Add couple of Staff
for i in range(3):
    s_id = f"STF-90{i}"
    if not Staff.objects.filter(employee_id=s_id).exists():
        dept = random.choice(STAFF_DEPT)
        role = random.choice(STAFF_ROLES)
        name = f"Demo Staff {i}"
        email = f"staff{i}@school.com"
        
        s = Staff.objects.create(
            employee_id=s_id,
            name=name,
            email=email,
            designation=role,
            department=dept,
            salary=20000 + random.randint(1000, 10000)
        )
        
print("Successfully generated Teachers and Staff. You can log into teachers using teacher0@school.com and password password123")
