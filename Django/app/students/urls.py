from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # ── Public ──────────────────────────────────────────────────────────────
    path('',          views.landing,       name='landing'),
    path('login/',    views.login_view,    name='login'),
    path('register/', views.register_view, name='register'),   # redirects to login
    path('logout/',   views.logout_view,   name='logout'),

    # ── Student / Teacher / General Dashboard ───────────────────────────────
    path('dashboard/',   views.dashboard,    name='dashboard'),
    path('dashboard/assignments/', views.student_assignments_view, name='student_assignments_view'),
    path('dashboard/documents/',   views.student_documents_view,   name='student_documents_view'),

    # ── Student CRUD ─────────────────────────────────────────────────────────
    path('students/',                 views.student_list,   name='students_list'),
    path('students/add/',             views.add_student,    name='add_student'),
    path('students/edit/<int:student_id>/',    views.edit_student,   name='edit_student'),
    path('students/partial/<int:student_id>/', views.partial_update, name='partial_update'),
    path('students/delete/<int:student_id>/',  views.delete_student, name='delete_student'),
    path('students/<int:student_id>/marks/',   views.enter_marks,    name='enter_marks'),

    # ── Admission Workflow ───────────────────────────────────────────────────
    path('admission/',                         views.admission_list,       name='admission_list'),
    path('admission/<int:student_id>/complete/',views.complete_admission,  name='complete_admission'),

    # ── Section Management ────────────────────────────────────────────────────
    path('sections/',                             views.section_list,   name='section_list'),
    path('sections/add/',                         views.add_section,    name='add_section'),
    path('sections/<int:pk>/',                    views.section_detail, name='section_detail'),
    path('sections/<int:section_pk>/assign-teacher/', views.assign_teacher_to_section, name='assign_teacher_to_section'),

    # ── Section Performance ───────────────────────────────────────────────────
    path('performance/',  views.section_performance, name='section_performance'),

    # ── Fee Management ────────────────────────────────────────────────────────
    path('fees/',  views.fee_management, name='fee_management'),

    # ── Announcements ─────────────────────────────────────────────────────────
    path('announcements/',        views.announcement_list,    name='announcement_list'),
    path('announcements/add/',    views.add_announcement,     name='add_announcement'),
    path('announcements/<int:pk>/delete/', views.delete_announcement, name='delete_announcement'),

    # ── Documents ─────────────────────────────────────────────────────────────
    path('documents/',     views.documents_list, name='documents_list'),
    path('documents/add/', views.add_document,   name='add_document'),

    # ── Assignments ───────────────────────────────────────────────────────────
    path('assignments/',     views.assignments_list, name='assignments_list'),
    path('assignments/add/', views.add_assignment,   name='add_assignment'),
    path('assignments/submit/<int:assign_id>/', views.submit_assignment, name='submit_assignment'),
    path('assignments/update/<int:assign_id>/', views.update_assignment_result, name='update_assignment'),

    # ── Logs ──────────────────────────────────────────────────────────────────
    path('logs/', views.logs_list, name='logs_list'),

    # ── Principal Dashboard ───────────────────────────────────────────────────
    path('principal/',   views.principal_dashboard, name='principal_dashboard'),
    path('principal/create-user/', views.create_user_account, name='create_user_account'),

    # ── Teacher CRUD (Principal only) ─────────────────────────────────────────
    path('teachers/',                  views.teacher_list,   name='teacher_list'),
    path('teachers/add/',              views.add_teacher,    name='add_teacher'),
    path('teachers/<int:pk>/',         views.teacher_detail, name='teacher_detail'),
    path('teachers/<int:pk>/edit/',    views.edit_teacher,   name='edit_teacher'),
    path('teachers/<int:pk>/delete/',  views.delete_teacher, name='delete_teacher'),

    # ── Staff CRUD (Principal only) ───────────────────────────────────────────
    path('staff/',                  views.staff_list,   name='staff_list'),
    path('staff/add/',              views.add_staff,    name='add_staff'),
    path('staff/<int:pk>/',         views.staff_detail, name='staff_detail'),
    path('staff/<int:pk>/edit/',    views.edit_staff,   name='edit_staff'),
    path('staff/<int:pk>/delete/',  views.delete_staff, name='delete_staff'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
