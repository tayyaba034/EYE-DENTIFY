import os
import sys
import numpy as np
import cv2
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.config import (
    FEATURES_DIR,
    PREDICTIONS_DIR,
    MODEL_NAME,
    MODEL_ROOT,
    DETECTION_THRESHOLD,
    INPUT_SIZE,
    RECOGNITION_THRESHOLD,
    USE_EUCLIDEAN,
    EUCLIDEAN_THRESHOLD,
    WEBCAM_INDEX,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    FPS,
    BOX_COLOR_RECOGNIZED,
    BOX_COLOR_UNKNOWN,
    BOX_THICKNESS,
    SKIP_FRAMES,
    LOG_PREDICTIONS,
    LOG_INTERVAL
)
from src.utils.helpers import (
    cosine_similarity,
    euclidean_distance,
    similarity_to_percentage,
    draw_bounding_box_with_percentage,
    calculate_fps,
    put_info_panel,
    save_prediction_log
)
from insightface.app import FaceAnalysis


class InferencePipeline:
    
    def __init__(self):
        """Initialize the inference pipeline."""
        print("=" * 70)
        print("Inference Pipeline - Real-Time Facial Recognition")
        print("=" * 70)
        
        self.reference_embeddings = {}
        self.app = None
        self.cap = None
        self.running = False
        self.frame_count = 0
        self.prev_time = 0
        self.last_log_time = 0
        self.last_faces_count = 0
        self.last_results_frame = None
        
        # Create predictions directory
        os.makedirs(PREDICTIONS_DIR, exist_ok=True)
    
    def load_reference_embeddings(self) -> bool:
        print("\n[1/4] Loading reference embeddings...")
        
        embeddings_file = os.path.join(FEATURES_DIR, 'reference_embeddings.npz')
        
        if not os.path.exists(embeddings_file):
            print(f"\n✗ Reference embeddings not found at: {embeddings_file}")
            print("\nPlease run the feature extraction pipeline first:")
            print("  python src/pipelines/feature_eng_pipeline.py")
            return False
        
        # Load embeddings
        data = np.load(embeddings_file)
        self.reference_embeddings = {name: data[name] for name in data.files}
        
        print(f"✓ Loaded {len(self.reference_embeddings)} reference embedding(s):")
        for name, embedding in self.reference_embeddings.items():
            print(f"  - {name}: shape {embedding.shape}")
        
        return True
    
    def initialize_model(self) -> bool:
        print("\n[2/4] Initializing InsightFace model...")
        
        try:
            self.app = FaceAnalysis(
                name=MODEL_NAME,
                root=MODEL_ROOT,
                providers=['CPUExecutionProvider']
            )
            self.app.prepare(
                ctx_id=0,
                det_thresh=DETECTION_THRESHOLD,
                det_size=INPUT_SIZE
            )
            print("✓ InsightFace model initialized")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize model: {e}")
            return False
    
    def initialize_webcam(self) -> bool:
        print("\n[3/4] Initializing webcam...")
        
        self.cap = cv2.VideoCapture(WEBCAM_INDEX)
        
        if not self.cap.isOpened():
            print(f"✗ Cannot open webcam (index: {WEBCAM_INDEX})")
            return False
        
        # Set webcam properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, FPS)
        
        # Get actual webcam properties
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        
        print(f"✓ Webcam initialized")
        print(f"  - Resolution: {actual_width}x{actual_height}")
        print(f"  - FPS: {actual_fps}")
        
        return True
    
    def compare_with_references(self, embedding: np.ndarray) -> tuple:
        best_match_name = "Unknown"
        best_similarity = -1.0
        
        # Compare with all reference embeddings
        for name, ref_embedding in self.reference_embeddings.items():
            if USE_EUCLIDEAN:
                # Use Euclidean distance (lower is better)
                distance = euclidean_distance(embedding, ref_embedding)
                # Convert distance to similarity-like score for display
                similarity = 1.0 / (1.0 + distance)
                is_match = distance < EUCLIDEAN_THRESHOLD
            else:
                # Use cosine similarity (higher is better)
                similarity = cosine_similarity(embedding, ref_embedding)
                is_match = similarity >= RECOGNITION_THRESHOLD
            
            # Track best match
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_name = name if is_match else "Unknown"
        
        # Determine if this is a match based on threshold
        if USE_EUCLIDEAN:
            distance = euclidean_distance(embedding, self.reference_embeddings[best_match_name])
            final_match = distance < EUCLIDEAN_THRESHOLD
        else:
            final_match = best_similarity >= RECOGNITION_THRESHOLD
        
        return best_match_name, best_similarity, final_match
    
    def process_frame(self, frame: np.ndarray) -> tuple:
        # Resize frame for faster detection (detection is the bottleneck)
        # Use a scaling factor to maintain ASPECT RATIO or fixed size
        detect_scale = 0.5
        small_frame = cv2.resize(frame, (0, 0), fx=detect_scale, fy=detect_scale)
        
        # Detect faces in small frame
        faces = self.app.get(small_frame)
        
        # Process each detected face
        for face in faces:
            # Scale bbox back to original frame size
            face.bbox = face.bbox / detect_scale
            
            # Extract embedding
            embedding = face.embedding
            bbox = face.bbox
            
            # Compare with reference embeddings
            name, similarity, is_match = self.compare_with_references(embedding)
            
            # Choose color based on match
            color = BOX_COLOR_RECOGNIZED if is_match else BOX_COLOR_UNKNOWN
            
            # Draw bounding box with match percentage
            frame = draw_bounding_box_with_percentage(
                frame,
                bbox,
                name,
                similarity,
                is_match,
                color,
                BOX_THICKNESS
            )
            
            # Log prediction if enabled
            if LOG_PREDICTIONS:
                current_time = time.time()
                if current_time - self.last_log_time >= LOG_INTERVAL:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    save_prediction_log(
                        timestamp,
                        name,
                        similarity,
                        is_match,
                        PREDICTIONS_DIR
                    )
                    self.last_log_time = current_time
        
        return frame, len(faces)
    
    def run(self):
        print("\n[4/4] Starting real-time recognition...")
        print("System Ready!")
        print("\nControls:")
        print("  'q' or 'ESC' - Quit application")
        print("  '+' or '='   - Increase recognition threshold")
        print("  '-' or '_'   - Decrease recognition threshold")
        print("  's'          - Save current frame")
        print("  'r'          - Reset threshold to default")
        
        self.running = True
        self.frame_count = 0
        self.prev_time = time.time()
        self.last_log_time = time.time()
        
        # Create predictions.log header if it doesn't exist
        log_file = os.path.join(PREDICTIONS_DIR, "predictions.log")
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write("timestamp,label,cosine_similarity,match_percentage,status\n")
        
        while self.running:
            # Capture frame
            ret, frame = self.cap.read()
            
            if not ret:
                print("\n✗ Failed to capture frame")
                break
            
            # Process frame (skip frames if configured)
            if self.frame_count % (SKIP_FRAMES + 1) == 0:
                frame, self.last_faces_count = self.process_frame(frame)
                self.last_results_frame = frame.copy()
            else:
                # Use the last processed frame's results if possible, 
                # or just show the current raw frame to keep it feeling fast
                # For now, we'll show the annotated frame from the last detection
                # but with the current time/info panel
                if self.last_results_frame is not None:
                    # Optional: We could try to track faces, but that's complex.
                    # Showing the last annotated frame while skipping is common.
                    display_frame = self.last_results_frame.copy()
                else:
                    display_frame = frame.copy()
            
            # Calculate and display FPS
            current_time = time.time()
            fps = calculate_fps(self.prev_time, current_time)
            self.prev_time = current_time
            
            # Add info panel
            display_frame = put_info_panel(display_frame if self.frame_count % (SKIP_FRAMES + 1) != 0 else frame, 
                                          fps, self.last_faces_count, RECOGNITION_THRESHOLD)
            
            # Display frame
            cv2.imshow('Facial Recognition System - Press Q to Quit', display_frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:  # 'q' or ESC
                print("\n\nQuitting application...")
                break
            elif key == ord('+') or key == ord('='):
                # Increase threshold
                import config.config as cfg
                cfg.RECOGNITION_THRESHOLD = min(1.0, cfg.RECOGNITION_THRESHOLD + 0.05)
                print(f"\rThreshold increased to: {cfg.RECOGNITION_THRESHOLD:.2f}", end='')
            elif key == ord('-') or key == ord('_'):
                # Decrease threshold
                import config.config as cfg
                cfg.RECOGNITION_THRESHOLD = max(0.0, cfg.RECOGNITION_THRESHOLD - 0.05)
                print(f"\rThreshold decreased to: {cfg.RECOGNITION_THRESHOLD:.2f}", end='')
            elif key == ord('r'):
                # Reset threshold
                import config.config as cfg
                cfg.RECOGNITION_THRESHOLD = 0.4
                print(f"\rThreshold reset to default: {cfg.RECOGNITION_THRESHOLD:.2f}", end='')
            elif key == ord('s'):
                # Save current frame
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(PREDICTIONS_DIR, f"screenshot_{timestamp}.jpg")
                cv2.imwrite(filename, frame)
                print(f"\nFrame saved: {filename}")
            
            self.frame_count += 1
        
        self.cleanup()
    
    def cleanup(self):
        """Release resources and close windows."""
        print("\n\nCleaning up resources...")
        
        if self.cap is not None:
            self.cap.release()
        
        cv2.destroyAllWindows()
        
        print("✓ Resources released")
        print("\n" + "=" * 70)
        print("Application closed successfully!")
        print("=" * 70)
    
    def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            True if all initialization successful, False otherwise
        """
        if not self.load_reference_embeddings():
            return False
        
        if not self.initialize_model():
            return False
        
        if not self.initialize_webcam():
            return False
        
        return True


def main():
    """Main entry point for inference pipeline."""
    pipeline = InferencePipeline()
    
    # Initialize
    if not pipeline.initialize():
        print("\n" + "=" * 70)
        print("Initialization failed. Please check the errors above.")
        print("=" * 70)
        sys.exit(1)
    
    # Run inference
    try:
        pipeline.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        pipeline.cleanup()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        pipeline.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
