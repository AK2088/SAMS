"""
Faculty app views for registration and dashboard
"""
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils.html import escape
from django.utils import timezone
from .models import Attendance, AttendanceSession, ClassRoom, MasterFaculty, RollingQRToken, Teacher
import secrets 
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages

# Constants
OTP_MIN = 100000
OTP_MAX = 999999
OTP_EXPIRY_SECONDS = 300  # 5 minutes


def _time_status(start_time, end_time, now_time):
    # Shared helper for dashboard status badge.
    if not start_time or not end_time:
        return "Timing Not Set", "secondary"
    if start_time <= now_time <= end_time:
        return "Ongoing", "success"
    if now_time < start_time:
        return "Upcoming", "warning"
    return "Completed", "secondary"


def _issue_new_token(session):
    """Deactivate old token(s) and issue a fresh QR token for a live session."""
    now = timezone.now()
    session.qr_tokens.filter(is_active=True).update(is_active=False)
    return RollingQRToken.objects.create(
        session=session,
        expires_at=now + timedelta(seconds=session.qr_validity_seconds),
        is_active=True,
    )


def _get_or_rotate_token(session):
    """Return active unexpired token; rotate if none exists."""
    now = timezone.now()
    token = (
        session.qr_tokens.filter(is_active=True, expires_at__gt=now)
        .order_by("-issued_at")
        .first()
    )
    if token:
        return token
    return _issue_new_token(session)


def facultyRegister(request):
    """
    Handle faculty registration
    Verifies enrollment ID against MasterFaculty, generates OTP, and sends it to faculty email.
    Also prevents duplicate registration for already registered faculty.
    """
    error = False

    if request.method == 'POST':
        # Enrollment ID is validated against master faculty records.
        enrollment_id = request.POST.get("enrollment_id")

        # If teacher already exists, prompt to login instead of re-register
        if Teacher.objects.filter(enrollment_id=enrollment_id).exists():
            messages.info(request, "You are already registered. Please login.")
            return redirect('login')

        try:
            # Verify enrollment ID exists in MasterFaculty
            faculty = MasterFaculty.objects.get(enrollment_id=enrollment_id)

            # Generate secure 6-digit OTP
            otp = secrets.randbelow(OTP_MAX - OTP_MIN + 1) + OTP_MIN

            # Store registration data in session for OTP verification
            request.session['otp'] = otp
            request.session['time_sent'] = datetime.now().timestamp()
            request.session['faculty_id'] = faculty.id
            request.session['email'] = faculty.email
            request.session['pass'] = request.POST.get('passwd')
            request.session['faculty_register'] = True  # Mark as faculty registration

            # Send OTP email (handle missing email settings gracefully)
            try:
                from_email = getattr(settings, 'EMAIL_HOST_USER', 'noreply@sams.local')
                send_mail(
                    subject="Your OTP for SAMS registration",
                    message=f"Your OTP is {otp}. This OTP will expire in 5 minutes.",
                    from_email=from_email,
                    recipient_list=[faculty.email],
                )
            except Exception:
                # Email sending failed, but continue (will be caught in OTP verification)
                pass

            return redirect('otp')

        except MasterFaculty.DoesNotExist:
            # Enrollment ID not found in master list
            error = True

    return render(request, 'teacher/faculty_registration.html', {'error': error})

@login_required
def renderDashboard(request):
    """
    Render faculty/teacher dashboard
    Requires user to be logged in and have a Teacher profile
    """
    name = ""
    classes = []
    user = request.user
    
    try:
        # Teacher sees only classes assigned to their profile.
        teacher = Teacher.objects.get(user=user)
        name = teacher.name
        now_time = timezone.localtime().time()
        class_qs = (
            ClassRoom.objects.filter(teacher=teacher, is_active=True)
            .select_related("section")
            .order_by("start_time", "subject_name")
        )
        for class_obj in class_qs:
            status_text, status_color = _time_status(class_obj.start_time, class_obj.end_time, now_time)
            classes.append(
                {
                    "id": class_obj.id,
                    "subject_name": class_obj.subject_name,
                    "section_code": class_obj.section.code,
                    "start_time": class_obj.start_time,
                    "end_time": class_obj.end_time,
                    "status_text": status_text,
                    "status_color": status_color,
                }
            )

    except Teacher.DoesNotExist:
        return redirect('login')

    context = {
        'name': name,
        'classes': classes,
    }

    return render(request, 'teacher/teacher_dashboard.html', context)


@login_required
@require_POST
def start_attendance_session(request, classroom_id):
    """Start a new live attendance session for a teacher-owned classroom."""
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return JsonResponse({"error": "Teacher profile not found."}, status=404)

    classroom = ClassRoom.objects.filter(id=classroom_id, teacher=teacher, is_active=True).first()
    if not classroom:
        return JsonResponse({"error": "Class not found for this teacher."}, status=404)

    # Reuse existing live session to avoid race/double-click invalidation.
    session = (
        AttendanceSession.objects.filter(classroom=classroom, teacher=teacher, is_live=True)
        .order_by("-started_at")
        .first()
    )
    if session:
        token = _get_or_rotate_token(session)
    else:
        session = AttendanceSession.objects.create(
            classroom=classroom,
            teacher=teacher,
            is_live=True,
            qr_validity_seconds=15,
        )
        token = _issue_new_token(session)
    return JsonResponse(
        {
            "success": True,
            "session_id": session.id,
            "token": token.token,
            "expires_at": token.expires_at.isoformat(),
            "validity_seconds": session.qr_validity_seconds,
            "classroom_id": classroom.id,
        }
    )


@login_required
@require_GET
def current_qr_token(request, session_id):
    """Fetch current token for a live session, rotating if expired."""
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return JsonResponse({"error": "Teacher profile not found."}, status=404)

    session = AttendanceSession.objects.filter(id=session_id, teacher=teacher).select_related("classroom").first()
    if not session:
        return JsonResponse({"error": "Session not found."}, status=404)
    if not session.is_live:
        return JsonResponse({"error": "Session is not live."}, status=400)

    token = _get_or_rotate_token(session)
    return JsonResponse(
        {
            "success": True,
            "session_id": session.id,
            "token": token.token,
            "expires_at": token.expires_at.isoformat(),
            "is_live": session.is_live,
            "classroom_id": session.classroom_id,
        }
    )


@login_required
@require_POST
def stop_attendance_session(request, session_id):
    """Stop a live attendance session and invalidate active tokens."""
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return JsonResponse({"error": "Teacher profile not found."}, status=404)

    session = AttendanceSession.objects.filter(id=session_id, teacher=teacher).first()
    if not session:
        return JsonResponse({"error": "Session not found."}, status=404)
    if not session.is_live:
        return JsonResponse({"success": True, "message": "Session already stopped."})

    session.is_live = False
    session.ended_at = timezone.now()
    session.save(update_fields=["is_live", "ended_at"])
    session.qr_tokens.filter(is_active=True).update(is_active=False)

    return JsonResponse({"success": True, "message": "Attendance session stopped."})


@login_required
@require_GET
def download_attendance_csv(request, classroom_id):
    """
    Export latest session attendance for the class as Excel-compatible .xls.
    Keeps dependency footprint small by using HTML table output.
    """
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return JsonResponse({"error": "Teacher profile not found."}, status=404)

    classroom = ClassRoom.objects.filter(id=classroom_id, teacher=teacher).select_related("section").first()
    if not classroom:
        return JsonResponse({"error": "Class not found for this teacher."}, status=404)

    session = AttendanceSession.objects.filter(classroom=classroom, teacher=teacher).order_by("-started_at").first()
    if not session:
        return JsonResponse({"error": "Take attendance first before downloading the sheet."}, status=400)

    # Don't allow download when no attendance attempt exists.
    if not Attendance.objects.filter(session=session).exists():
        return JsonResponse({"error": "Take attendance first before downloading the sheet."}, status=400)

    teacher_name = teacher.name or teacher.enrollment_id
    students = classroom.section.students.select_related("user").order_by("roll")
    attendance_map = {
        row.student_id: row
        for row in Attendance.objects.filter(session=session).select_related("student")
    }

    rows = []
    present_count = 0
    for student in students:
        # If no record exists for student in this session, they are absent.
        row = attendance_map.get(student.id)
        status = "ABSENT"
        attendance_time = ""
        attendance_date = ""
        score = ""
        if row:
            status = row.status.upper()
            stamp = row.marked_at or row.qr_scanned_at
            if stamp:
                local_stamp = timezone.localtime(stamp)
                attendance_date = local_stamp.strftime("%Y-%m-%d")
                attendance_time = local_stamp.strftime("%H:%M:%S")
            score = f"{row.face_score:.4f}" if row.face_score is not None else ""
            if row.status == Attendance.STATUS_PRESENT:
                present_count += 1
        rows.append(
            {
                "roll": student.roll,
                "name": student.name,
                "status": status,
                "date": attendance_date,
                "time": attendance_time,
                "score": score,
            }
        )

    strength = students.count()
    absent_count = strength - present_count
    started_local = timezone.localtime(session.started_at)
    ended_local = timezone.localtime(session.ended_at).strftime("%Y-%m-%d %H:%M:%S") if session.ended_at else "LIVE"

    # Excel-compatible HTML table output (.xls)
    html = [
        "<html><head><meta charset='utf-8'></head><body>",
        "<table border='1'>",
        f"<tr><td><b>Class Name</b></td><td>{escape(classroom.subject_name)}</td></tr>",
        f"<tr><td><b>Teacher</b></td><td>{escape(teacher_name)}</td></tr>",
        f"<tr><td><b>Section</b></td><td>{escape(classroom.section.code)}</td></tr>",
        f"<tr><td><b>Session ID</b></td><td>{session.id}</td></tr>",
        f"<tr><td><b>Session Date</b></td><td>{started_local.strftime('%Y-%m-%d')}</td></tr>",
        f"<tr><td><b>Started At</b></td><td>{started_local.strftime('%H:%M:%S')}</td></tr>",
        f"<tr><td><b>Ended At</b></td><td>{ended_local}</td></tr>",
        "<tr><td colspan='7'></td></tr>",
        "<tr>"
        "<th>Roll No</th><th>Student Name</th><th>Class Name</th><th>Section</th>"
        "<th>Attendance Date</th><th>Attendance Time</th><th>Status</th>"
        "</tr>",
    ]
    for row in rows:
        html.append(
            "<tr>"
            f"<td>{row['roll']}</td>"
            f"<td>{escape(row['name'] or '')}</td>"
            f"<td>{escape(classroom.subject_name)}</td>"
            f"<td>{escape(classroom.section.code)}</td>"
            f"<td>{row['date']}</td>"
            f"<td>{row['time']}</td>"
            f"<td>{row['status']}</td>"
            "</tr>"
        )
    html.extend(
        [
            "<tr><td colspan='7'></td></tr>",
            f"<tr><td><b>Class Strength</b></td><td>{strength}</td><td colspan='5'></td></tr>",
            f"<tr><td><b>Present</b></td><td>{present_count}</td><td colspan='5'></td></tr>",
            f"<tr><td><b>Absent</b></td><td>{absent_count}</td><td colspan='5'></td></tr>",
            "</table></body></html>",
        ]
    )

    response = HttpResponse("".join(html), content_type="application/vnd.ms-excel; charset=utf-8")
    raw_filename = f"{classroom.section.code}-{classroom.subject_name}"
    safe_filename = (
        raw_filename.replace("\\", "")
        .replace("/", "")
        .replace(":", "")
        .replace("*", "")
        .replace("?", "")
        .replace('"', "")
        .replace("<", "")
        .replace(">", "")
        .replace("|", "")
        .strip()
    ) or f"attendance_{classroom.id}"
    response["Content-Disposition"] = (
        f'attachment; filename="{safe_filename}.xls"'
    )
    return response
