import os

# Fix OpenMP runtime conflict
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "01-raw")
PREPROCESSED_DATA_DIR = os.path.join(DATA_DIR, "02-preprocessed")
FEATURES_DIR = os.path.join(DATA_DIR, "03-features")
PREDICTIONS_DIR = os.path.join(DATA_DIR, "04-predictions")

# Reference images directory (users place their images here)
REFERENCE_IMAGE_DIR = RAW_DATA_DIR
EMBEDDINGS_FILE = os.path.join(FEATURES_DIR, "reference_embeddings.npy")

# InsightFace Model Configuration
MODEL_NAME = "buffalo_l"  
MODEL_ROOT = os.path.join(BASE_DIR, ".insightface_models")

# Detection Configuration
DETECTION_THRESHOLD = 0.5  
INPUT_SIZE = (640, 640)    

# Recognition Configuration
RECOGNITION_THRESHOLD = 0.4  

# Alternative: Use Euclidean distance (commented out by default)
USE_EUCLIDEAN = False     
EUCLIDEAN_THRESHOLD = 1.0  # Lower is better for Euclidean distance

# Webcam Configuration
WEBCAM_INDEX = 0           # Default webcam (0 for built-in, 1+ for external)
FRAME_WIDTH = 1280         # Webcam frame width
FRAME_HEIGHT = 720         # Webcam frame height
FPS = 30                   # Target frames per second

# Display Configuration
BOX_COLOR_RECOGNIZED = (0, 255, 0)      # Green for recognized person
BOX_COLOR_UNKNOWN = (0, 0, 255)         # Red for unknown person
BOX_THICKNESS = 3
FONT_SCALE = 0.9
FONT_THICKNESS = 2
TEXT_COLOR = (255, 255, 255)            # White text
TEXT_BG_COLOR = (0, 0, 0)               # Black background for text

# Performance Configuration
SKIP_FRAMES = 2            # Process every N frames (0 = process all frames)
                           # Increase to improve performance on slower systems

# Logging Configuration
LOG_PREDICTIONS = True     # Save predictions to data/04-predictions
LOG_INTERVAL = 30          # Log every N seconds
