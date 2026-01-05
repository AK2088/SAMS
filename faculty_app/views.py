from datetime import datetime
from django.shortcuts import render, redirect
from .models import MasterFaculty,Teacher
import random
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail

def facultyRegister(request):
    error = False
    if request.method == 'POST':
        enrollment_id = request.POST.get("enrollment_id")

        try:
            faculty = MasterFaculty.objects.get(enrollment_id=enrollment_id)

            otp = random.randint(100000, 999999)

            request.session['otp'] = otp
            request.session['time_sent'] = datetime.now().timestamp()
            request.session['faculty_id'] = faculty.id
            request.session['email']= faculty.email
            request.session['pass']= request.POST.get('passwd')

            send_mail(
                subject="Your OTP for SAMS registration",
                message=f"Your OTP is {otp}. This OTP will expire in 5 minutes.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[faculty.email],
            )

            return redirect('otp')

        except MasterFaculty.DoesNotExist:
            error = True

    return render(request, 'faculty_registration.html', {'error': error})

@login_required
def renderDashboard(request):
    name = ""
    user = request.user
    try:
        teacher = Teacher.objects.get(user=user)
        name = teacher.name

    except Teacher.DoesNotExist:
        redirect('login')

    context={
        'name':name,
    }

    return render(request, 'teacher_dashboard.html',context)
