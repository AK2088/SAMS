"""
Faculty app models
Defines Teacher and MasterFaculty models
"""
from django.db import models
from django.contrib.auth.models import User


class Teacher(models.Model):
    """
    Teacher model - extends Django User with faculty-specific information
    One-to-one relationship with Django's built-in User model
    Created after successful registration and OTP verification
    """
    # Link to Django User account (one teacher per user)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=150, blank=True)
    # Enrollment ID must be unique
    enrollment_id = models.CharField(max_length=10, unique=True)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    
    # Verification and registration flags
    mail_verified = models.BooleanField(default=False)  # Email OTP verified
    is_registered = models.BooleanField(default=False)   # Registration complete
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    upadated_at = models.DateTimeField(auto_now=True)  # Note: typo in field name (upadated)

    def __str__(self):
        """String representation for admin and debugging"""
        return f"{self.user.username} ({self.enrollment_id})"
    

class MasterFaculty(models.Model):
    """
    MasterFaculty model - master list of all faculty members
    Used to verify enrollment IDs during registration
    Faculty must exist here before they can register
    """
    class Meta:
        verbose_name = "Faculty"
        verbose_name_plural = "Faculty Master"
    
    # Enrollment ID must be unique
    enrollment_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    # Email must be unique
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """String representation for admin and debugging"""
        return f"{self.name} ({self.enrollment_id})"
