import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from students.models import Student, Teacher, Staff, UserProfile

def process_users(model_class, role_name, password):
    print(f"Setting common password '{password}' for all {role_name}s...")
    count = 0
    for obj in model_class.objects.all():
        # Use email as username for teacher/staff, or email/fallback for students
        if role_name == 'student':
            username = obj.email if obj.email else f"student_{obj.id}"
        else:
            username = obj.email if obj.email else f"{role_name}_{obj.id}"
        
        if not username:
            continue

        user, created = User.objects.get_or_create(username=username)
        if created:
            user.email = obj.email or ""
            parts = obj.name.split() if obj.name else [role_name.capitalize()]
            user.first_name = parts[0]
            user.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            
        user.set_password(password)
        user.save()
        
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role_name
        profile.save()
        count += 1
    print(f"Successfully processed {count} {role_name}s.")
    return count

common_password = 'password123'
total = 0
total += process_users(Student, 'student', common_password)
total += process_users(Teacher, 'teacher', common_password)
total += process_users(Staff, 'staff', common_password)

print(f"\nFinished! Processed {total} users in total. They can now login with their respective usernames and '{common_password}' as the password.")
