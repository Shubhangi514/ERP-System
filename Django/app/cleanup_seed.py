import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from students.models import Student
latest_students = list(Student.objects.order_by('-id')[:35])
for s in latest_students:
    print(f"Deleting {s.name}...")
    try:
        s.delete()
    except Exception as e:
        print(f"Error {e}")
print("Cleanup done.")
