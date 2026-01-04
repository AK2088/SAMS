from django.shortcuts import render

# Create your views here.

def facultyRegister(request):
    return render(request,'faculty_registration.html')

def renderDashboard(request):
    return render(request,'teacher_dashboard.html')
