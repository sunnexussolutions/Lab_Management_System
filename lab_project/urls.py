from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from labapp import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home),   # homepage
    path('admin/', admin.site.urls),
    path("college/login/", views.college_auth, name="college_auth"),
    path('college/dashboard/', views.college_dashboard, name="college_dashboard"),
    path('college/logout/', views.college_logout, name="college_logout"),
    path(
"college/add-professor/",
views.add_professor,
name="add_professor"
),

path(
"college/professors/",
views.view_professors,
name="view_professors"
),
path(
"college/edit-profile/",
views.edit_profile,
name="edit_profile"
),
path(
"college/delete-professor/<int:professor_id>/",
views.delete_professor,
name="delete_professor"
),
path(
"college/edit-professor/",
views.edit_professor,
name="edit_professor"
),
    path("college/add-lab/", views.add_lab, name="add_lab"),
    
    # Student URLs
    path("student/login/", views.student_login, name="student_login"),
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("student/update-profile/", views.update_profile, name="update_profile"),
    path("student/logout/", views.student_logout, name="student_logout"),
    path("student/check-call/", views.check_call, name="check_call"),
    path("student/export-marks-excel/<int:lab_id>/", views.export_marks_excel, name="export_marks_excel"),
    path("student/delete-submission/<int:submission_id>/", views.delete_submission, name="delete_submission"),

    path("professor/login/", views.professor_auth, name="professor_auth"),
    path("professor/dashboard/", views.professor_dashboard, name="professor_dashboard"),
    path("professor/logout/", views.professor_logout, name="professor_logout"),
    path("professor/edit-profile/", views.professor_edit_profile, name="professor_edit_profile"),
    path("professor/upload-student-excel/", views.upload_student_excel, name="upload_student_excel"),
    path("professor/check-upload-status/", views.check_upload_status, name="check_upload_status"),
    path("professor/delete-upload/", views.delete_upload, name="delete_upload"),
    path("professor/get-students-for-division/", views.get_students_for_division, name="get_students_for_division"),
    path("professor/get-submissions-for-division/", views.get_submissions_for_division, name="get_submissions_for_division"),
    path("professor/save-marks/", views.save_marks, name="save_marks"),
    path("professor/download-marks-excel/", views.download_marks_excel, name="download_marks_excel"),
    path("professor/download-total-marks-excel/", views.download_total_marks_excel, name="download_total_marks_excel"),
    path("professor/send-marks-report/", views.send_marks_report, name="send_marks_report"),
    path("professor/evaluate-submission/<int:submission_id>/", views.evaluate_submission, name="evaluate_submission"),
    path("professor/save-attendance/", views.save_attendance, name="save_attendance"),
    path("professor/check-lab-resources-status/", views.check_lab_resources_status, name="check_lab_resources_status"),
    path("professor/toggle-viva-session/", views.toggle_viva_session, name="toggle_viva_session"),
    path("professor/upload-lab-resource/", views.upload_lab_resource, name="upload_lab_resource"),
    path("professor/delete-lab-resource/", views.delete_lab_resource, name="delete_lab_resource"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="professor/password_reset.html"
        ),
        name="password_reset"
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="professor/password_reset_done.html"
        ),
        name="password_reset_done"
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="professor/password_reset_confirm.html"
        ),
        name="password_reset_confirm"
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="professor/password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)