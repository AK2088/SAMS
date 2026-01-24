"""
Faculty app URL configuration
"""
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # Faculty registration endpoint
    path('faculty/', views.facultyRegister, name='facultyRegister'),
]