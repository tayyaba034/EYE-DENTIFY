"""
__init__.py — Person Detection Module Entry Point
Surveillance Intelligence Pipeline — Stage 1: Person Detection

Public surface exposed to the pipeline orchestrator:
    from person_detection_module import PersonDetector, FrameDetectionOutput
"""

from person_detection_module.detector import PersonDetector                         # noqa: F401
from person_detection_module.schemas import FrameDetectionOutput, DetectionResult  # noqa: F401

__all__ = [
    "PersonDetector",
    "FrameDetectionOutput",
    "DetectionResult",
]

__version__ = "1.0.0"
__stage__ = 1
__pipeline_role__ = "person_detection"
