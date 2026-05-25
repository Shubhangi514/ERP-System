import os
import django
import random
import time
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from students.models import (
    Student, Teacher, Staff, Document, UserProfile, 
    ROLE_PRINCIPAL, ROLE_TEACHER, ROLE_STAFF, ROLE_STUDENT
)
from django.contrib.auth.models import User

# Note: We disable signal Google Sheets API syncing if preferred to speed up, 
# but if you want it to sync, we will leave it as is.

first_names = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan", "Priya", "Neha", "Sneha", "Pooja", "Riya", "Shruti"]
last_names = ["Sharma", "Patel", "Singh", "Kumar", "Das", "Bose", "Gupta", "Verma", "Jain", "Mehta"]
courses = ["B.Tech", "B.Sc", "B.Com", "B.A.", "M.Tech", "MBA"]
classes = ["UG-1", "UG-2", "UG-3", "UG-4", "PG-1", "PG-2"]
genders = ["M", "F", "O"]

def create_fake_image():
    return b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'

def seed():
    # Helper to create auth user
    def create_user(username, email, role):
        if not User.objects.filter(username=username).exists():
            u = User.objects.create_user(username=username, email=email, password='password123')
            UserProfile.objects.create(user=u, role=role)
            return u
        return User.objects.get(username=username)

    print("CREATING 2 PRINCIPALS...")
    for i in range(2):
        create_user(f"principal{i+1}", f"principal{i+1}@school.com", ROLE_PRINCIPAL)

    print("CREATING 4 TEACHERS...")
    for i in range(4):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        name = f"{fname} {lname}"
        email = f"teacher{i+1}@school.com"
        create_user(f"teacher{i+1}", email, ROLE_TEACHER)
        
        t = Teacher(
            employee_id=f"TCH-100{i}", name=name, email=email,
            subject=random.choice(["Math", "Science", "History", "English"]),
            employment_type="permanent", gender=random.choice(genders),
            experience_yrs=random.randint(2, 15)
        )
        t.profile_picture.save(f"t_avatar_{i}.gif", ContentFile(create_fake_image()), save=False)
        try:
            t.save()
        except: pass

    print("CREATING 5 STAFF...")
    for i in range(5):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        name = f"{fname} {lname}"
        email = f"staff{i+1}@school.com"
        create_user(f"staff{i+1}", email, ROLE_STAFF)
        
        s = Staff(
            employee_id=f"STF-200{i}", name=name, email=email,
            department=random.choice(["Administration", "IT Support", "Maintenance", "Library"]),
            designation="Assistant", employment_type="permanent"
        )
        s.profile_picture.save(f"s_avatar_{i}.gif", ContentFile(create_fake_image()), save=False)
        try:
            s.save()
        except: pass

    print("CREATING 50 STUDENTS...")
    for i in range(50):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        name = f"{fname} {lname}"
        email = f"student{i+1}@school.com"
        create_user(f"student{i+1}", email, ROLE_STUDENT)
        
        student = Student(
            name=name, email=email, age=random.randint(18, 25),
            course=random.choice(courses), class_name=random.choice(classes),
            gender=random.choice(genders), fees_paid=random.choice([True, False]),
            attendance=round(random.uniform(55.0, 99.0), 1),
            marks=round(random.uniform(250.0, 480.0), 1)
        )
        student.profile_picture.save(f"avatar_{i}.gif", ContentFile(create_fake_image()), save=False)
        
        try:
            student.save()
        except Exception as e:
            print(f"Error saving student: {e}")
            
    print("Database seeding entirely finished! Logins are simple (e.g. username 'teacher1', password 'password123')")

if __name__ == '__main__':
    seed()
