"""
Main URL configuration for SAMS
Defines all URL patterns for the application
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.templatetags.static import static
from . import views
from faculty_app import views as facultyViews
from student_app import views as studentViews

urlpatterns = [
    # Browser favicon fallback endpoint
    path(
        "favicon.ico",
        RedirectView.as_view(url=static("icons/favicon.png"), permanent=True),
    ),
    # Admin panel
    path('admin/', admin.site.urls),
    
    # Home and role selection
    path('', views.home, name='home'),
    path('roleselection/', views.role, name='role'),
    
    # Authentication
    path('login/', views.loginView, name='login'),
    path('logout/', views.logoutView, name='logout'),
    
    # Registration (includes both student and faculty registration)
    path('registration/', include('faculty_app.urls')),
    path('registration/', include('student_app.urls')),
    
    # OTP verification
    path('optverify/', views.otpVerification, name='otp'),
    
    # Password reset
    path('passwordreset/', views.passwordReset, name='passRst'),
    
    # Dashboards
    path('fdashboard/', facultyViews.renderDashboard, name='fdashboard'),
    path('sdashboard/', studentViews.renderDashboard, name='sdashboard'),

    # Teacher attendance APIs
    path('attendance/teacher/start/<int:classroom_id>/', facultyViews.start_attendance_session, name='startAttendanceSession'),
    path('attendance/teacher/qr/<int:session_id>/', facultyViews.current_qr_token, name='currentQrToken'),
    path('attendance/teacher/stop/<int:session_id>/', facultyViews.stop_attendance_session, name='stopAttendanceSession'),
    path('attendance/teacher/download/<int:classroom_id>/', facultyViews.download_attendance_csv, name='downloadAttendanceCsv'),

    # Student attendance APIs
    path('attendance/student/scan/', studentViews.scan_attendance_qr, name='scanAttendanceQr'),
    path('attendance/student/verify-face/', studentViews.verify_attendance_face, name='verifyAttendanceFace'),
]

# Global HTML error handlers (API endpoints still return JSON in app views).
handler400 = "sams_main.views.error_400"
handler403 = "sams_main.views.error_403"
handler404 = "sams_main.views.error_404"
handler500 = "sams_main.views.error_500"
