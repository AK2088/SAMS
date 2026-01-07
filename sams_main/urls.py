
from django.contrib import admin
from django.urls import path,include
from . import views
from faculty_app import views as facultyViews
from student_app import views as studentViews

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('roleselection/',views.role , name='role'),
    path('login/', views.loginView, name='login'),
    path('registration/',include('faculty_app.urls')),
    path('registration/',include('student_app.urls')),
    path('optverify/',views.otpVerification,name='otp'),
    path('fdashboard/',facultyViews.renderDashboard, name='fdashboard'),
    path('sdashboard/',studentViews.renderDashboard, name='sdashboard'),
    path('passwordreset/',views.passwordReset,name='passRst'),
    path('logout/',views.logoutView,name='logout'),

]
