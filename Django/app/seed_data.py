import os
import random
import time
from django.core.files.base import ContentFile
from django.conf import settings
from students.models import Student, Document

first_names = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan", "Shaurya", "Atharva", "Ananya", "Aadhya", "Saanvi", "Kiara", "Diya", "Pihu", "Prisha", "Avni", "Kavya", "Fatima", "Zara", "Rahul", "Priya", "Amit", "Neha", "Rohan", "Sneha", "Karan", "Pooja", "Vikram", "Riya", "Varun", "Shruti"]
last_names = ["Sharma", "Patel", "Singh", "Kumar", "Das", "Bose", "Gupta", "Verma", "Jain", "Mehta", "Naidu", "Iyer", "Pillai", "Reddy", "Nair", "Rao", "Menon", "Kapoor", "Chopra", "Chawla", "Yadav", "Ahluwalia", "Agarwal", "Bansal"]

courses = ["B.Tech", "B.Sc", "B.Com", "B.A.", "M.Tech", "MBA"]
classes = ["UG-1", "UG-2", "UG-3", "UG-4", "PG-1", "PG-2"]
genders = ["M", "F", "O"]
doc_types = ["ID", "FORM", "MEDICAL", "OTHER"]

def create_fake_image():
    # Extremely minimal pure valid GIF 1x1 image byte string 
    fake_gif = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    return fake_gif

def create_fake_pdf():
    # Extremely minimal valid PDF
    pdf_content = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\ntrailer<</Root 1 0 R>>"
    return pdf_content

print("Creating 35 fake students...")
for i in range(35):
    fname = random.choice(first_names)
    lname = random.choice(last_names)
    name = f"{fname} {lname}"
    email = f"{fname.lower()}.{lname.lower()}{random.randint(1, 999)}@example.com"
    age = random.randint(18, 25)
    course = random.choice(courses)
    attendance = round(random.uniform(55.0, 99.0), 1)
    marks = round(random.uniform(250.0, 480.0), 1)
    
    phone = f"+91 {random.randint(6000000000, 9999999999)}"
    gender = random.choice(genders)
    class_name = random.choice(classes)
    fees_paid = random.choice([True, False])
    address = f"{random.randint(1, 100)}, {random.choice(['MG Road', 'Gandhi Marg', 'Main Street', 'Park Avenue', 'Station Road'])}, {random.choice(['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata'])}"
    
    student = Student(
        name=name, email=email, age=age, course=course,
        attendance=attendance, marks=marks,
        phone=phone, gender=gender, class_name=class_name,
        fees_paid=fees_paid, address=address
    )
    
    student.profile_picture.save(f"avatar_{i}_{int(time.time())}.gif", ContentFile(create_fake_image()), save=False)
    student.resume.save(f"resume_{i}_{int(time.time())}.pdf", ContentFile(create_fake_pdf()), save=False)
    
    print(f"[{i+1}/35] Saving {name} to db and Google Sheets...")
    # This triggers the API post_save sync to sheets
    try:
        student.save()
    except Exception as e:
        print(f"Error saving {name}: {e}")
        time.sleep(2) # Backoff if rate limited
        continue
    
    # Also create a Document
    doc = Document(
        student=student,
        doc_type=random.choice(doc_types)
    )
    doc.document_file.save(f"doc_{i}_{int(time.time())}.pdf", ContentFile(create_fake_pdf()), save=False)
    doc.save()
    
    time.sleep(1) # Sleep to avoid hitting Google API limits (60 per min per user)

print("Finished seeding student data!")
