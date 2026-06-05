from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np

from alert_decision_module import AlertDecisionEngine
from clothing_feature_extraction_module import ClothingFeatureExtractor
from explainability_module import ExplainabilityEngine
from height_estimation_module import HeightEstimator
from multi_attribute_fusion_module import FusionEngine, FusionInput
from output_delivery_module import OutputDeliveryEngine
from temporal_validation_module import TemporalValidator


@dataclass
class BackendPipelineResult:
    frame_id: int
    detections: dict
    tracks: dict
    face_features: List[dict]
    clothing_features: List[dict]
    height_features: List[dict]
    fusion: List[dict]
    temporal: List[dict]
    alerts: List[dict]
    deliveries: List[dict]

    def to_dict(self) -> dict:
        return _make_json_safe(
            {
                "frame_id": self.frame_id,
                "detections": self.detections,
                "tracks": self.tracks,
                "face_features": self.face_features,
                "clothing_features": self.clothing_features,
                "height_features": self.height_features,
                "fusion": self.fusion,
                "temporal": self.temporal,
                "alerts": self.alerts,
                "deliveries": self.deliveries,
            }
        )


def _make_json_safe(value):
    if isinstance(value, dict):
        return {key: _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


class SurveillanceBackendPipeline:
    """
    Backend-only pipeline coordinator.

    Web delivery is intentionally excluded until the frontend skill is ready.
    """

    def __init__(self, face_node, color_model: str = "kmeans") -> None:
        self.face_node = face_node
        self.clothing_node = ClothingFeatureExtractor(color_model=color_model)
        self.height_node = HeightEstimator()
        self.fusion_engine = FusionEngine()
        self.temporal_validator = TemporalValidator()
        self.alert_engine = AlertDecisionEngine()
        self.explainability_engine = ExplainabilityEngine()
        self.output_delivery_engine = OutputDeliveryEngine()

    def process(self, detection_output, tracking_output, frame) -> BackendPipelineResult:
        face_results = self.face_node.process(tracking_output, frame) if self.face_node is not None else []
        clothing_results = [
            item.to_dict() for item in self.clothing_node.process(tracking_output, frame)
        ]
        height_results = [
            item.to_dict() for item in self.height_node.process(tracking_output, frame)
        ]

        face_by_track = {item["track_id"]: item for item in face_results}
        clothing_by_track = {item["track_id"]: item for item in clothing_results}
        height_by_track = {item["track_id"]: item for item in height_results}

        fusion_results: List[dict] = []
        temporal_results: List[dict] = []
        alert_results: List[dict] = []
        delivery_results: List[dict] = []

        for track in tracking_output.confirmed_tracks:
            track_id = track.track_id
            face_score = face_by_track.get(track_id, {}).get("face_score")
            clothing_score = clothing_by_track.get(track_id, {}).get("clothing", {}).get(
                "confidence"
            )
            height_score = height_by_track.get(track_id, {}).get("height", {}).get(
                "confidence"
            )
            fusion = self.fusion_engine.fuse(
                FusionInput(
                    track_id=track_id,
                    face_score=face_score,
                    clothing_score=clothing_score,
                    height_score=height_score,
                )
            )
            fusion_results.append(fusion.to_dict())

            temporal = self.temporal_validator.update(track_id, fusion.final_score)
            temporal_results.append(temporal.to_dict())

            clothing_entry = clothing_by_track.get(track_id, {}).get("clothing", {})
            explanation = self.explainability_engine.build(
                final_score=fusion.final_score,
                face_score=face_score,
                clothing_color=clothing_entry.get("color"),
                clothing_score=clothing_entry.get("confidence"),
                temporal_validated=temporal.validated,
                consecutive_frames=temporal.consecutive_frames,
            )
            alert = self.alert_engine.evaluate(
                track_id=track_id,
                validated=temporal.validated,
                final_score=fusion.final_score,
                contributions=fusion.contribution,
            )
            alert.explanation = explanation
            alert_results.append(alert.to_dict())
            if alert.alert:
                delivery_results.append(
                    self.output_delivery_engine.create_record(
                        track_id=track_id,
                        confidence=alert.confidence,
                        explanation=explanation,
                        frame=frame,
                        bbox=track.bbox,
                    ).to_dict()
                )

        return BackendPipelineResult(
            frame_id=detection_output.frame_id,
            detections=detection_output.to_dict(),
            tracks=tracking_output.to_dict(),
            face_features=face_results,
            clothing_features=clothing_results,
            height_features=height_results,
            fusion=fusion_results,
            temporal=temporal_results,
            alerts=alert_results,
            deliveries=delivery_results,
        )
