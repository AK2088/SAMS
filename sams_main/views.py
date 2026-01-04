from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from datetime import datetime
from django.shortcuts import render, redirect
from faculty_app.models import Teacher, MasterFaculty
from django.contrib.auth import authenticate, login as auth_login


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
        else :
            #studnet login logic here
            pass


    return render(request, "login.html", {
        "credential_error": credential_error
    })


def otpVerification(request):
    error = False
    registration_success = False

    if 'faculty_id' not in request.session:
        return redirect('facultyRegister')

    if request.method == 'POST':
        otp_entered = request.POST.get('otp')

        otp_stored = request.session.get('otp')
        time_sent = request.session.get('time_sent')

        if not otp_stored or not time_sent:
            return redirect('facultyRegister')

        current_time = datetime.now().timestamp()

        if otp_entered == str(otp_stored) and current_time - time_sent <= 300:
            
            faculty_master = MasterFaculty.objects.get(
                id=request.session['faculty_id']
            )

            user = User.objects.create(
                username=faculty_master.enrollment_id,
                email=faculty_master.email,
                password=make_password(request.session['pass'])
            )

            teacher = Teacher.objects.create(
                user=user,
                enrollment_id=faculty_master.enrollment_id,
                department=faculty_master.department,
                designation=faculty_master.designation,
                mail_verified=True,
                is_registered=True
            )

            for key in ['otp', 'faculty_id', 'time_sent', 'pass', 'email']:
                request.session.pop(key, None)
            
            registration_success = True

        else:
            error = True

    context = {
        'email': request.session.get('email'),
        'error': error,
        'registration_success' : registration_success,

    }

    return render(request, 'otp_verification.html', context)


def passwordReset(request):
    return render(request,'forgot_password.html')
