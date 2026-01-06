from django.shortcuts import render,redirect
from datetime import datetime
import random
from django.core.mail import send_mail
from django.conf import settings


# Create your views here.
def studentRegister(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        roll = request.POST.get('roll')
        password = request.POST.get('password')
        domain = "@kiit.ac.in"
        mail= str(roll)+domain

        otp = random.randint(100000, 999999)
        request.session['otp'] = otp
        request.session['name']=name
        request.session['time_sent'] = datetime.now().timestamp()
        request.session['roll'] = roll
        request.session['email']= mail
        request.session['pass']= password
        request.session['faculty_register']=False

        send_mail(
        subject="Your OTP for SAMS registration",
        message=f"Your OTP is {otp}. This OTP will expire in 5 minutes.",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[mail],
        )
        
        return redirect('otp')


    return render(request,'student_registration.html')

def renderDashboard(request):
    return render(request,'student_dashboard.html')