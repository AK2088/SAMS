
from django.contrib import admin
from django.urls import path,include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('roleselection/',views.role , name='role'),
    path('login/', views.login, name='login'),
    path('registration/',include('faculty_app.urls')),
    path('registration/',include('student_app.urls')),
    path('optverify/',views.otpVerification,name='otp'),
    path('passwordreset/',views.passwordReset,name='passRst'),
   

]
