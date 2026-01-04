from django.db import models

from datetime import timedelta
from django.utils import timezone
from django.db import models


class EmailOTP(models.Model):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    )

    identifier = models.CharField(max_length=50, unique=True)
    email = models.EmailField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)

    def __str__(self):
        return f"{self.identifier} ({self.role})"
