"""
Student app URL configuration
"""
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # Student registration endpoint
    path('student/', views.studentRegister, name='studentRegister'),
]