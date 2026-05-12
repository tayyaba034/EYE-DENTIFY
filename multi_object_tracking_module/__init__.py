"""
__init__.py — Multi-Object Tracking Module Entry Point
Surveillance Intelligence Pipeline — Stage 2: Multi-Object Tracking

Public surface exposed to the pipeline orchestrator:
    from multi_object_tracking_module import MultiObjectTracker, FrameTrackingOutput
"""

from multi_object_tracking_module.tracker import MultiObjectTracker                          # noqa: F401
from multi_object_tracking_module.schemas import FrameTrackingOutput, TrackedPerson          # noqa: F401

__all__ = [
    "MultiObjectTracker",
    "FrameTrackingOutput",
    "TrackedPerson",
]

__version__ = "1.0.0"
__stage__ = 2
__pipeline_role__ = "multi_object_tracking"
