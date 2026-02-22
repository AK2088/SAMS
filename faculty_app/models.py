"""
Faculty app models
Defines Teacher and MasterFaculty models plus attendance domain models
"""
import secrets
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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


class Section(models.Model):
    """
    Academic section/batch (for example: CSE-12).
    Students belong to exactly one section.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    expected_strength = models.PositiveIntegerField(default=40)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return f"{self.code} - {self.name}"


class ClassRoom(models.Model):
    """
    A teachable class card shown on dashboards.
    One teacher can handle many classes/sections.
    """
    subject_name = models.CharField(max_length=120)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="classes")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="classes")
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("section__code", "subject_name")

    def __str__(self):
        return f"{self.subject_name} ({self.section.code})"


class AttendanceSession(models.Model):
    """
    One live attendance window created when teacher clicks "Take Attendance".
    """
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="sessions")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="attendance_sessions")
    session_date = models.DateField(default=timezone.localdate)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_live = models.BooleanField(default=True)
    qr_validity_seconds = models.PositiveIntegerField(default=15)

    class Meta:
        ordering = ("-started_at",)

    def __str__(self):
        return f"{self.classroom} @ {self.started_at:%Y-%m-%d %H:%M}"


class RollingQRToken(models.Model):
    """
    Short-lived QR tokens generated repeatedly for one AttendanceSession.
    """
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="qr_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-issued_at",)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"{self.session_id} token @ {self.issued_at:%H:%M:%S}"


class Attendance(models.Model):
    """
    Student attendance state per session.
    QR must be valid at scan time, face check may happen later.
    """
    STATUS_PENDING_FACE = "pending_face"
    STATUS_PRESENT = "present"
    STATUS_FACE_FAILED = "face_failed"
    STATUS_CHOICES = (
        (STATUS_PENDING_FACE, "Pending Face"),
        (STATUS_PRESENT, "Present"),
        (STATUS_FACE_FAILED, "Face Failed"),
    )

    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="attendance_records")
    student = models.ForeignKey("student_app.Student", on_delete=models.CASCADE, related_name="attendance_records")
    scanned_token = models.ForeignKey(
        RollingQRToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_scans",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING_FACE)
    qr_scanned_at = models.DateTimeField(auto_now_add=True)
    face_checked_at = models.DateTimeField(null=True, blank=True)
    marked_at = models.DateTimeField(null=True, blank=True)
    face_score = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ("-qr_scanned_at",)
        constraints = [
            models.UniqueConstraint(fields=["session", "student"], name="uniq_session_student_attendance")
        ]

    def __str__(self):
        return f"{self.student.roll} - {self.session_id} - {self.status}"
