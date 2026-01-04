from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def role(request):
    return render(request,'roles.html')

def login(request):
    return render(request,'login.html')

def otpVerification(request):
    return render(request,'otp_verification.html')

def passwordReset(request):
    return render(request,'forgot_password.html')
