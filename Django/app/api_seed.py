import random
import time
import requests
import io
import re

first_names = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan", "Shaurya", "Atharva", "Ananya", "Aadhya", "Saanvi", "Kiara", "Diya", "Pihu", "Prisha", "Avni", "Kavya", "Fatima", "Zara", "Rahul", "Priya", "Amit", "Neha", "Rohan", "Sneha", "Karan", "Pooja", "Vikram", "Riya", "Varun", "Shruti"]
last_names = ["Sharma", "Patel", "Singh", "Kumar", "Das", "Bose", "Gupta", "Verma", "Jain", "Mehta", "Naidu", "Iyer", "Pillai", "Reddy", "Nair", "Rao", "Menon", "Kapoor", "Chopra", "Chawla", "Yadav", "Ahluwalia", "Agarwal", "Bansal"]

courses = ["B.Tech", "B.Sc", "B.Com", "B.A.", "M.Tech", "MBA"]
classes = ["UG-1", "UG-2", "UG-3", "UG-4", "PG-1", "PG-2"]
genders = ["M", "F", "O"]

def create_fake_image():
    return b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'

def create_fake_pdf():
    return b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\ntrailer<</Root 1 0 R>>"

BASE_URL = "http://127.0.0.1:8000"
session = requests.Session()

def get_csrf_token(url):
    response = session.get(url)
    match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
    if match:
        return match.group(1)
    return None

print("Simulating 35 API POST requests to /add/...")

new_student_ids = []

for i in range(35):
    csrf = get_csrf_token(f"{BASE_URL}/add/")
    if not csrf:
        print("Failed to get CSRF token.")
        break
        
    fname = random.choice(first_names)
    lname = random.choice(last_names)
    name = f"{fname} {lname}"
    email = f"{fname.lower()}.{lname.lower()}{random.randint(1, 999)}@example.com"
    
    data = {
        'csrfmiddlewaretoken': csrf,
        'name': name,
        'age': str(random.randint(18, 25)),
        'email': email,
        'phone': f"+91 {random.randint(6000000000, 9999999999)}",
        'gender': random.choice(genders),
        'class_name': random.choice(classes),
        'course': random.choice(courses),
        'attendance': f"{round(random.uniform(55.0, 99.0), 1)}",
        'marks': f"{round(random.uniform(250.0, 480.0), 1)}",
        'address': f"{random.randint(1, 100)}, {random.choice(['MG Road', 'Gandhi Marg', 'Main Street'])}, {random.choice(['City A', 'City B'])}"
    }
    
    if random.choice([True, False]):
        data['fees_paid'] = 'on'
        
    files = {
        'profile_picture': (f'avatar_{i}.gif', create_fake_image(), 'image/gif'),
        'resume': (f'resume_{i}.pdf', create_fake_pdf(), 'application/pdf')
    }
    
    print(f"[{i+1}/35] Sending POST request for {name}...")
    r_post = session.post(f"{BASE_URL}/add/", data=data, files=files)
    
    if r_post.status_code in [200, 302, 301]:
        print(f"Success for {name} (Status code: {r_post.status_code})")
        # Find if it redirected us, which means successful save.
        # But we won't get the ID cleanly without parsing the DB, which is fine.
    else:
        print(f"Failed for {name}: {r_post.status_code}")
        print(r_post.text[:200]) # Print snippet of error
        
    # We must delay a bit since the backend view blocks to update Google Sheets. 
    # The response won't return until the sheet is updated!
    time.sleep(0.5)

print("\n--- Done seeding students via API POST ---")

print("Seeding some random documents via API POST...")
# Scrape the students list to find IDs to attach documents to
r_list = session.get(f"{BASE_URL}/students/")
if r_list.status_code == 200:
    id_matches = re.findall(r'href="/edit/(\d+)/"', r_list.text)
    unique_ids = list(set(id_matches))
    unique_ids = random.sample(unique_ids, min(len(unique_ids), 35))
    
    for i, sid in enumerate(unique_ids):
        csrf = get_csrf_token(f"{BASE_URL}/documents/add/")
        if not csrf:
            break
            
        data = {
            'csrfmiddlewaretoken': csrf,
            'student_id': sid,
            'doc_type': random.choice(["ID", "FORM", "MEDICAL", "OTHER"])
        }
        files = {
            'document_file': (f'doc_{i}.pdf', create_fake_pdf(), 'application/pdf')
        }
        
        print(f"Uploading generic document for student ID #{sid}...")
        r_doc = session.post(f"{BASE_URL}/documents/add/", data=data, files=files)
        time.sleep(0.5)
        
print("Fully Finished!")
