"""
Student app views for registration and dashboard
"""
from django.shortcuts import render, redirect
from datetime import datetime
import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
import json
import base64
import io
import os
import numpy as np
from PIL import Image
import cv2
import torch
from .models import Student
from faculty_app.models import Attendance, ClassRoom, RollingQRToken

# Constants
OTP_MIN = 100000
OTP_MAX = 999999
OTP_EXPIRY_SECONDS = 300  # 5 minutes


def _time_status(start_time, end_time, now_time):
    # Used by dashboard cards to show quick class state labels.
    if not start_time or not end_time:
        return "Timing Not Set", "secondary"
    if start_time <= now_time <= end_time:
        return "Ongoing", "success"
    if now_time < start_time:
        return "Upcoming", "warning"
    return "Completed", "secondary"


def studentRegister(request):
    """
    Handle student registration
    Collects student details, generates OTP, and sends it to student's KIIT email.
    Also prevents duplicate registration for already registered students.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        roll = request.POST.get('roll')
        password = request.POST.get('password')

        # If student already exists, prompt to login instead of re-register
        if Student.objects.filter(roll=roll).exists():
            messages.info(request, "You are already registered. Please login.")
            return redirect('login')

        # Construct KIIT email address from roll number
        domain = "@kiit.ac.in"
        mail = str(roll) + domain

        # Generate secure 6-digit OTP
        otp = secrets.randbelow(OTP_MAX - OTP_MIN + 1) + OTP_MIN

        # Store registration data in session for OTP verification
        request.session['otp'] = otp
        request.session['name'] = name
        request.session['time_sent'] = datetime.now().timestamp()
        request.session['roll'] = roll
        request.session['email'] = mail
        request.session['pass'] = password
        request.session['faculty_register'] = False  # Mark as student registration

        # Send OTP email (handle missing email settings gracefully)
        try:
            from_email = getattr(settings, 'EMAIL_HOST_USER', 'noreply@sams.local')
            send_mail(
                subject="Your OTP for SAMS registration",
                message=f"Your OTP is {otp}. This OTP will expire in 5 minutes.",
                from_email=from_email,
                recipient_list=[mail],
            )
        except Exception:
            # Email sending failed, but continue (will be caught in OTP verification)
            pass

        return redirect('otp')

    return render(request, 'student/student_registration.html')


@login_required
def renderDashboard(request):
    """
    Render student dashboard
    Requires user to be logged in and have a Student profile
    """
    name = ""
    face_verified = False
    classes = []
    section_code = ""
    user = request.user
    
    try:
        # Load logged-in student's profile and classes for their section only.
        student = Student.objects.get(user=user)
        name = student.name
        face_verified = student.face_verified
        if student.section:
            section_code = student.section.code
            now_time = timezone.localtime().time()
            class_qs = (
                ClassRoom.objects.filter(section=student.section, is_active=True)
                .select_related("section", "teacher")
                .order_by("start_time", "subject_name")
            )
            for class_obj in class_qs:
                status_text, status_color = _time_status(class_obj.start_time, class_obj.end_time, now_time)
                classes.append(
                    {
                        "id": class_obj.id,
                        "subject_name": class_obj.subject_name,
                        "section_code": class_obj.section.code,
                        "teacher_name": class_obj.teacher.name,
                        "start_time": class_obj.start_time,
                        "end_time": class_obj.end_time,
                        "status_text": status_text,
                        "status_color": status_color,
                    }
                )

    except Student.DoesNotExist:
        return redirect('login')

    context = {
        'name': name,
        'face_verified': face_verified,
        'classes': classes,
        'section_code': section_code,
    }

    return render(request, 'student/student_dashboard.html', context)


# Initialize FaceNet models (load once, reuse)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = None
resnet = None

def get_face_models():
    """Load face recognition models (lazy initialization - models loaded on first use)"""
    global mtcnn, resnet
    try:
        from facenet_pytorch import MTCNN, InceptionResnetV1
    except Exception as exc:
        raise RuntimeError(f"Face recognition dependencies not available: {exc}")

    if mtcnn is None:
        mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, thresholds=[0.6, 0.7, 0.7], factor=0.709, device=device)
    if resnet is None:
        resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)
    return mtcnn, resnet


@login_required
def register_face(request):
    """
    Register student's facial biometrics
    Receives base64 image from frontend, extracts face embedding, and saves to Student model
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        user = request.user
        student = Student.objects.get(user=user)
        
        # Parse JSON data
        data = json.loads(request.body)
        image_b64 = data.get('image', '')
        
        if not image_b64:
            return JsonResponse({'error': 'No image provided'}, status=400)
        
        # Decode base64 image
        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]
        
        img_data = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(img_data))
        img_rgb = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGB)
        
        # Get face recognition models
        mtcnn_model, resnet_model = get_face_models()
        
        # Extract face and generate embedding
        face = mtcnn_model(img_rgb)
        if face is None:
            return JsonResponse({'error': 'No face detected. Please ensure your face is clearly visible.'}, status=400)
        
        embedding = resnet_model(face.unsqueeze(0)).detach().cpu().numpy().flatten()
        
        # Convert numpy array to list for JSON storage
        embedding_list = embedding.tolist()
        
        # Save to Student model (database)
        student.face_embedding = embedding_list
        student.face_verified = True
        student.save()
        
        
        return JsonResponse({
            'success': True,
            'message': 'Face registered successfully and saved to database',
            'face_verified': True
        })
        
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error processing face: {str(e)}'}, status=500)


def _decode_base64_image(image_b64):
    """Decode base64 image payload into RGB ndarray for face processing."""
    if ',' in image_b64:
        image_b64 = image_b64.split(',')[1]
    img_data = base64.b64decode(image_b64)
    img = Image.open(io.BytesIO(img_data))
    return cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGB)


def _cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two embeddings."""
    a = np.array(vec1, dtype=np.float32)
    b = np.array(vec2, dtype=np.float32)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return -1.0
    return float(np.dot(a, b) / denom)


@login_required
def scan_attendance_qr(request):
    """Validate scanned QR token and create/update pending attendance attempt."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        student = Student.objects.select_related("section").get(user=request.user)
    except Student.DoesNotExist:
        return JsonResponse({"error": "Student profile not found"}, status=404)

    if not student.section_id:
        return JsonResponse({"error": "Student is not assigned to any section."}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    token_value = (data.get("token") or "").strip()
    classroom_id = data.get("classroom_id")
    if not token_value:
        return JsonResponse({"error": "Token is required."}, status=400)
    if classroom_id is None:
        return JsonResponse({"error": "classroom_id is required."}, status=400)

    try:
        classroom_id = int(classroom_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid classroom_id."}, status=400)

    now = timezone.now()
    # Token must be active and unexpired at scan time.
    qr_token = (
        RollingQRToken.objects.select_related("session__classroom")
        .filter(token=token_value, is_active=True)
        .first()
    )
    if not qr_token:
        return JsonResponse({"error": "Invalid QR token."}, status=400)
    if qr_token.expires_at <= now:
        return JsonResponse({"error": "QR token expired."}, status=400)

    session = qr_token.session
    if not session.is_live:
        return JsonResponse({"error": "Attendance session is not live."}, status=400)
    if classroom_id != session.classroom_id:
        return JsonResponse({"error": "Scanned QR does not belong to selected class."}, status=400)

    # Hard authorization check: student can mark attendance only for classes in their own section.
    if session.classroom.section_id != student.section_id:
        return JsonResponse({"error": "You don't belong to this class."}, status=403)

    # One attendance record per student per session (enforced by model constraint too).
    attendance, created = Attendance.objects.get_or_create(
        session=session,
        student=student,
        defaults={
            "status": Attendance.STATUS_PENDING_FACE,
            "scanned_token": qr_token,
        },
    )
    if not created and attendance.status == Attendance.STATUS_PRESENT:
        return JsonResponse({"error": "Attendance already marked as present for this session."}, status=400)

    attendance.status = Attendance.STATUS_PENDING_FACE
    attendance.scanned_token = qr_token
    attendance.save(update_fields=["status", "scanned_token"])

    return JsonResponse(
        {
            "success": True,
            "attendance_id": attendance.id,
            "session_id": session.id,
            "subject_name": session.classroom.subject_name,
            "section_code": session.classroom.section.code,
            "message": "QR accepted. Proceed to face verification.",
        }
    )


@login_required
def verify_attendance_face(request):
    """Complete attendance by matching captured face with registered embedding."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return JsonResponse({"error": "Student profile not found"}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    attendance_id = data.get("attendance_id")
    image_b64 = data.get("image", "")
    if not attendance_id or not image_b64:
        return JsonResponse({"error": "attendance_id and image are required."}, status=400)
    if not student.face_embedding:
        return JsonResponse({"error": "No registered face embedding found for student."}, status=400)

    attendance = Attendance.objects.filter(id=attendance_id, student=student).select_related("session").first()
    if not attendance:
        return JsonResponse({"error": "Attendance record not found."}, status=404)

    try:
        # Extract live embedding from captured image.
        img_rgb = _decode_base64_image(image_b64)
        mtcnn_model, resnet_model = get_face_models()
        face = mtcnn_model(img_rgb)
        if face is None:
            return JsonResponse({"error": "No face detected. Try again."}, status=400)
        embedding = resnet_model(face.unsqueeze(0)).detach().cpu().numpy().flatten().tolist()
    except Exception as exc:
        return JsonResponse({"error": f"Error processing face: {exc}"}, status=500)

    # Default threshold can be tuned via settings.py (FACE_MATCH_THRESHOLD).
    threshold = float(getattr(settings, "FACE_MATCH_THRESHOLD", 0.70))
    score = _cosine_similarity(student.face_embedding, embedding)
    now = timezone.now()
    attendance.face_checked_at = now
    attendance.face_score = score

    if score >= threshold:
        attendance.status = Attendance.STATUS_PRESENT
        attendance.marked_at = now
        attendance.save(update_fields=["face_checked_at", "face_score", "status", "marked_at"])
        return JsonResponse(
            {
                "success": True,
                "match": True,
                "score": score,
                "threshold": threshold,
                "status": attendance.status,
                "message": "Face verified. Attendance marked present.",
            }
        )

    attendance.status = Attendance.STATUS_FACE_FAILED
    attendance.save(update_fields=["face_checked_at", "face_score", "status"])
    return JsonResponse(
        {
            "success": True,
            "match": False,
            "score": score,
            "threshold": threshold,
            "status": attendance.status,
            "message": "Face verification failed.",
        }
    )
