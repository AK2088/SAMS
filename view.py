import json
import qrcode
from io import BytesIO
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import Session, Attendance, Student
import openpyxl


@login_required
def create_session(request):
    if request.method == "POST":
        subject = request.POST.get("subject")
        expires = timezone.now() + timedelta(minutes=2)

        session = Session.objects.create(
            subject=subject,
            created_by=request.user,
            expires_at=expires
        )

        return redirect("session_page", session_id=session.session_id)

    return render(request, "create_session.html")


@login_required
def session_page(request, session_id):
    session = get_object_or_404(Session, session_id=session_id)

    qr_data = {
        "session_id": str(session.session_id)
    }

    qr = qrcode.make(json.dumps(qr_data))
    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    qr_base64 = buffer.getvalue().hex()

    count = Attendance.objects.filter(session=session).count()

    return render(request, "session_page.html", {
        "session": session,
        "qr_data": json.dumps(qr_data),
        "count": count
    })


def mark_attendance(request):
    if request.method == "POST":
        data = json.loads(request.body)
        session_id = data.get("session_id")
        roll = data.get("roll")
        name = data.get("name")

        session = get_object_or_404(Session, session_id=session_id)

        if not session.is_active():
            return JsonResponse({"error": "Session expired"}, status=400)

        student, _ = Student.objects.get_or_create(
            roll=roll,
            defaults={"name": name}
        )

        Attendance.objects.get_or_create(
            session=session,
            student=student
        )

        return JsonResponse({"status": "success"})

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def export_excel(request, session_id):
    session = get_object_or_404(Session, session_id=session_id)
    records = Attendance.objects.filter(session=session)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Roll", "Name", "Timestamp"])

    for r in records:
        ws.append([r.student.roll, r.student.name, r.timestamp.strftime("%Y-%m-%d %H:%M:%S")])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f"attachment; filename=attendance_{session.subject}.xlsx"
    wb.save(response)

    return response