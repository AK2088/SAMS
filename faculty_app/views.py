"""
Faculty app views for registration and dashboard
"""
from datetime import datetime
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import ClassRoom, MasterFaculty, Teacher
import secrets  # Changed from random to secrets for secure OTP generation
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages

# Constants
OTP_MIN = 100000
OTP_MAX = 999999
OTP_EXPIRY_SECONDS = 300  # 5 minutes


def _time_status(start_time, end_time, now_time):
    if not start_time or not end_time:
        return "Timing Not Set", "secondary"
    if start_time <= now_time <= end_time:
        return "Ongoing", "success"
    if now_time < start_time:
        return "Upcoming", "warning"
    return "Completed", "secondary"


def facultyRegister(request):
    """
    Handle faculty registration
    Verifies enrollment ID against MasterFaculty, generates OTP, and sends it to faculty email.
    Also prevents duplicate registration for already registered faculty.
    """
    error = False

    if request.method == 'POST':
        enrollment_id = request.POST.get("enrollment_id")

        # If teacher already exists, prompt to login instead of re-register
        if Teacher.objects.filter(enrollment_id=enrollment_id).exists():
            messages.info(request, "You are already registered. Please login.")
            return redirect('login')

        try:
            # Verify enrollment ID exists in MasterFaculty
            faculty = MasterFaculty.objects.get(enrollment_id=enrollment_id)

            # Generate secure 6-digit OTP
            otp = secrets.randbelow(OTP_MAX - OTP_MIN + 1) + OTP_MIN

            # Store registration data in session for OTP verification
            request.session['otp'] = otp
            request.session['time_sent'] = datetime.now().timestamp()
            request.session['faculty_id'] = faculty.id
            request.session['email'] = faculty.email
            request.session['pass'] = request.POST.get('passwd')
            request.session['faculty_register'] = True  # Mark as faculty registration

            # Send OTP email (handle missing email settings gracefully)
            try:
                from_email = getattr(settings, 'EMAIL_HOST_USER', 'noreply@sams.local')
                send_mail(
                    subject="Your OTP for SAMS registration",
                    message=f"Your OTP is {otp}. This OTP will expire in 5 minutes.",
                    from_email=from_email,
                    recipient_list=[faculty.email],
                )
            except Exception:
                # Email sending failed, but continue (will be caught in OTP verification)
                pass

            return redirect('otp')

        except MasterFaculty.DoesNotExist:
            # Enrollment ID not found in master list
            error = True

    return render(request, 'faculty_registration.html', {'error': error})

@login_required
def renderDashboard(request):
    """
    Render faculty/teacher dashboard
    Requires user to be logged in and have a Teacher profile
    """
    name = ""
    classes = []
    user = request.user
    
    try:
        teacher = Teacher.objects.get(user=user)
        name = teacher.name
        now_time = timezone.localtime().time()
        class_qs = (
            ClassRoom.objects.filter(teacher=teacher, is_active=True)
            .select_related("section")
            .order_by("start_time", "subject_name")
        )
        for class_obj in class_qs:
            status_text, status_color = _time_status(class_obj.start_time, class_obj.end_time, now_time)
            classes.append(
                {
                    "id": class_obj.id,
                    "subject_name": class_obj.subject_name,
                    "section_code": class_obj.section.code,
                    "start_time": class_obj.start_time,
                    "end_time": class_obj.end_time,
                    "status_text": status_text,
                    "status_color": status_color,
                }
            )

    except Teacher.DoesNotExist:
        return redirect('login')

    context = {
        'name': name,
        'classes': classes,
    }

    return render(request, 'teacher_dashboard.html', context)
