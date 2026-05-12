import os
import numpy as np
import cv2
from insightface.app import FaceAnalysis
from typing import Optional, Tuple, List
import config
from utils import cosine_similarity, preprocess_image


class FaceRecognizer:
    
    def __init__(
        self,
        model_name: str = config.MODEL_NAME,
        detection_threshold: float = config.DETECTION_THRESHOLD,
        recognition_threshold: float = config.RECOGNITION_THRESHOLD
    ):
    
        self.model_name = model_name
        self.detection_threshold = detection_threshold
        self.recognition_threshold = recognition_threshold
        self.reference_embedding = None
        self.reference_name = "Person"
        
        # Initialize InsightFace app
        print(f"Initializing InsightFace with model: {model_name}")
        print("Downloading models if not present (this may take a minute)...")
        
        self.app = FaceAnalysis(
            name=model_name,
            root=config.MODEL_ROOT,
            providers=['CPUExecutionProvider']  # Use CPU (change to CUDAExecutionProvider for GPU)
        )
        
        # Prepare model with specified input size and detection threshold
        self.app.prepare(
            ctx_id=0,
            det_thresh=detection_threshold,
            det_size=config.INPUT_SIZE
        )
        
        print("InsightFace initialized successfully!")
    
    def load_reference_image(self, image_path: str, person_name: str = "Person") -> bool:
        print(f"\nLoading reference image from: {image_path}")
        
        # Check if file exists
        if not os.path.exists(image_path):
            print(f"Error: Reference image not found at {image_path}")
            return False
        
        # Load and preprocess image
        try:
            image = preprocess_image(image_path)
        except Exception as e:
            print(f"Error loading image: {e}")
            return False
        
        # Detect faces in reference image
        faces = self.app.get(image)
        
        if len(faces) == 0:
            print("Error: No face detected in reference image")
            return False
        
        if len(faces) > 1:
            print(f"Warning: Multiple faces detected ({len(faces)}), using the first one")
        
        # Extract embedding from first detected face
        self.reference_embedding = faces[0].embedding
        self.reference_name = person_name
        
        print(f"Reference embedding extracted successfully!")
        print(f"Embedding shape: {self.reference_embedding.shape}")
        print(f"Person name: {self.reference_name}")
        
        return True
    
    def recognize_faces(self, frame: np.ndarray) -> List[Tuple[np.ndarray, str, float]]:
        # Detect faces in frame
        faces = self.app.get(frame)
        
        results = []
        
        for face in faces:
            # Extract bounding box
            bbox = face.bbox  # [x1, y1, x2, y2]
            
            # Extract embedding
            embedding = face.embedding
            
            # Compare with reference embedding
            if self.reference_embedding is not None:
                similarity = cosine_similarity(embedding, self.reference_embedding)
                
                # Determine if face matches reference
                if similarity >= self.recognition_threshold:
                    label = self.reference_name
                    confidence = similarity
                else:
                    label = "Unknown"
                    confidence = similarity
            else:
                label = "Unknown"
                confidence = 0.0
            
            results.append((bbox, label, confidence))
        
        return results
    
    def get_embedding(self, frame: np.ndarray, bbox: Optional[np.ndarray] = None) -> Optional[np.ndarray]:
        faces = self.app.get(frame)
        
        if len(faces) == 0:
            return None
        
        # If bbox specified, find closest face
        if bbox is not None:
            # Find face with closest bounding box
            min_dist = float('inf')
            closest_face = faces[0]
            
            for face in faces:
                dist = np.linalg.norm(face.bbox - bbox)
                if dist < min_dist:
                    min_dist = dist
                    closest_face = face
            
            return closest_face.embedding
        
        # Otherwise return first face
        return faces[0].embedding
    
    def set_recognition_threshold(self, threshold: float):
        if 0.0 <= threshold <= 1.0:
            self.recognition_threshold = threshold
            print(f"Recognition threshold updated to: {threshold}")
        else:
            print("Error: Threshold must be between 0 and 1")
    
    def get_detection_count(self, frame: np.ndarray) -> int:
        faces = self.app.get(frame)
        return len(faces)
