import numpy as np
import cv2
from typing import Tuple, Optional
import os


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    # Normalize embeddings to unit vectors
    embedding1_norm = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
    embedding2_norm = embedding2 / (np.linalg.norm(embedding2) + 1e-8)
    
    # Compute dot product (cosine similarity for normalized vectors)
    similarity = np.dot(embedding1_norm, embedding2_norm)
    
    # Convert to 0-1 range for better interpretability
    # Original range is -1 to 1, we normalize to 0-100% match
    similarity_percent = (similarity + 1) / 2
    
    return float(similarity)


def euclidean_distance(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    return float(np.linalg.norm(embedding1 - embedding2))


def similarity_to_percentage(similarity: float) -> float:
    # Cosine similarity ranges from -1 to 1
    # We map this to 0-100% for user-friendly display
    percentage = ((similarity + 1) / 2) * 100
    return max(0.0, min(100.0, percentage))


def draw_bounding_box_with_percentage(
    frame: np.ndarray,
    bbox: np.ndarray,
    label: str,
    similarity: float,
    is_match: bool,
    color: Tuple[int, int, int],
    thickness: int = 3
) -> np.ndarray:

    # Extract coordinates
    x1, y1, x2, y2 = bbox.astype(int)
    
    # Draw rectangle
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    
    # Convert similarity to percentage
    percentage = similarity_to_percentage(similarity)
    
    # Prepare label text
    if is_match:
        match_status = "✓ MATCH"
        text = f"{label}: {percentage:.1f}% {match_status}"
    else:
        match_status = "✗ NO MATCH"
        text = f"Unknown: {percentage:.1f}% {match_status}"
    
    # Get text size for background rectangle
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    font_thickness = 2
    (text_width, text_height), baseline = cv2.getTextSize(
        text, font, font_scale, font_thickness
    )
    
    # Draw background rectangle for text
    text_x = x1
    text_y = y1 - 10
    if text_y < text_height:
        text_y = y2 + text_height + 10
    
    # Draw filled rectangle background
    cv2.rectangle(
        frame,
        (text_x, text_y - text_height - baseline - 5),
        (text_x + text_width + 10, text_y + baseline),
        color,
        -1  # Filled rectangle
    )
    
    # Draw text
    cv2.putText(
        frame,
        text,
        (text_x + 5, text_y - baseline - 2),
        font,
        font_scale,
        (255, 255, 255),  # White text
        font_thickness,
        cv2.LINE_AA
    )
    
    # Draw additional info below the box
    info_text = f"Cosine Sim: {similarity:.3f}"
    cv2.putText(
        frame,
        info_text,
        (x1, y2 + 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv2.LINE_AA
    )
    
    return frame


def preprocess_image(image_path: str, target_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Load image
    image = cv2.imread(image_path)
    
    if image is None:
        raise ValueError(f"Failed to load image from {image_path}")
    
    # Resize if target size specified
    if target_size is not None:
        image = cv2.resize(image, target_size)
    
    return image


def calculate_fps(prev_time: float, current_time: float) -> float:
    time_diff = current_time - prev_time
    if time_diff > 0:
        fps = 1.0 / time_diff
    else:
        fps = 0.0
    
    return fps


def put_info_panel(frame: np.ndarray, fps: float, face_count: int, threshold: float) -> np.ndarray:
    height, width = frame.shape[:2]
    
    # Create semi-transparent overlay for info panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (400, 120), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    # Display information
    info_lines = [
        f"FPS: {fps:.1f}",
        f"Faces Detected: {face_count}",
        f"Threshold: {threshold:.2f}",
        f"Match at: {similarity_to_percentage(threshold):.0f}%"
    ]
    
    y_offset = 35
    for line in info_lines:
        cv2.putText(
            frame,
            line,
            (20, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )
        y_offset += 25
    
    return frame


def save_prediction_log(
    timestamp: str,
    label: str,
    similarity: float,
    is_match: bool,
    output_dir: str
) -> None:
   
    log_file = os.path.join(output_dir, "predictions.log")
    
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Write log entry
    with open(log_file, 'a') as f:
        percentage = similarity_to_percentage(similarity)
        status = "MATCH" if is_match else "NO_MATCH"
        f.write(f"{timestamp},{label},{similarity:.4f},{percentage:.2f},{status}\n")


def get_image_files(directory: str) -> list:
    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    image_files = []
    
    if not os.path.exists(directory):
        return image_files
    
    for filename in os.listdir(directory):
        ext = os.path.splitext(filename)[1].lower()
        if ext in valid_extensions:
            image_files.append(os.path.join(directory, filename))
    
    return image_files


def validate_reference_image(image_path: str) -> bool:
    try:
        if not os.path.exists(image_path):
            return False
        image = cv2.imread(image_path)
        return image is not None
    except Exception:
        return False
