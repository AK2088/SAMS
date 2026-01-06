from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone
from django.db import models

class Student(models.Model):
    name=models.CharField(max_length=50,null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    roll = models.IntegerField(unique=True)
    face_embedding = models.JSONField(null=True, blank=True)

    mail_verified = models.BooleanField(default=False)
    face_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_verified(self):
        return self.mail_verified and self.face_verified

    def __str__(self):
        return f"{self.user.username} ({self.roll})"



