from django.db import models
from django.contrib.auth.models import User

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=150,blank=True)
    enrollment_id = models.CharField(max_length=10, unique=True)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    mail_verified = models.BooleanField(default=False)
    is_registered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    upadated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.enrollment_id})"
    

class MasterFaculty(models.Model):
    class Meta:
        verbose_name = "Faculty"
        verbose_name_plural = "Faculty Master"
    
    enrollment_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.enrollment_id})"
