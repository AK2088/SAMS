"""
Student app views for registration and dashboard
"""
from django.shortcuts import render, redirect
from datetime import datetime
import secrets  # Changed from random to secrets for secure OTP generation
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Student

# Constants
OTP_MIN = 100000
OTP_MAX = 999999
OTP_EXPIRY_SECONDS = 300  # 5 minutes


def studentRegister(request):
    """
    Handle student registration
    Collects student details, generates OTP, and sends it to student's KIIT email
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        roll = request.POST.get('roll')
        password = request.POST.get('password')
        
        # Construct KIIT email address from roll number
        domain = "@kiit.ac.in"
        mail = str(roll) + domain

        # Generate secure 6-digit OTP
        otp = secrets.randbelow(OTP_MAX - OTP_MIN + 1) + OTP_MIN
        
        # Store registration data in session for OTP verification
        request.session['otp'] = otp
        request.session['name'] = name
        request.session['time_sent'] = datetime.now().timestamp()
        request.session['roll'] = roll
        request.session['email'] = mail
        request.session['pass'] = password
        request.session['faculty_register'] = False  # Mark as student registration

        # Send OTP email (handle missing email settings gracefully)
        try:
            from_email = getattr(settings, 'EMAIL_HOST_USER', 'noreply@sams.local')
            send_mail(
                subject="Your OTP for SAMS registration",
                message=f"Your OTP is {otp}. This OTP will expire in 5 minutes.",
                from_email=from_email,
                recipient_list=[mail],
            )
        except Exception:
            # Email sending failed, but continue (will be caught in OTP verification)
            pass
        
        return redirect('otp')

    return render(request, 'student_registration.html')


@login_required
def renderDashboard(request):
    """
    Render student dashboard
    Requires user to be logged in and have a Student profile
    """
    name = ""
    user = request.user
    
    try:
        student = Student.objects.get(user=user)
        name = student.name

    except Student.DoesNotExist:
        # Fixed bug: Added return statement
        return redirect('login')

    context = {
        'name': name,
    }

    return render(request, 'student_dashboard.html', context)