"""
Faculty app URL configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    # Faculty registration endpoint
    path('faculty/', views.facultyRegister, name='facultyRegister'),
]
