# Multi-Camera Re-Identification (Multi-Camera ReID) Implementation Plan

## Executive Summary

This document provides a complete, step-by-step implementation guide to add **Multi-Camera Re-Identification** capability to your surveillance pipeline. This feature enables the system to track and identify the same person across multiple camera feeds, creating a unified identity graph across the entire surveillance zone.

---

## Part 1: Architecture Overview

### 1.1 Current Pipeline (Single-Camera)

```
Camera Feed
   ↓
Detection (YOLOv8) → Tracking (DeepSORT/ByteTrack)
   ↓
Single-Camera Track ID (e.g., Track #42 in Camera A)
   ↓
Feature Extraction (Face, Clothing, Height)
   ↓
Alert Decision & Delivery
```

### 1.2 Proposed Multi-Camera Architecture

```
┌─────────────────────────────────────────────────────────┐
│         MULTI-CAMERA SURVEILLANCE SYSTEM                │
└─────────────────────────────────────────────────────────┘

CAMERA A INPUT          CAMERA B INPUT          CAMERA C INPUT
       ↓                       ↓                       ↓
Detection+Tracking      Detection+Tracking      Detection+Tracking
(Local Track IDs)       (Local Track IDs)       (Local Track IDs)
       ↓                       ↓                       ↓
    Track A-1               Track B-5               Track C-12
    Track A-3               Track B-7               Track C-8
       ↓                       ↓                       ↓
┌─────────────────────────────────────────────────────────┐
│        MULTI-CAMERA REID MODULE (NEW)                    │
│                                                         │
│  • Extract embeddings from each camera track           │
│  • Cross-camera similarity matching                    │
│  • Temporal-spatial validation                         │
│  • Global re-identification                            │
│  • Identity graph construction                         │
└─────────────────────────────────────────────────────────┘
       ↓
Global Unified Identity
Example: PERSON_001 appears as:
  - Track A-1 (Camera A, t=10s)
  - Track B-5 (Camera B, t=15s)
  - Track C-12 (Camera C, t=22s)
       ↓
Multi-Attribute Fusion (Enhanced with Camera Context)
       ↓
Alert Decision (Now with Cross-Camera Confidence)
       ↓
Enriched Alert: "PERSON_001 detected in 3 cameras within 30s"
```

---

## Part 2: New Module Structure

### 2.1 Create New Directory: `multi_camera_reid_module/`

```
multi_camera_reid_module/
├── __init__.py
├── config.py
├── schemas.py
├── embedding_extractor.py
├── re_identification_engine.py
├── temporal_spatial_validator.py
├── identity_graph.py
├── cross_camera_matcher.py
├── tests/
│   ├── __init__.py
│   ├── test_embedding_extractor.py
│   ├── test_reid_engine.py
│   ├── test_identity_graph.py
│   ├── test_temporal_spatial_validator.py
│   └── test_cross_camera_matcher.py
├── models/
│   ├── osnet_ain_x3_ms_d_c.pth  (OSNet weights for Re-ID)
│   └── osnet_ain_ms_m_c.pth     (Alternative lightweight model)
├── requirements.txt
└── README.md
```

### 2.2 Directory Setup Steps

1. Create the directory structure
2. Copy requirements.txt template
3. Initialize module with placeholder classes
4. Set up configuration for multi-camera

---

## Part 3: Detailed Component Implementation

### 3.1 **config.py** - Multi-Camera ReID Configuration

**Key Configurations:**

```python
# Model settings
REID_MODEL_NAME = "osnet_ain_x3_ms_d_c"  # or lightweight variant
REID_EMBEDDING_DIM = 256
REID_MODEL_WEIGHTS_PATH = "models/osnet_ain_x3_ms_d_c.pth"

# Matching thresholds
CROSS_CAMERA_SIMILARITY_THRESHOLD = 0.30  # Cosine similarity
INTRA_CAMERA_SIMILARITY_THRESHOLD = 0.50  # Higher for same camera

# Temporal-Spatial constraints
MAX_TIME_BETWEEN_CAMERAS = 120  # seconds (max time for same person in different cameras)
MIN_TIME_BETWEEN_SAME_CAMERA = 5  # seconds (min time before reappearance in same camera)

# Identity graph settings
GRAPH_CLEANUP_INTERVAL = 300  # seconds
MAX_IDENTITY_HISTORY = 3600  # seconds (1 hour)
MIN_CONFIDENCE_FOR_GLOBAL_ID = 0.65

# Embedding cache
EMBEDDING_CACHE_SIZE = 1000
EMBEDDING_CACHE_TTL = 60  # seconds

# Camera configuration
CAMERA_CONFIG = {
    "camera_a": {
        "id": "camera_a",
        "location": "entrance",
        "calibrated_distance": None,  # meters (for spatial validation)
        "adjacent_cameras": ["camera_b"]  # cameras that can see overlapping areas
    },
    "camera_b": {
        "id": "camera_b",
        "location": "corridor",
        "calibrated_distance": 15.0,
        "adjacent_cameras": ["camera_a", "camera_c"]
    },
    "camera_c": {
        "id": "camera_c",
        "location": "exit",
        "calibrated_distance": 30.0,
        "adjacent_cameras": ["camera_b"]
    },
}
```

### 3.2 **schemas.py** - Data Structures

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np

@dataclass
class ReIDEmbedding:
    """Single person re-identification embedding from one camera."""
    track_id: int
    camera_id: str
    timestamp: datetime
    embedding: np.ndarray  # Shape: (256,) or (512,) depending on model
    confidence: float
    bbox: Tuple[float, float, float, float]  # x, y, w, h
    frame_id: int
    
    def embedding_norm(self) -> float:
        """Return L2 norm of embedding (for normalization)."""
        return np.linalg.norm(self.embedding)


@dataclass
class CrossCameraMatch:
    """Result of cross-camera matching between two embeddings."""
    camera_1_id: str
    camera_2_id: str
    track_1_id: int
    track_2_id: int
    similarity: float
    match_confidence: float
    temporal_valid: bool
    spatial_valid: bool
    match_confidence_breakdown: Dict[str, float] = field(default_factory=dict)
    
    def is_valid_match(self, threshold: float = 0.30) -> bool:
        """Check if match confidence exceeds threshold."""
        return self.match_confidence >= threshold


@dataclass
class GlobalIdentity:
    """Represents a unified identity across multiple cameras."""
    global_id: str  # UUID or "PERSON_XXXXX"
    appearances: List[ReIDEmbedding]  # All detections of this person
    creation_time: datetime
    last_update: datetime
    confidence_score: float
    camera_ids: set  # Which cameras have detected this person
    estimated_height: Optional[float] = None
    clothing_signature: Optional[Dict] = None
    
    def get_timeline(self) -> List[Tuple[str, datetime]]:
        """Return chronological camera appearances."""
        sorted_appearances = sorted(self.appearances, key=lambda x: x.timestamp)
        return [(app.camera_id, app.timestamp) for app in sorted_appearances]
    
    def get_primary_embedding(self) -> np.ndarray:
        """Return most recent embedding."""
        most_recent = max(self.appearances, key=lambda x: x.timestamp)
        return most_recent.embedding


@dataclass
class IdentityMatchResult:
    """Result of identity matching for a new track across cameras."""
    new_track_id: int
    new_camera_id: str
    matched_global_id: Optional[str]
    matched_confidence: float
    candidate_matches: List[CrossCameraMatch]  # Ranked by confidence
    is_new_identity: bool  # True if no good match found
```

### 3.3 **embedding_extractor.py** - Feature Extraction for Re-ID

**Responsibilities:**
- Load pre-trained OSNet (or similar) model
- Extract 256-dimensional embeddings from person crops
- Normalize embeddings
- Cache embeddings for efficiency
- Handle model loading and GPU management

**Key Methods:**
```python
class ReIDEmbeddingExtractor:
    def __init__(self, model_path: str, device: str = "cuda"):
        """Initialize with pre-trained Re-ID model."""
        
    def extract_embedding(self, person_crop: np.ndarray) -> np.ndarray:
        """Extract normalized embedding from person crop."""
        
    def extract_batch_embeddings(self, person_crops: List[np.ndarray]) -> List[np.ndarray]:
        """Extract embeddings for multiple person crops (batch)."""
        
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
```

### 3.4 **cross_camera_matcher.py** - Cross-Camera Similarity Matching

**Responsibilities:**
- Compare embeddings across cameras
- Rank candidate matches
- Score each potential match
- Return ranked list of candidates

**Key Methods:**
```python
class CrossCameraMatcher:
    def __init__(self, config: dict):
        """Initialize with camera configuration."""
        
    def find_candidate_matches(
        self, 
        new_embedding: ReIDEmbedding,
        candidate_embeddings: List[ReIDEmbedding],
        top_k: int = 5
    ) -> List[CrossCameraMatch]:
        """Find top-k candidate matches for a new embedding."""
        
    def score_match(
        self,
        embedding1: ReIDEmbedding,
        embedding2: ReIDEmbedding
    ) -> Tuple[float, Dict[str, float]]:
        """Score a potential match with breakdown of components."""
        # Components:
        # - embedding_similarity (base cosine)
        # - temporal_plausibility
        # - spatial_plausibility
        # - clothing_consistency (if available)
        # - height_consistency (if available)
```

### 3.5 **temporal_spatial_validator.py** - Constraint Validation

**Responsibilities:**
- Validate temporal constraints (travel time between cameras)
- Validate spatial constraints (walking distance)
- Check camera adjacency
- Prevent impossible matches

**Key Methods:**
```python
class TemporalSpatialValidator:
    def __init__(self, config: dict):
        """Initialize with camera topology and constraints."""
        
    def validate_temporal_gap(
        self,
        camera_1_id: str,
        timestamp_1: datetime,
        camera_2_id: str,
        timestamp_2: datetime
    ) -> Tuple[bool, Dict]:
        """
        Validate if travel time between cameras is physically possible.
        Returns: (is_valid, explanation_dict)
        """
        
    def validate_spatial_distance(
        self,
        camera_1_id: str,
        camera_2_id: str,
        travel_time_sec: float,
        assumed_speed_mps: float = 1.5  # meters per second (walking)
    ) -> Tuple[bool, Dict]:
        """
        Validate spatial distance against estimated walking speed.
        """
        
    def are_cameras_adjacent(self, camera_1_id: str, camera_2_id: str) -> bool:
        """Check if two cameras have overlapping or adjacent coverage."""
```

### 3.6 **identity_graph.py** - Identity Graph Management

**Responsibilities:**
- Maintain mapping of global identities to local track IDs
- Manage re-identification clusters
- Update identity graph as new matches discovered
- Garbage collection (remove old identities)

**Key Methods:**
```python
class IdentityGraph:
    def __init__(self, config: dict):
        """Initialize empty identity graph."""
        
    def add_appearance(
        self,
        embedding: ReIDEmbedding,
        global_id: Optional[str] = None
    ) -> str:
        """
        Add a new appearance to graph.
        If global_id is provided, append to existing identity.
        Otherwise, create new identity.
        Returns: assigned global_id
        """
        
    def merge_identities(self, global_id_1: str, global_id_2: str) -> str:
        """
        Merge two identities (called when match confidence is high).
        Returns: unified global_id
        """
        
    def get_identity(self, global_id: str) -> Optional[GlobalIdentity]:
        """Retrieve full identity record."""
        
    def lookup_local_track(
        self,
        track_id: int,
        camera_id: str
    ) -> Optional[str]:
        """
        Lookup: (track_id, camera_id) -> global_id
        Returns global identity if exists.
        """
        
    def cleanup_expired_identities(self, max_age_sec: int):
        """Remove identities older than max_age_sec."""
        
    def get_identity_timeline(self, global_id: str) -> List[Tuple[str, datetime]]:
        """Get chronological appearance timeline across cameras."""
```

### 3.7 **re_identification_engine.py** - Main ReID Orchestrator

**Responsibilities:**
- Orchestrate multi-camera re-identification
- Integrate all sub-components
- Manage embedding extraction pipeline
- Match new detections to existing identities
- Update identity graph

**Key Methods:**
```python
class MultiCameraReIDEngine:
    def __init__(self, config: dict, device: str = "cuda"):
        """Initialize with configuration."""
        self.extractor = ReIDEmbeddingExtractor(config["reid_model_path"], device)
        self.matcher = CrossCameraMatcher(config)
        self.validator = TemporalSpatialValidator(config)
        self.identity_graph = IdentityGraph(config)
        
    def process_track(
        self,
        track_id: int,
        camera_id: str,
        person_crop: np.ndarray,
        bbox: Tuple,
        timestamp: datetime,
        frame_id: int
    ) -> IdentityMatchResult:
        """
        Process a single track detection across cameras.
        Flow:
        1. Extract embedding
        2. Query identity graph for similar identities
        3. Find candidate matches from other cameras
        4. Rank candidates with temporal-spatial validation
        5. Update identity graph
        6. Return match result
        """
        
    def batch_process_tracks(
        self,
        camera_outputs: Dict[str, List[dict]]
    ) -> Dict[str, IdentityMatchResult]:
        """
        Process outputs from multiple cameras in one batch.
        camera_outputs format:
        {
            "camera_a": [
                {
                    "track_id": 1,
                    "person_crop": np.ndarray,
                    "bbox": (x, y, w, h),
                    "timestamp": datetime,
                    "frame_id": 42
                },
                ...
            ],
            "camera_b": [...],
        }
        """
        
    def get_cross_camera_statistics(self) -> dict:
        """Return statistics about cross-camera matches."""
        # Number of global identities
        # Number of cross-camera appearances
        # Most commonly matched pairs
        # etc.
```

---

## Part 4: Changes to Existing Modules

### 4.1 **multi_object_tracking_module/** - Minimal Changes

**File: `multi_object_tracking_module/schemas.py`**

ADD new fields to `TrackedPerson`:
```python
@dataclass
class TrackedPerson:
    track_id: int
    bbox: Tuple[float, float, float, float]
    confidence: float
    
    # NEW FIELDS:
    global_reid_id: Optional[str] = None  # Maps to multi-camera identity
    reid_confidence: Optional[float] = None  # Confidence of cross-camera match
    person_crop: Optional[np.ndarray] = None  # Crop for embedding extraction
```

**Rationale:** No breaking changes. Only optional fields added for optional ReID integration.

### 4.2 **multi_attribute_fusion_module/** - Enhanced Fusion

**File: `multi_attribute_fusion_module/fuser.py`**

ADD new fusion input for cross-camera signal:
```python
@dataclass
class FusionInput:
    track_id: int
    face_score: Optional[float] = None
    clothing_score: Optional[float] = None
    temporal_score: Optional[float] = None
    height_score: Optional[float] = None
    
    # NEW FIELD:
    cross_camera_reid_score: Optional[float] = None  # ReID confidence from multi-camera
    global_reid_id: Optional[str] = None  # Global identity
```

**Updated `FusionEngine.fuse()` method:**
```python
def fuse(self, item: FusionInput) -> FusionResult:
    # Existing scores...
    
    # NEW: Add cross-camera ReID signal
    cross_reid = self._clamp(item.cross_camera_reid_score)
    
    # Boost confidence if cross-camera ReID is high
    if cross_reid is not None and cross_reid >= 0.80:
        # When person appears in 2+ cameras with high confidence,
        # increase overall confidence by 10%
        confidence_boost = 0.10
    
    contributions = {
        # ...existing...
        "cross_camera_reid": cross_reid_weight * (cross_reid or 0.0)
    }
```

### 4.3 **output_delivery_module/** - Enhanced Alerts

**File: `output_delivery_module/delivery.py`**

ADD new fields to `DeliveryRecord`:
```python
@dataclass
class DeliveryRecord:
    track_id: int
    timestamp: str
    confidence: float
    explanation: str
    snapshot: Optional[str]
    
    # NEW FIELDS:
    global_reid_id: Optional[str] = None
    cameras_detected_in: List[str] = field(default_factory=list)
    cross_camera_detection: bool = False
    reid_timeline: Optional[List[dict]] = None  # Timeline across cameras
```

**Enhanced explanation generation:**
```python
def format_explanation_with_reid(self, record: DeliveryRecord) -> str:
    base_explanation = self.existing_explanation_logic(record)
    
    if record.cross_camera_detection and record.reid_timeline:
        camera_timeline = " → ".join(
            f"{cam}@{ts}" for cam, ts in record.reid_timeline
        )
        reid_context = f"\nCross-camera identity: Tracked across {camera_timeline}"
        return base_explanation + reid_context
    
    return base_explanation
```

### 4.4 **surveillance_backend_pipeline.py** - Integration Point

**File: `surveillance_backend_pipeline.py`**

ADD ReID engine initialization:
```python
class SurveillanceBackendPipeline:
    def __init__(self, face_node, reid_engine=None):
        self.face_node = face_node
        self.clothing_node = ClothingFeatureExtractor()
        self.height_node = HeightEstimator()
        self.fusion_engine = FusionEngine()
        self.temporal_validator = TemporalValidator()
        self.alert_engine = AlertDecisionEngine()
        self.explainability_engine = ExplainabilityEngine()
        self.output_delivery_engine = OutputDeliveryEngine()
        
        # NEW: Multi-camera ReID
        self.reid_engine = reid_engine
```

**ADD ReID processing in pipeline:**
```python
def process(self, detection_output, tracking_output, frame, camera_id=None):
    # ... existing processing ...
    
    # NEW: Cross-camera re-identification
    reid_results = []
    if self.reid_engine and camera_id:
        for track in tracking_output.confirmed_tracks:
            # Extract person crop
            person_crop = self._extract_crop(frame, track.bbox)
            
            # Process through ReID engine
            reid_result = self.reid_engine.process_track(
                track_id=track.track_id,
                camera_id=camera_id,
                person_crop=person_crop,
                bbox=track.bbox,
                timestamp=datetime.now(),
                frame_id=detection_output.frame_id
            )
            reid_results.append(reid_result)
            
            # Update track with global ID
            track.global_reid_id = reid_result.matched_global_id
            track.reid_confidence = reid_result.matched_confidence
    
    # Pass ReID info to fusion
    fusion_inputs = [
        FusionInput(
            track_id=track.track_id,
            # ... existing scores ...
            cross_camera_reid_score=track.reid_confidence,
            global_reid_id=track.global_reid_id
        )
        for track in tracking_output.confirmed_tracks
    ]
    # ... continue with fusion ...
```

### 4.5 **surveillance_live_service.py** - Multi-Camera Support

**File: `surveillance_live_service.py`**

MODIFY to support multiple cameras:
```python
class MultiCameraLiveService:
    def __init__(self, camera_config: dict):
        self.camera_config = camera_config
        self.camera_threads = {}
        self.reid_engine = MultiCameraReIDEngine(config)  # NEW
        
    def add_camera(self, camera_id: str, source: str, backend: str):
        """Add a new camera to the service."""
        camera_service = SingleCameraService(
            camera_id=camera_id,
            source=source,
            backend=backend,
            reid_engine=self.reid_engine  # Share ReID engine
        )
        self.camera_threads[camera_id] = camera_service
        camera_service.start()
        
    def process_frame(self, camera_id: str, detection_output, tracking_output, frame):
        """Process frame with multi-camera context."""
        result = self.backend_pipeline.process(
            detection_output,
            tracking_output,
            frame,
            camera_id=camera_id  # NEW: pass camera_id
        )
        return result
```

---

## Part 5: Database Schema Changes

### 5.1 Supabase Table: `global_identities`

```sql
CREATE TABLE global_identities (
    global_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    appearance_count INTEGER DEFAULT 1,
    camera_ids TEXT[] DEFAULT '{}',  -- Array of camera IDs
    estimated_height_cm FLOAT,
    clothing_signature JSONB,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Index for fast lookup
CREATE INDEX idx_global_identities_last_updated ON global_identities(last_updated DESC);
```

### 5.2 Supabase Table: `reid_appearances` (audit trail)

```sql
CREATE TABLE reid_appearances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    global_id UUID NOT NULL REFERENCES global_identities(global_id),
    camera_id TEXT NOT NULL,
    local_track_id INTEGER,
    timestamp TIMESTAMP NOT NULL,
    confidence_score FLOAT,
    embedding BYTEA,  -- Store compressed embedding
    bbox_x FLOAT,
    bbox_y FLOAT,
    bbox_w FLOAT,
    bbox_h FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_reid_appearances_global_id ON reid_appearances(global_id);
CREATE INDEX idx_reid_appearances_camera_timestamp ON reid_appearances(camera_id, timestamp DESC);
```

### 5.3 Update existing `alerts` table

```sql
-- Add new columns to alerts table
ALTER TABLE alerts ADD COLUMN global_reid_id UUID REFERENCES global_identities(global_id);
ALTER TABLE alerts ADD COLUMN cross_camera_detection BOOLEAN DEFAULT FALSE;
ALTER TABLE alerts ADD COLUMN reid_cameras TEXT[] DEFAULT '{}';

-- Create index
CREATE INDEX idx_alerts_global_reid_id ON alerts(global_reid_id);
```

---

## Part 6: Configuration Files

### 6.1 Create `.env` variables

```bash
# Multi-Camera ReID Configuration
REID_MODEL_WEIGHTS_PATH=multi_camera_reid_module/models/osnet_ain_x3_ms_d_c.pth
REID_EMBEDDING_DIM=256
REID_SIMILARITY_THRESHOLD=0.30
REID_MAX_TIME_BETWEEN_CAMERAS=120
REID_MIN_CONFIDENCE_FOR_GLOBAL_ID=0.65

# Camera Configuration (JSON format or separate env vars)
CAMERA_CONFIGURATION='{
  "camera_entrance": {
    "id": "camera_entrance",
    "location": "main_entrance",
    "adjacent_cameras": ["camera_corridor"]
  },
  "camera_corridor": {
    "id": "camera_corridor",
    "location": "hallway",
    "adjacent_cameras": ["camera_entrance", "camera_exit"]
  },
  "camera_exit": {
    "id": "camera_exit",
    "location": "side_exit",
    "adjacent_cameras": ["camera_corridor"]
  }
}'
```

### 6.2 Create `multi_camera_reid_module/requirements.txt`

```
torch>=2.0.0,<3.0.0
torchvision>=0.15.0
torchreid>=1.4.0  # Or implement custom Re-ID model
numpy>=1.21.0
opencv-python>=4.5.0
scikit-learn>=1.0.0
scipy>=1.7.0
Pillow>=9.0.0
```

---

## Part 7: Step-by-Step Implementation Guide

### Phase 1: Setup (Week 1)

**Step 1.1: Create Module Structure**
- [ ] Create `multi_camera_reid_module/` directory
- [ ] Create all subdirectories and `__init__.py` files
- [ ] Create `config.py` with configuration template
- [ ] Create `requirements.txt`

**Step 1.2: Data Structures**
- [ ] Implement `schemas.py` with all dataclasses
- [ ] Add type hints and validation
- [ ] Create unit tests for schemas

**Step 1.3: Download Re-ID Model**
- [ ] Download OSNet pre-trained weights
  - Link: https://github.com/KaiyangZhou/deep-person-reid
  - File: `osnet_ain_x3_ms_d_c.pth`
- [ ] Place in `multi_camera_reid_module/models/`
- [ ] Verify file integrity (checksum)

**Step 1.4: Install Dependencies**
- [ ] Run `pip install -r multi_camera_reid_module/requirements.txt`
- [ ] Verify imports work
- [ ] Test PyTorch GPU availability

### Phase 2: Core ReID Engine (Week 2)

**Step 2.1: Embedding Extractor**
- [ ] Implement `embedding_extractor.py`
  - Load OSNet model
  - Forward pass for single crops
  - Batch processing
  - Caching mechanism
- [ ] Unit tests for embedding extraction
- [ ] Test with sample person crops
- [ ] Benchmark: ~10ms per 256x128 crop on GPU

**Step 2.2: Cross-Camera Matcher**
- [ ] Implement `cross_camera_matcher.py`
  - Cosine similarity computation
  - Candidate ranking
  - Score breakdown
- [ ] Unit tests for matching
- [ ] Test with mock embeddings
- [ ] Benchmark: <5ms for 100 candidates

**Step 2.3: Temporal-Spatial Validator**
- [ ] Implement `temporal_spatial_validator.py`
  - Travel time validation
  - Spatial distance validation
  - Camera adjacency lookup
- [ ] Unit tests for validation
- [ ] Test with various camera configurations

**Step 2.4: Identity Graph**
- [ ] Implement `identity_graph.py`
  - In-memory graph structure (initially)
  - Add/merge operations
  - Lookup operations
  - Cleanup/expiration
- [ ] Unit tests for graph operations
- [ ] Test with 1000+ identities

### Phase 3: Main Engine (Week 3)

**Step 3.1: ReID Engine Integration**
- [ ] Implement `re_identification_engine.py`
  - Integrate all sub-components
  - Orchestration logic
  - Batch processing
- [ ] Unit tests for engine
- [ ] Integration tests with mock data

**Step 3.2: Testing with Mock Data**
- [ ] Create synthetic multi-camera dataset
  - 3-5 mock cameras
  - 10-20 synthetic people
  - Temporal sequences
- [ ] Test end-to-end ReID matching
- [ ] Verify cross-camera linking

### Phase 4: Pipeline Integration (Week 4)

**Step 4.1: Update Tracking Module**
- [ ] Add `global_reid_id` field to `TrackedPerson`
- [ ] Update `schemas.py`
- [ ] Ensure backward compatibility
- [ ] Test existing tracking still works

**Step 4.2: Update Fusion Module**
- [ ] Add ReID score to `FusionInput`
- [ ] Implement ReID signal in fusion logic
- [ ] Update fusion weights (optional)
- [ ] Test fusion with new signal

**Step 4.3: Update Output Delivery**
- [ ] Add ReID fields to `DeliveryRecord`
- [ ] Enhance explanation generation
- [ ] Update database insertion
- [ ] Test alert generation

**Step 4.4: Update Backend Pipeline**
- [ ] Initialize ReID engine in `SurveillanceBackendPipeline`
- [ ] Add ReID processing step
- [ ] Pass camera_id through pipeline
- [ ] Test pipeline with single camera first

### Phase 5: Multi-Camera Support (Week 5)

**Step 5.1: Create Multi-Camera Service**
- [ ] Implement `MultiCameraLiveService`
- [ ] Support hot-adding cameras
- [ ] Share ReID engine across cameras
- [ ] Test with 2-3 cameras

**Step 5.2: Database Setup**
- [ ] Create Supabase tables
- [ ] Set up migrations
- [ ] Create indexes
- [ ] Test data insertion

**Step 5.3: End-to-End Testing**
- [ ] Test with multi-camera feed
- [ ] Verify cross-camera linking
- [ ] Check alert generation
- [ ] Monitor performance metrics

### Phase 6: Optimization & Deployment (Week 6)

**Step 6.1: Performance Optimization**
- [ ] Profile embedding extraction
- [ ] Optimize matching algorithm (use FAISS?)
- [ ] Batch processing optimization
- [ ] Cache optimization

**Step 6.2: Error Handling & Robustness**
- [ ] Add comprehensive error handling
- [ ] Implement circuit breakers
- [ ] Add fallback mechanisms
- [ ] Test edge cases

**Step 6.3: Documentation & Testing**
- [ ] Write module documentation
- [ ] Create integration guide
- [ ] Write deployment guide
- [ ] Create troubleshooting guide

---

## Part 8: Testing Strategy

### 8.1 Unit Tests

**`test_embedding_extractor.py`**
- Test model loading
- Test single embedding extraction
- Test batch processing
- Test embedding normalization
- Benchmark performance
- Test GPU/CPU mode switching

**`test_cross_camera_matcher.py`**
- Test similarity computation
- Test candidate ranking
- Test score breakdown
- Test edge cases (empty lists, single candidate)

**`test_temporal_spatial_validator.py`**
- Test temporal gap validation with various times
- Test spatial distance computation
- Test camera adjacency
- Test edge cases (0 time gap, impossible distances)

**`test_identity_graph.py`**
- Test identity creation
- Test appearance addition
- Test graph merging
- Test lookup operations
- Test cleanup/expiration
- Test with concurrent operations

### 8.2 Integration Tests

**`test_reid_engine.py`**
- Test complete track processing
- Test batch processing
- Test with real-looking data
- Test error handling

**`test_pipeline_integration.py`**
- Test pipeline with ReID enabled
- Test multi-camera processing
- Test fusion with ReID scores
- Test alert generation

### 8.3 System Tests

**Multi-Camera Scenario Testing**
- Setup 3+ cameras in test environment
- Create scenarios:
  - Same person visible in 2 cameras
  - Same person with 30s gap between cameras
  - Different people with similar appearance
  - Rapid transitions between cameras
  - No transition (incompatible time/space)

**Performance Testing**
- Benchmarks:
  - Embedding extraction: <15ms per crop
  - Matching 100 candidates: <10ms
  - Graph lookup: <5ms
  - Full track processing: <50ms

### 8.4 Regression Testing

- Ensure existing pipeline functionality unchanged
- Run existing test suite
- Verify alert accuracy metrics

---

## Part 9: Performance Optimization Tips

### 9.1 Embedding Caching

```python
# Cache extracted embeddings with TTL
# Format: (camera_id, track_id, frame_id) -> embedding
# Reuse when same person reappears quickly
```

### 9.2 Candidate Matching Acceleration

```python
# Use FAISS (Facebook AI Similarity Search) for fast matching
# Create index of all embeddings
# Query top-k candidates in <1ms for 10k embeddings
pip install faiss-cpu  # or faiss-gpu
```

### 9.3 Batch Processing

```python
# Process embeddings in batches
# Batch size 32-64 for optimal GPU utilization
# Reduces per-embedding overhead
```

### 9.4 Lazy Loading

```python
# Don't load all identities upfront
# Query by time window or camera
# Keep only recent identities in memory
```

---

## Part 10: Known Challenges & Mitigation

| Challenge | Description | Mitigation |
|-----------|-------------|-----------|
| **Lighting Variations** | Different cameras have different lighting | Use lighting-invariant embeddings, augment training data |
| **Pose Variations** | Person appears in different poses | Ensure Re-ID model trained on diverse poses |
| **Occlusion** | Person partially occluded in one camera | Require higher confidence threshold when occluded |
| **Similar Appearance** | Different people look similar | Use height + clothing + temporal constraints |
| **Slow Movement** | Person takes long time between cameras | Relax temporal constraint for long distances |
| **Fast Movement** | Person moves too fast between cameras | Flag as anomalous, manual review |
| **Camera Drift** | Camera moves or rotates | Periodic recalibration needed |
| **Model Drift** | Person changes appearance (clothing) | Use multiple features, update models periodically |

---

## Part 11: Configuration Examples

### 11.1 Two-Camera Configuration

```python
CAMERA_CONFIG = {
    "entrance": {
        "id": "entrance",
        "location": "building_entrance",
        "adjacent_cameras": ["corridor"],
        "calibrated_distance": 20.0  # 20 meters to next camera
    },
    "corridor": {
        "id": "corridor",
        "location": "hallway",
        "adjacent_cameras": ["entrance", "exit"],
        "calibrated_distance_to_entrance": 20.0,
        "calibrated_distance_to_exit": 30.0
    },
    "exit": {
        "id": "exit",
        "location": "building_exit",
        "adjacent_cameras": ["corridor"],
        "calibrated_distance": 30.0
    }
}

# Travel times:
# entrance -> corridor: 20m / 1.5 m/s = ~13 seconds
# corridor -> exit: 30m / 1.5 m/s = ~20 seconds
# entrance -> exit: 50m / 1.5 m/s = ~33 seconds
```

### 11.2 Large Campus Configuration

```python
CAMERA_CONFIG = {
    "gate_1": {"id": "gate_1", "adjacent_cameras": ["zone_a"]},
    "zone_a": {"id": "zone_a", "adjacent_cameras": ["gate_1", "zone_b"]},
    "zone_b": {"id": "zone_b", "adjacent_cameras": ["zone_a", "gate_2"]},
    "gate_2": {"id": "gate_2", "adjacent_cameras": ["zone_b"]},
}

# With many cameras, use graph-based approach for pathfinding
# Find fastest path from camera A to camera B
```

---

## Part 12: Monitoring & Metrics

### 12.1 Key Metrics to Track

```python
class MultiCameraReIDMetrics:
    # Matching metrics
    cross_camera_matches_per_second
    average_match_confidence
    false_positive_rate
    false_negative_rate
    
    # Performance metrics
    embedding_extraction_latency_ms
    matching_latency_ms
    total_reid_latency_ms
    
    # Graph metrics
    total_global_identities
    average_appearances_per_identity
    identities_per_camera
    cross_camera_percentage  # % of identities in 2+ cameras
```

### 12.2 Dashboard Signals

- Real-time number of tracked people per camera
- Cross-camera linking success rate
- Average confidence scores
- Performance bottlenecks
- Error rates

---

## Part 13: Deployment Checklist

- [ ] All tests passing (unit, integration, system)
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] Configuration for production environment
- [ ] Database migrations applied
- [ ] Model weights validated
- [ ] Error handling tested
- [ ] Monitoring setup
- [ ] Rollback plan documented
- [ ] Team trained on new features
- [ ] Staging environment validation
- [ ] Production gradual rollout plan

---

## Part 14: Future Enhancements

1. **Graph Database Integration**: Use Neo4j for rich identity relationships
2. **Temporal Graph Networks**: Deep learning for trajectory prediction
3. **Multi-Modal Fusion**: Combine appearance + gait + pose
4. **Federated Learning**: Train models without centralizing data
5. **Real-Time Alerts**: Notify when person appears in distant cameras
6. **Anomaly Detection**: Detect unusual movement patterns
7. **Privacy-Preserving Re-ID**: Encrypted embeddings
8. **Mobile Re-ID**: Optimize for edge devices
9. **Domain Adaptation**: Handle distribution shift across venues
10. **Active Learning**: Collect hard examples for model improvement

---

## Summary

This implementation plan provides a complete roadmap to integrate Multi-Camera Re-Identification into your surveillance pipeline. The approach is:

- **Modular**: Separate ReID module doesn't break existing code
- **Incremental**: Can integrate gradually
- **Scalable**: Handles 2-50+ cameras
- **Testable**: Comprehensive testing strategy
- **Performant**: Optimized for real-time processing
- **Maintainable**: Clear architecture and documentation

**Estimated Timeline**: 6 weeks for full implementation and deployment.

**Resource Requirements**:
- 1-2 Senior ML Engineers
- GPU hardware (NVIDIA recommended)
- ~40GB storage for models and cache
- Supabase/PostgreSQL for identity graph

---

## Quick Reference: File Changes Summary

| File | Action | Complexity |
|------|--------|-----------|
| `multi_camera_reid_module/*` | CREATE NEW | High |
| `multi_object_tracking_module/schemas.py` | ADD fields | Low |
| `multi_attribute_fusion_module/fuser.py` | UPDATE logic | Medium |
| `output_delivery_module/delivery.py` | ADD fields | Low |
| `surveillance_backend_pipeline.py` | INTEGRATE | Medium |
| `surveillance_live_service.py` | ENHANCE | High |
| Database schema | EXTEND | Low |
| `.env` configuration | EXPAND | Low |

**Total Lines of Code**: ~2000-2500 lines (across all files)

