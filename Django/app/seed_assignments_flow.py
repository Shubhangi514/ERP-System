import os
import django
import random
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from students.models import Student, Teacher, Assignment

SUBJECTS = ['Mathematics', 'Physics', 'Computer Science', 'Chemistry', 'English', 'History', 'Biology']
REMARKS = ['Excellent effort!', 'Good work, but check question 3.', 'Keep it up!', 'Wrong approach in section B.', 'Partially correct.', 'Outstanding!', 'Need more detail in the conclusion.']
STATUSES = ['PENDING', 'SUBMITTED', 'WRONG', 'COMPLETE']

def seed_flow():
    students = list(Student.objects.all())
    teachers = list(Teacher.objects.all())
    
    if not students or not teachers:
        print("Need students and teachers to seed assignments. Please run seed_data.py and seed_fake_data.py first.")
        return

    print(f"Seeding assignment flow for {len(students)} students using {len(teachers)} teachers...")

    for student in students:
        # Create 2-3 assignments for each student
        for _ in range(random.randint(2, 3)):
            teacher = random.choice(teachers)
            subject = random.choice(SUBJECTS)
            
            # 1. Teacher assigns (PENDING)
            assignment = Assignment.objects.create(
                student=student,
                teacher=teacher,
                subject=subject,
                status='PENDING'
            )
            
            # Randomly decide the flow
            flow_type = random.random()
            
            if flow_type > 0.2:
                # 2. Student submits (SUBMITTED)
                assignment.status = 'SUBMITTED'
                assignment.save()
                
                if flow_type > 0.5:
                    # 3. Teacher checks (COMPLETE or WRONG)
                    assignment.status = random.choice(['COMPLETE', 'WRONG'])
                    assignment.remark = random.choice(REMARKS)
                    if assignment.status == 'COMPLETE':
                        assignment.score = random.randint(80, 100)
                    else:
                        assignment.score = random.randint(40, 75)
                    assignment.save()
            
    print("Assignment flow seeded successfully!")

if __name__ == '__main__':
    seed_flow()
