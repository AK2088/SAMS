"""
Main URL configuration for SAMS
Defines all URL patterns for the application
"""
from django.contrib import admin
from django.urls import path, include
from . import views
from faculty_app import views as facultyViews
from student_app import views as studentViews

urlpatterns = [
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
]
