"""
face_node.py — Stage 3A: Facial Recognition Node
Surveillance Intelligence Pipeline

Executes facial embedding extraction, quality verification, and similarity
scoring against a known database, without making final identification decisions.
"""

from typing import List, Dict, Any, Optional
import os
import sys

# Workaround for OpenMP Error #15
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import numpy as np
import cv2

# Add project root to path safely
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from insightface.app.face_analysis import FaceAnalysis
except ImportError:
    from insightface.app import FaceAnalysis
from person_detection_module.schemas import FrameDetectionOutput
from multi_object_tracking_module.schemas import FrameTrackingOutput, TrackedPerson

try:
    from facial_recognition_module.config.config import (
        MODEL_NAME,
        MODEL_ROOT,
        FEATURES_DIR,
        DETECTION_THRESHOLD,
    )
except ImportError:
    from config.config import MODEL_NAME, MODEL_ROOT, FEATURES_DIR, DETECTION_THRESHOLD


class FaceExtractorNode:
    """
    Stage 3A: Facial Verification
    
    Responsibilities:
    * Validate face quality (blur, angle, occlusion)
    * Extract embeddings
    * Compare against watchlist/database using Cosine Similarity
    * Cache historical scores per track_id
    * Return similarity signal, NOT identity confirmation.
    """

    def __init__(self):
        # 1. Initialize InsightFace
        self.app = FaceAnalysis(
            name=MODEL_NAME, 
            root=MODEL_ROOT, 
            providers=['CPUExecutionProvider']
        )
        self.app.prepare(ctx_id=0, det_thresh=DETECTION_THRESHOLD)
        
        # 2. Load Database
        self.reference_embeddings = self._load_database()
        
        # 3. Cache Management
        self.embedding_cache: Dict[int, Dict[str, Any]] = {}
        
        # Quality thresholds - loosened for blurry cameras
        self.MIN_BLUR_VARIANCE = 10.0
        self.MAX_YAW = 40.0
        self.MAX_PITCH = 30.0
        self.MIN_DET_SCORE = 0.45

    def _load_database(self) -> Dict[str, np.ndarray]:
        embeddings_file = os.path.join(FEATURES_DIR, 'reference_embeddings.npz')
        if not os.path.exists(embeddings_file):
            return {}
        data = np.load(embeddings_file)
        return {name: data[name] for name in data.files}

    def _cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        dot = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))

    def _check_quality(self, frame: np.ndarray, bbox: List[float], face_obj) -> bool:
        """Evaluate if the face is reliable enough for embedding extraction."""
        
        # A. Occlusion / Detection Confidence Check
        if face_obj.det_score < self.MIN_DET_SCORE:
            return False
            
        # B. Angle Check (pitch, yaw, roll)
        if face_obj.pose is not None:
            pitch, yaw, roll = face_obj.pose
            if abs(pitch) > self.MAX_PITCH or abs(yaw) > self.MAX_YAW:
                return False

        # C. Blur Check (Laplacian Variance)
        x1, y1, x2, y2 = [int(v) for v in bbox]
        # Ensure safely within frame
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
        
        if x2 - x1 < 20 or y2 - y1 < 20: 
            return False # Too small
            
        crop = frame[y1:y2, x1:x2]
        if crop.size > 0:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            variance = cv2.Laplacian(gray, cv2.CV_64F).var()
            if variance < self.MIN_BLUR_VARIANCE:
                return False
                
        return True

    def process(self, tracking_output: FrameTrackingOutput, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Process the frame using tracking bounding boxes to detect faces.
        Returns a list of structured dictionaries for Stage 4 Fusion.
        """
        results = []
        
        for track in tracking_output.confirmed_tracks:
            track_id = track.track_id
            
            # --- CACHING STRATEGY ---
            # If we already have a high-quality embedding for this track_id, skip re-computation
            if track_id in self.embedding_cache:
                cached = self.embedding_cache[track_id]
                results.append(cached)
                continue

            # Extract the tracked person's crop
            x, y, w, h = [int(v) for v in track.bbox]
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(frame.shape[1], x + w), min(frame.shape[0], y + h)
            
            # Default miss result
            result = {
                "track_id": track_id,
                "face_score": 0.0,
                "face_detected": False
            }

            if x2 - x1 < 40 or y2 - y1 < 40:
                results.append(result)
                continue
                
            person_crop = frame[y1:y2, x1:x2]
            
            # Run InsightFace strictly on the cropped person
            faces = self.app.get(person_crop)
            
            if len(faces) > 0:
                # Find the most prominent face in the crop
                best_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
                
                # Verify quality
                if self._check_quality(person_crop, best_face.bbox, best_face):
                    
                    # Calculate absolute face bounding box relative to full frame
                    fx1, fy1, fx2, fy2 = best_face.bbox
                    abs_face_bbox = [int(fx1 + x1), int(fy1 + y1), int(fx2 + x1), int(fy2 + y1)]
                    
                    # Compute max similarity against watchlist
                    max_sim = 0.0
                    for _, ref_emb in self.reference_embeddings.items():
                        sim = self._cosine_similarity(best_face.embedding, ref_emb)
                        if sim > max_sim:
                            max_sim = sim
                            
                    # Build success block
                    result["face_detected"] = True
                    result["face_score"] = float(max_sim)
                    result["face_bbox"] = abs_face_bbox
                    
                    # Store in Cache dynamically
                    self.embedding_cache[track_id] = result
            
            results.append(result)
            
        return results

    def reset(self):
        """Clear cache (called on stream end or scene cut)."""
        self.embedding_cache.clear()
