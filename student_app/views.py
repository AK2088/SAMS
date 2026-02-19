"""
Student app views for registration and dashboard
"""
from django.shortcuts import render, redirect
from datetime import datetime
import secrets  # Changed from random to secrets for secure OTP generation
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
import base64
import io
import os
import numpy as np
from PIL import Image
import cv2
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from .models import Student

# Constants
OTP_MIN = 100000
OTP_MAX = 999999
OTP_EXPIRY_SECONDS = 300  # 5 minutes


def studentRegister(request):
    """
    Handle student registration
    Collects student details, generates OTP, and sends it to student's KIIT email
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        roll = request.POST.get('roll')
        password = request.POST.get('password')
        
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

    return render(request, 'student_registration.html')


@login_required
def renderDashboard(request):
    """
    Render student dashboard
    Requires user to be logged in and have a Student profile
    """
    name = ""
    face_verified = False
    user = request.user
    
    try:
        student = Student.objects.get(user=user)
        name = student.name
        face_verified = student.face_verified

    except Student.DoesNotExist:
        # Fixed bug: Added return statement
        return redirect('login')

    context = {
        'name': name,
        'face_verified': face_verified,
    }

    return render(request, 'student_dashboard.html', context)


# Initialize FaceNet models (load once, reuse)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = None
resnet = None

def get_face_models():
    """Load face recognition models (lazy initialization - models loaded on first use)"""
    global mtcnn, resnet
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
        
        # Save to text file for testing 
        os.makedirs('facial_vectors', exist_ok=True)
        with open(f'facial_vectors/roll_{student.roll}.txt', 'w') as f:
            f.write(f"Roll Number: {student.roll}\n")
            f.write(f"Student Name: {student.name}\n")
            f.write(f"Face Embedding Vector:\n")
            f.write(json.dumps(embedding_list, indent=2))
        
        return JsonResponse({
            'success': True,
            'message': 'Face registered successfully and saved to database',
            'face_verified': True
        })
        
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error processing face: {str(e)}'}, status=500)