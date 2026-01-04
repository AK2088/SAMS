from django.shortcuts import render

# Create your views here.
def studentRegister(request):
    return render(request,'student_registration.html')

def renderDashboard(request):
    return render(request,'student_dashboard.html')