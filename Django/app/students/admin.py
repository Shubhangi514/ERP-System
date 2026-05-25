from django.contrib import admin
from .models import Student, Document, Assignment, LogEntry, Teacher, Staff, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role')
    list_filter   = ('role',)
    search_fields = ('user__username',)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display  = ('employee_id', 'name', 'subject', 'qualification', 'experience_yrs', 'employment_type', 'date_joined')
    list_filter   = ('employment_type', 'qualification', 'gender')
    search_fields = ('name', 'email', 'employee_id', 'subject')
    ordering      = ('name',)
    fieldsets = (
        ('Personal', {'fields': ('employee_id','name','email','phone','gender','date_of_birth','address','profile_picture')}),
        ('Academic', {'fields': ('subject','classes_taught','qualification','experience_yrs','specialization')}),
        ('Employment', {'fields': ('employment_type','date_joined','salary')}),
        ('Bio', {'fields': ('bio','achievements')}),
    )


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display  = ('employee_id', 'name', 'designation', 'department', 'employment_type', 'date_joined')
    list_filter   = ('department', 'employment_type', 'gender')
    search_fields = ('name', 'email', 'employee_id', 'designation')
    ordering      = ('department', 'name')
    fieldsets = (
        ('Personal',    {'fields': ('employee_id','name','email','phone','gender','date_of_birth','address','profile_picture')}),
        ('Work',        {'fields': ('designation','department','work_description')}),
        ('Employment',  {'fields': ('employment_type','date_joined','salary')}),
        ('Qualifications & Bio', {'fields': ('qualification','bio')}),
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name', 'email', 'class_name', 'course', 'gender', 'fees_paid', 'marks', 'attendance')
    list_filter   = ('gender', 'fees_paid', 'class_name', 'course')
    search_fields = ('name', 'email')
    ordering      = ('name',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display  = ('doc_id', 'student', 'doc_type', 'upload_date')
    list_filter   = ('doc_type',)
    search_fields = ('student__name',)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display  = ('assign_id', 'student', 'subject', 'status', 'score')
    list_filter   = ('status',)
    search_fields = ('student__name', 'subject')


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display  = ('action', 'user_id', 'timestamp', 'description')
    list_filter   = ('action',)
    search_fields = ('description',)
    ordering      = ('-timestamp',)
