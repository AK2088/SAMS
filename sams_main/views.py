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
            
            pass


    return render(request, "login.html", {
        "credential_error": credential_error
    })


def otpVerification(request):
    error = False
    registration_success = False

    # ---------- COMMON OTP VALIDATION ----------
    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        otp_stored = request.session.get('otp')
        time_sent = request.session.get('time_sent')

        if not otp_stored or not time_sent:
            return redirect('login')

        current_time = datetime.now().timestamp()

        if otp_entered != str(otp_stored) or current_time - time_sent > 300:
            # wrong otp so we lower block wont be exexuted 
            error = True
        else:
            # ---------- PASSWORD RESET FLOW ----------
            if request.session.get('for_password_reset_faculty'):

                enrollment_id = request.session.get('enrollment_id')
                newPassword = request.session.get('newPass')

                user = User.objects.get(username=enrollment_id)
                user.password = make_password(newPassword)
                user.save()

                for key in ['otp', 'time_sent', 'for_password_reset', 'enrollment_id', 'email', 'newPass']:
                    request.session.pop(key, None)
                
                messages.success(request, "Password reset successful, please login with your new Password")

                return redirect('login')

            else:
                #---------- FACULTY REGISTRATION FLOW ----------
                if(request.session['faculty_register']):
                    if 'faculty_id' not in request.session:
                        return redirect('facultyRegister')

                    faculty_master = MasterFaculty.objects.get(id=request.session['faculty_id'])

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

                    for key in ['otp', 'faculty_id', 'time_sent', 'pass', 'email']:
                        request.session.pop(key, None)

                    registration_success = True
                else:
                    # Registraion for student
                    if 'roll' not in request.session:
                        return redirect('studentRegister')
                    
                    user = User.objects.create(
                        username=request.session['roll'],
                        email=request.session['email'],
                        password = make_password(request.session['pass']),
                    )

                    Student.objects.create(
                        name=request.session['name'],
                        user=user,
                        roll=request.session['roll'],
                        mail_verified=True,
                    )

                    registration_success=True
                    request.session.clear()



    context = {
        'email': request.session.get('email'),
        'error': error,
        'registration_success': registration_success
    }

    return render(request, 'otp_verification.html', context)


def passwordReset(request):
    credential_error = False
    email = ""

    if request.method == 'POST':
        if request.POST.get('role') == 'faculty':
            enrollment_id = request.POST.get('enrollment_id')

            try:
                user = User.objects.get(username=enrollment_id)
                email = user.email

                # ---------- OTP GENERATION ----------
                otp = random.randint(100000, 999999)
                request.session['otp'] = otp
                request.session['time_sent'] = datetime.now().timestamp()

                # ---------- PASSWORD RESET FLAGS ----------
                request.session['for_password_reset_faculty'] = True
                request.session['enrollment_id'] = enrollment_id
                request.session['email'] = email
                request.session['newPass'] = request.POST.get('newPass')

                # ---------- SEND MAIL ----------
                send_mail(
                    subject='OTP for resetting your password for SAMS',
                    message=f'Your OTP for password reset is {otp}. This otp is valid for 5 minutes only!',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[email],
                    fail_silently=False
                )

                return redirect('otp')

            except User.DoesNotExist:
                credential_error = True

        elif request.POST.get('role') == 'student':
            #student pass reset here 
            # man fuckk thiss shittt just take manual attendance 
            pass

    return render(request, 'forgot_password.html', {
        'error': credential_error,
        'email': email,
    })



def logoutView(request):
    logout(request)
    return redirect('login')
