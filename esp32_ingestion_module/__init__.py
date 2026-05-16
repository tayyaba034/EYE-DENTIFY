# esp32_ingestion_module — receives JPEG frames from ESP32-CAM
# and exposes them as a drop-in replacement for cv2.VideoCapture
from .frame_store import FrameStore
from .esp32_capture import ESP32FrameCapture

__all__ = ["FrameStore", "ESP32FrameCapture"]
