"""
Utility functions for facial recognition system.
Includes image processing, similarity computation, and visualization helpers.
"""

import numpy as np
import cv2
from typing import Tuple, Optional


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Compute cosine similarity between two face embeddings.
    
    Cosine similarity measures the cosine of the angle between two vectors.
    Result ranges from -1 (opposite) to 1 (identical).
    For face recognition, higher values indicate more similar faces.
    
    Args:
        embedding1: First face embedding vector (normalized)
        embedding2: Second face embedding vector (normalized)
    
    Returns:
        Cosine similarity score (float between -1 and 1)
    """
    # Normalize embeddings to unit vectors
    embedding1_norm = embedding1 / np.linalg.norm(embedding1)
    embedding2_norm = embedding2 / np.linalg.norm(embedding2)
    
    # Compute dot product (cosine similarity for normalized vectors)
    similarity = np.dot(embedding1_norm, embedding2_norm)
    
    return float(similarity)


def draw_bounding_box(
    frame: np.ndarray,
    bbox: np.ndarray,
    label: str,
    confidence: float,
    color: Tuple[int, int, int],
    thickness: int = 2
) -> np.ndarray:
    """
    Draw bounding box with label and confidence on frame.
    
    Args:
        frame: Input image frame
        bbox: Bounding box coordinates [x1, y1, x2, y2]
        label: Text label (e.g., person name or "Unknown")
        confidence: Confidence score (0-1)
        color: BGR color tuple for box
        thickness: Line thickness for bounding box
    
    Returns:
        Frame with drawn bounding box and label
    """
    # Extract coordinates
    x1, y1, x2, y2 = bbox.astype(int)
    
    # Draw rectangle
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    
    # Prepare label text
    text = f"{label}: {confidence:.2f}"
    
    # Get text size for background rectangle
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    font_thickness = 2
    (text_width, text_height), baseline = cv2.getTextSize(
        text, font, font_scale, font_thickness
    )
    
    # Draw background rectangle for text
    text_x = x1
    text_y = y1 - 10
    if text_y < text_height:
        text_y = y2 + text_height + 10
    
    cv2.rectangle(
        frame,
        (text_x, text_y - text_height - baseline),
        (text_x + text_width, text_y + baseline),
        color,
        -1  # Filled rectangle
    )
    
    # Draw text
    cv2.putText(
        frame,
        text,
        (text_x, text_y - baseline),
        font,
        font_scale,
        (255, 255, 255),  # White text
        font_thickness
    )
    
    return frame


def preprocess_image(image_path: str, target_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
    """
    Load and preprocess image for face detection.
    
    Args:
        image_path: Path to image file
        target_size: Optional target size (width, height) for resizing
    
    Returns:
        Preprocessed image as numpy array (BGR format)
    
    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image cannot be loaded
    """
    # Load image
    image = cv2.imread(image_path)
    
    if image is None:
        raise ValueError(f"Failed to load image from {image_path}")
    
    # Resize if target size specified
    if target_size is not None:
        image = cv2.resize(image, target_size)
    
    return image


def calculate_fps(prev_time: float, current_time: float) -> float:
    """
    Calculate frames per second.
    
    Args:
        prev_time: Previous frame timestamp
        current_time: Current frame timestamp
    
    Returns:
        FPS value
    """
    time_diff = current_time - prev_time
    if time_diff > 0:
        fps = 1.0 / time_diff
    else:
        fps = 0.0
    
    return fps


def put_fps_text(frame: np.ndarray, fps: float) -> np.ndarray:
    """
    Display FPS on frame.
    
    Args:
        frame: Input frame
        fps: FPS value to display
    
    Returns:
        Frame with FPS text
    """
    fps_text = f"FPS: {fps:.1f}"
    cv2.putText(
        frame,
        fps_text,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 255, 0),
        2
    )
    
    return frame


def validate_reference_image(image_path: str) -> bool:
    """
    Validate that reference image exists and can be loaded.
    
    Args:
        image_path: Path to reference image
    
    Returns:
        True if valid, False otherwise
    """
    try:
        image = cv2.imread(image_path)
        return image is not None
    except Exception:
        return False
