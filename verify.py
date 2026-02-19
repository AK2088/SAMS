from flask import Flask, request, jsonify
from flask_cors import CORS
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image
import numpy as np
import cv2
import os
from sklearn.metrics.pairwise import cosine_similarity
import io

app = Flask(__name__)
CORS(app)

# Load FaceNet models (MTCNN detect, ResNet embed)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, thresholds=[0.6, 0.7, 0.7], factor=0.709, device=device)
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

STORED_EMBEDDINGS_DIR = 'stored_faces'
THRESHOLD = 0.6  # Cosine sim > 0.6 = match (tune as needed, 0.4-0.8 typical) [web:29]

# Enroll user (admin call, save embedding)
@app.route('/api/enroll', methods=['POST'])
def enroll():
    data = request.json
    user_id = data['user_id']
    image_b64 = data['image']  # Frontend sends base64 image
    
    img = Image.open(io.BytesIO(base64.b64decode(image_b64.split(',')[1])))
    img_rgb = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGB)
    
    # Extract face & embedding
    face = mtcnn(img_rgb)
    if face is None:
        return jsonify({'error': 'No face detected'}), 400
    
    embedding = resnet(face.unsqueeze(0)).detach().cpu().numpy().flatten()
    np.save(os.path.join(STORED_EMBEDDINGS_DIR, f'{user_id}.npy'), embedding)
    return jsonify({'message': f'Enrolled {user_id}'})

# Verify (your flowchart)
@app.route('/api/face-verify', methods=['POST'])
def face_verify():
    data = request.json
    image_b64 = data['image']  # From React camera capture
    
    # Capture face using camera image
    img = Image.open(io.BytesIO(base64.b64decode(image_b64.split(',')[1])))
    img_rgb = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGB)
    
    # ML extracts embedding (FaceNet)
    face = mtcnn(img_rgb)
    if face is None:
        return jsonify({'match': False, 'error': 'No face detected'})
    
    input_embedding = resnet(face.unsqueeze(0)).detach().cpu().numpy().flatten()
    
    # Compare with stored
    best_match_id = None
    best_sim = -1
    

    for file in os.listdir(STORED_EMBEDDINGS_DIR):
        if file.endswith('.npy'):
            user_id = file[:-4]
            stored_emb = np.load(os.path.join(STORED_EMBEDDINGS_DIR, file))
            sim = cosine_similarity([input_embedding], [stored_emb])[0][0]
            
            if sim > best_sim:
                best_sim = sim
                best_match_id = user_id
    
    # Match threshold?
    is_match = best_sim > THRESHOLD
    return jsonify({
        'match': is_match,
        'user_id': best_match_id,
        'similarity': float(best_sim),
        'threshold': THRESHOLD
    })

if __name__ == '__main__':
    os.makedirs(STORED_EMBEDDINGS_DIR, exist_ok=True)
    app.run(debug=True, port=5000)