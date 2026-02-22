"""
Student app URL configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    # Student registration endpoint
    path('student/', views.studentRegister, name='studentRegister'),
    # Face registration endpoint
    path('register-face/', views.register_face, name='registerFace'),
]
