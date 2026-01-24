"""
Faculty app views for registration and dashboard
"""
from datetime import datetime
from django.shortcuts import render, redirect
from .models import MasterFaculty, Teacher
import secrets  # Changed from random to secrets for secure OTP generation
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail

# Constants
OTP_MIN = 100000
OTP_MAX = 999999
OTP_EXPIRY_SECONDS = 300  # 5 minutes


def facultyRegister(request):
    """
    Handle faculty registration
    Verifies enrollment ID against MasterFaculty, generates OTP, and sends it to faculty email
    """
    error = False
    
    if request.method == 'POST':
        enrollment_id = request.POST.get("enrollment_id")

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
    user = request.user
    
    try:
        teacher = Teacher.objects.get(user=user)
        name = teacher.name

    except Teacher.DoesNotExist:
        return redirect('login')

    context = {
        'name': name,
    }

    return render(request, 'teacher_dashboard.html', context)
