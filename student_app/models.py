"""
Student app models
Defines the Student model which extends Django's User model
"""
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone
from django.db import models


class Student(models.Model):
    """
    Student model - extends Django User with student-specific information
    One-to-one relationship with Django's built-in User model
    """
    name = models.CharField(max_length=50, null=True)
    # Link to Django User account (one student per user)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Roll number must be unique
    roll = models.IntegerField(unique=True)
    # Face embedding data for face recognition (stored as JSON)
    face_embedding = models.JSONField(null=True, blank=True)

    # Verification flags
    mail_verified = models.BooleanField(default=False)  # Email OTP verified
    face_verified = models.BooleanField(default=False)   # Face recognition verified

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_verified(self):
        """
        Check if student is fully verified (both email and face)
        """
        return self.mail_verified and self.face_verified

    def __str__(self):
        """String representation for admin and debugging"""
        return f"{self.user.username} ({self.roll})"



