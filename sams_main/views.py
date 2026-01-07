from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from datetime import datetime
from django.shortcuts import render, redirect
from faculty_app.models import Teacher, MasterFaculty
from student_app.models import Student
from django.contrib.auth import authenticate, login as auth_login , logout
import random
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages



def home(request):
    return render(request, 'home.html')

def role(request):
    return render(request,'roles.html')


def loginView(request):
    
    credential_error = False

    if request.method == "POST":
        role = request.POST.get("roles")

        if role=="faculty":
            enrollment_id = request.POST.get("enrollment_id")
            password = request.POST.get("password")

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
                    if teacher.is_registered and teacher.mail_verified:
                        auth_login(request, user)
                        return redirect("fdashboard")

                except Teacher.DoesNotExist:
                    credential_error = True
        else:
            #student login implementation
            roll = request.POST.get("roll")
            password=request.POST.get("password")
            user = authenticate(request,username=roll,password=password)

            if user is None:
                credential_error=True
            try:
                student = Student.objects.get(user=user)
                if student.mail_verified:
                    auth_login(request, user)
                    return redirect("sdashboard")

            except Student.DoesNotExist:
                credential_error = True
            


    return render(request, "login.html", {
        "credential_error": credential_error
    })


def otpVerification(request):
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
        if otp_entered != str(otp_stored) or current_time - time_sent > 300:
            error = True

        else:
            # =====================================================
            # PASSWORD RESET FLOW
            # =====================================================

            # ---------- FACULTY PASSWORD RESET ----------
            if request.session.get('for_password_reset_faculty') is True:

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
            elif request.session.get('for_password_reset_faculty') is False:

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

                    faculty_master = MasterFaculty.objects.get(
                        id=request.session['faculty_id']
                    )

                    user = User.objects.create(
                        username=faculty_master.enrollment_id,
                        email=faculty_master.email,
                        password=make_password(request.session['pass'])
                    )

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

                    user = User.objects.create(
                        username=request.session['roll'],
                        email=request.session['email'],
                        password=make_password(request.session['pass']),
                    )

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



def passwordReset(request):
    credential_error = False
    email = ""

    # Clear stale reset state
    for key in ['otp', 'time_sent', 'for_password_reset_faculty', 'roll', 'enrollment_id', 'newPass']:
        request.session.pop(key, None)

    if request.method == 'POST':
        role = request.POST.get('role')

        # ================= FACULTY =================
        if role == 'faculty':
            enrollment_id = request.POST.get('enrollment_id')

            try:
                user = User.objects.get(username=enrollment_id)
                Teacher.objects.get(user=user)

                email = user.email

                otp = random.randint(100000, 999999)
                request.session['otp'] = otp
                request.session['time_sent'] = datetime.now().timestamp()
                request.session['for_password_reset_faculty'] = True
                request.session['enrollment_id'] = enrollment_id
                request.session['email'] = email
                request.session['newPass'] = request.POST.get('newPass')

                send_mail(
                    subject='OTP for resetting your password for SAMS',
                    message=f'Your OTP is {otp}. Valid for 5 minutes.',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[email],
                )

                return redirect('otp')

            except (User.DoesNotExist, Teacher.DoesNotExist):
                credential_error = True

        # ================= STUDENT =================
        elif role == 'student':
            roll = request.POST.get("roll")

            try:
                user = User.objects.get(username=roll)
                Student.objects.get(user=user)

                email = user.email

                otp = random.randint(100000, 999999)
                request.session['otp'] = otp
                request.session['time_sent'] = datetime.now().timestamp()
                request.session['for_password_reset_faculty'] = False
                request.session['roll'] = roll
                request.session['email'] = email
                request.session['newPass'] = request.POST.get('newPass')

                send_mail(
                    subject='OTP for resetting your password for SAMS',
                    message=f'Your OTP is {otp}. Valid for 5 minutes.',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[email],
                )

                return redirect('otp')

            except (User.DoesNotExist, Student.DoesNotExist):
                credential_error = True

    return render(request, 'forgot_password.html', {
        'error': credential_error,
        'email': email,
    })






def logoutView(request):
    request.session.flush()
    logout(request)

    return redirect('login')
