"""
Main authentication views for SAMS (Smart Attendance Management System)
Handles login, OTP verification, password reset, and logout functionality
"""
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from datetime import datetime
from django.shortcuts import render, redirect
from faculty_app.models import Teacher, MasterFaculty
from student_app.models import Student
from django.contrib.auth import authenticate, login as auth_login , logout
import secrets  # Changed from random to secrets for secure OTP generation
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages

# Constants
OTP_EXPIRY_SECONDS = 300  # OTP valid for 5 minutes
OTP_MIN = 100000
OTP_MAX = 999999



def home(request):
    """Render the home page"""
    return render(request, 'home.html')

def role(request):
    """Render the role selection page for registration"""
    return render(request,'roles.html')


def loginView(request):
    """
    Handle user login for both students and faculty
    Validates credentials and checks if user is registered and email verified
    """
    credential_error = False

    if request.method == "POST":
        role = request.POST.get("roles")

        # ================= FACULTY LOGIN =================
        if role == "faculty":
            enrollment_id = request.POST.get("enrollment_id")
            password = request.POST.get("password")

            # Authenticate user with Django's built-in authentication
            user = authenticate(
                request,
                username=enrollment_id,
                password=password
            )

            if user is None:
                credential_error = True
            else:
                try:
                    teacher = Teacher.objects.get(user=user)
                    # Check if teacher is registered and email is verified
                    if teacher.is_registered and teacher.mail_verified:
                        auth_login(request, user)
                        return redirect("fdashboard")
                    else:
                        credential_error = True

                except Teacher.DoesNotExist:
                    credential_error = True
        
        # ================= STUDENT LOGIN =================
        else:
            roll = request.POST.get("roll")
            password = request.POST.get("password")
            
            # Authenticate user with Django's built-in authentication
            user = authenticate(request, username=roll, password=password)

            if user is None:
                credential_error = True
            else:
                try:
                    student = Student.objects.get(user=user)
                    # Check if student email is verified
                    if student.mail_verified:
                        auth_login(request, user)
                        return redirect("sdashboard")
                    else:
                        credential_error = True

                except Student.DoesNotExist:
                    credential_error = True

    return render(request, "login.html", {
        "credential_error": credential_error
    })


def otpVerification(request):
    """
    Verify OTP for registration or password reset
    Handles both student and faculty flows
    """
    error = False
    registration_success = False
    display_email = request.session.get('email')

    if request.method == 'POST':
        # ---------- OTP DATA ----------
        otp_entered = request.POST.get('otp')
        otp_stored = request.session.get('otp')
        time_sent = request.session.get('time_sent')

        # Missing / expired session → restart flow
        if not otp_stored or not time_sent:
            return redirect('login')

        current_time = datetime.now().timestamp()

        # ---------- OTP VALIDATION ----------
        # Check if OTP matches and hasn't expired (5 minutes)
        if otp_entered != str(otp_stored) or current_time - time_sent > OTP_EXPIRY_SECONDS:
            error = True

        else:
            # =====================================================
            # PASSWORD RESET FLOW
            # =====================================================
            is_password_reset = request.session.get('for_password_reset_faculty')
            
            # ---------- FACULTY PASSWORD RESET ----------
            if is_password_reset is True:
                enrollment_id = request.session.get('enrollment_id')
                newPassword = request.session.get('newPass')

                user = User.objects.get(username=enrollment_id)
                user.password = make_password(newPassword)
                user.save()

                # Password reset finished → clear EVERYTHING
                request.session.flush()

                messages.success(
                    request,
                    "Password reset successful, please login with your new Password"
                )
                return redirect('login')

            # ---------- STUDENT PASSWORD RESET ----------
            elif is_password_reset is False:
                roll = request.session.get("roll")
                newPassword = request.session.get("newPass")

                user = User.objects.get(username=roll)
                user.password = make_password(newPassword)
                user.save()

                # Password reset finished → clear EVERYTHING
                request.session.flush()

                messages.success(
                    request,
                    "Password reset successful, please login with your new Password"
                )
                return redirect('login')

            # =====================================================
            # REGISTRATION FLOW
            # =====================================================
            else:
                # ---------- FACULTY REGISTRATION ----------
                if request.session.get('faculty_register'):
                    if 'faculty_id' not in request.session:
                        return redirect('facultyRegister')

                    # Get faculty master record
                    faculty_master = MasterFaculty.objects.get(
                        id=request.session['faculty_id']
                    )

                    # Create Django User account
                    user = User.objects.create(
                        username=faculty_master.enrollment_id,
                        email=faculty_master.email,
                        password=make_password(request.session['pass'])
                    )

                    # Create Teacher profile linked to user
                    Teacher.objects.create(
                        user=user,
                        name=faculty_master.name,
                        enrollment_id=faculty_master.enrollment_id,
                        department=faculty_master.department,
                        designation=faculty_master.designation,
                        mail_verified=True,
                        is_registered=True,
                    )

                    registration_success = True

                    # Registration complete → clear EVERYTHING
                    request.session.flush()

                # ---------- STUDENT REGISTRATION ----------
                else:
                    if 'roll' not in request.session:
                        return redirect('studentRegister')

                    # Create Django User account
                    user = User.objects.create(
                        username=request.session['roll'],
                        email=request.session['email'],
                        password=make_password(request.session['pass']),
                    )

                    # Create Student profile linked to user
                    Student.objects.create(
                        name=request.session['name'],
                        user=user,
                        roll=request.session['roll'],
                        mail_verified=True,
                    )

                    registration_success = True

                    # Registration complete → clear EVERYTHING
                    request.session.flush()

    context = {
    'email':display_email,
    'error': error,
    'registration_success': registration_success
    }
    return render(request, 'otp_verification.html', context)



def _generate_otp():
    """
    Helper function to generate secure 6-digit OTP
    Uses secrets module for cryptographically secure random generation
    """
    return secrets.randbelow(OTP_MAX - OTP_MIN + 1) + OTP_MIN


def _send_otp_email(email, otp, purpose='password reset'):
    """
    Helper function to send OTP email
    Handles missing email settings gracefully
    """
    try:
        # Use a default from_email if EMAIL_HOST_USER is not set
        from_email = getattr(settings, 'EMAIL_HOST_USER', 'noreply@sams.local')
        
        send_mail(
            subject=f'OTP for {purpose} for SAMS',
            message=f'Your OTP is {otp}. Valid for 5 minutes.',
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        # Log error in production (for now, just return False)
        return False


def passwordReset(request):
    """
    Handle password reset request
    Sends OTP to user's registered email for verification
    """
    credential_error = False
    email = ""

    # Clear stale reset state from previous attempts
    for key in ['otp', 'time_sent', 'for_password_reset_faculty', 'roll', 'enrollment_id', 'newPass']:
        request.session.pop(key, None)

    if request.method == 'POST':
        role = request.POST.get('role')

        # ================= FACULTY PASSWORD RESET =================
        if role == 'faculty':
            enrollment_id = request.POST.get('enrollment_id')

            try:
                # Verify user exists and is a faculty member
                user = User.objects.get(username=enrollment_id)
                Teacher.objects.get(user=user)

                email = user.email

                # Generate secure OTP
                otp = _generate_otp()
                
                # Store OTP and related data in session
                request.session['otp'] = otp
                request.session['time_sent'] = datetime.now().timestamp()
                request.session['for_password_reset_faculty'] = True
                request.session['enrollment_id'] = enrollment_id
                request.session['email'] = email
                request.session['newPass'] = request.POST.get('newPass')

                # Send OTP email
                _send_otp_email(email, otp, 'resetting your password')

                return redirect('otp')

            except (User.DoesNotExist, Teacher.DoesNotExist):
                credential_error = True

        # ================= STUDENT PASSWORD RESET =================
        elif role == 'student':
            roll = request.POST.get("roll")

            try:
                # Verify user exists and is a student
                user = User.objects.get(username=roll)
                Student.objects.get(user=user)

                email = user.email

                # Generate secure OTP
                otp = _generate_otp()
                
                # Store OTP and related data in session
                request.session['otp'] = otp
                request.session['time_sent'] = datetime.now().timestamp()
                request.session['for_password_reset_faculty'] = False  # False = student
                request.session['roll'] = roll
                request.session['email'] = email
                request.session['newPass'] = request.POST.get('newPass')

                # Send OTP email
                _send_otp_email(email, otp, 'resetting your password')

                return redirect('otp')

            except (User.DoesNotExist, Student.DoesNotExist):
                credential_error = True

    return render(request, 'forgot_password.html', {
        'error': credential_error,
        'email': email,
    })




def logoutView(request):
    """
    Handle user logout
    Clears all session data and logs out the user
    """
    request.session.flush()
    logout(request)

    return redirect('login')
