# Multi-Camera ReID: Quick Reference Guide

## Architecture at a Glance

```
MULTI-CAMERA REID SYSTEM OVERVIEW

┌─ INPUT LAYER ──────────────────────────────────────────┐
│  Multiple Camera Feeds with Local Track IDs            │
│  (Camera A: Track 1-10, Camera B: Track 1-8, etc)      │
└─────────────────────────┬────────────────────────────────┘
                          ↓
┌─ FEATURE EXTRACTION ────────────────────────────────────┐
│  1. Person Crop → OSNet Model → 256-dim Embedding      │
│  2. Cache embeddings for quick lookup                   │
└─────────────────────────┬────────────────────────────────┘
                          ↓
┌─ MATCHING LAYER ───────────────────────────────────────┐
│  1. Compare embedding with existing identities         │
│  2. Rank candidates by cosine similarity               │
│  3. Apply temporal-spatial constraints                 │
│  4. Return top match + confidence score                │
└─────────────────────────┬────────────────────────────────┘
                          ↓
┌─ IDENTITY GRAPH ───────────────────────────────────────┐
│  In-memory graph: (camera, track) → global_identity   │
│  Supports merge operations when high confidence        │
└─────────────────────────┬────────────────────────────────┘
                          ↓
┌─ OUTPUT ───────────────────────────────────────────────┐
│  Enriched tracks with:                                  │
│  - global_reid_id (e.g., "PERSON_001")                │
│  - reid_confidence (0.0-1.0)                           │
│  - cameras_seen (list of camera IDs)                   │
└────────────────────────────────────────────────────────┘
```

---

## File Structure to Create

```bash
multi_camera_reid_module/
    ├── __init__.py                          # Package init, expose main API
    ├── config.py                            # Config variables and camera topology
    ├── schemas.py                           # Data structures (ReIDEmbedding, GlobalIdentity, etc)
    ├── embedding_extractor.py               # Load OSNet, extract embeddings
    ├── cross_camera_matcher.py              # Compare embeddings, rank matches
    ├── temporal_spatial_validator.py        # Validate travel possibilities
    ├── identity_graph.py                    # In-memory identity tracking
    ├── re_identification_engine.py          # Orchestrator, main API
    ├── requirements.txt                     # pip packages (torch, torchvision, torchreid, etc)
    ├── models/
    │   └── osnet_ain_x3_ms_d_c.pth         # Pre-trained weights (~80MB)
    ├── tests/
    │   ├── __init__.py
    │   ├── test_embedding_extractor.py
    │   ├── test_cross_camera_matcher.py
    │   ├── test_temporal_spatial_validator.py
    │   ├── test_identity_graph.py
    │   └── test_reid_engine.py
    └── README.md                            # Module documentation
```

---

## Key Components & Their Roles

### 1. **ReIDEmbeddingExtractor**
- **Purpose**: Convert person crop → 256-dim vector
- **Input**: np.ndarray BGR image (256x128 typically)
- **Output**: np.ndarray (256,) normalized embedding
- **Performance**: ~10ms per crop on GPU

**Usage:**
```python
from multi_camera_reid_module.embedding_extractor import ReIDEmbeddingExtractor

extractor = ReIDEmbeddingExtractor(model_path="models/osnet_ain_x3_ms_d_c.pth")
person_crop = frame[y:y+h, x:x+w]  # Extract from tracked person
embedding = extractor.extract_embedding(person_crop)  # Returns (256,) array
```

### 2. **CrossCameraMatcher**
- **Purpose**: Find which existing identity matches this new embedding
- **Input**: New embedding + list of candidate embeddings
- **Output**: Ranked list of (candidate_id, similarity_score, confidence)
- **Performance**: <10ms for 100 candidates

**Usage:**
```python
from multi_camera_reid_module.cross_camera_matcher import CrossCameraMatcher

matcher = CrossCameraMatcher(config)
candidates = matcher.find_candidate_matches(
    new_embedding=ReIDEmbedding(...),
    candidate_embeddings=[...],
    top_k=5
)
# Returns: List[CrossCameraMatch]
# candidates[0] is best match with highest confidence
```

### 3. **TemporalSpatialValidator**
- **Purpose**: Ensure matches are physically possible
- **Validates**: Travel time & distance between cameras
- **Input**: Two cameras + timestamps
- **Output**: (is_valid: bool, explanation: dict)

**Usage:**
```python
from multi_camera_reid_module.temporal_spatial_validator import TemporalSpatialValidator

validator = TemporalSpatialValidator(camera_config)
is_valid, explanation = validator.validate_temporal_gap(
    camera_1_id="entrance",
    timestamp_1=datetime(2024, 1, 1, 10, 0, 0),
    camera_2_id="exit",
    timestamp_2=datetime(2024, 1, 1, 10, 0, 45)
)
# Should return: (True, {"travel_time_sec": 45, "max_allowed": 120})
```

### 4. **IdentityGraph**
- **Purpose**: Maintain mapping: (camera, local_track_id) → global_identity_id
- **Operations**: Add appearance, merge identities, lookup, cleanup
- **Stores**: Embedded timestamps, embeddings, camera info

**Usage:**
```python
from multi_camera_reid_module.identity_graph import IdentityGraph

graph = IdentityGraph(config)

# Add new appearance
global_id = graph.add_appearance(embedding, global_id=None)  # Creates new

# Add to existing identity
global_id = graph.add_appearance(embedding, global_id="PERSON_001")  # Appends

# Lookup person
identity = graph.get_identity("PERSON_001")
print(identity.cameras_ids)  # {camera_a, camera_b}
print(identity.get_timeline())  # [(camera_a, t1), (camera_b, t2)]
```

### 5. **MultiCameraReIDEngine** (Main API)
- **Purpose**: Orchestrate all components
- **Main Entry Point**: `process_track()` or `batch_process_tracks()`
- **Returns**: `IdentityMatchResult` with global_id + confidence

**Usage:**
```python
from multi_camera_reid_module.re_identification_engine import MultiCameraReIDEngine

reid_engine = MultiCameraReIDEngine(config, device="cuda")

# For each detected track in each camera:
result = reid_engine.process_track(
    track_id=5,
    camera_id="entrance",
    person_crop=frame[y:y+h, x:x+w],
    bbox=(x, y, w, h),
    timestamp=datetime.now(),
    frame_id=42
)

print(f"Global ID: {result.matched_global_id}")
print(f"Confidence: {result.matched_confidence}")
print(f"Is new: {result.is_new_identity}")
```

---

## Configuration Essentials

### Minimum Configuration (2 cameras)

```python
# config.py

REID_MODEL_PATH = "multi_camera_reid_module/models/osnet_ain_x3_ms_d_c.pth"
REID_EMBEDDING_DIM = 256
REID_SIMILARITY_THRESHOLD = 0.30  # Cosine similarity

MAX_TIME_BETWEEN_CAMERAS = 120  # seconds
MIN_CONFIDENCE_FOR_GLOBAL_ID = 0.65

CAMERA_CONFIG = {
    "camera_a": {
        "id": "camera_a",
        "location": "entrance",
        "adjacent_cameras": ["camera_b"]
    },
    "camera_b": {
        "id": "camera_b",
        "location": "exit",
        "adjacent_cameras": ["camera_a"]
    }
}
```

### Production Configuration (5+ cameras)

```python
# Add: calibrated distances, pathfinding, load balancing
CAMERA_CONFIG = {
    "cam_1": {
        "id": "cam_1",
        "location": "entrance",
        "calibrated_distance_to": {
            "cam_2": 15.0,  # meters
            "cam_3": 40.0
        },
        "adjacent_cameras": ["cam_2", "cam_3"]
    },
    # ... more cameras
}

# Use FAISS for faster matching
USE_FAISS_INDEX = True
FAISS_INDEX_REFRESH_INTERVAL = 300  # seconds
```

---

## Integration Points (What Changes)

### 1. tracking_module/schemas.py
**ADD:**
```python
@dataclass
class TrackedPerson:
    # ... existing fields ...
    global_reid_id: Optional[str] = None
    reid_confidence: Optional[float] = None
    person_crop: Optional[np.ndarray] = None  # For embedding extraction
```

### 2. fusion_module/fuser.py
**ADD:**
```python
@dataclass
class FusionInput:
    # ... existing fields ...
    cross_camera_reid_score: Optional[float] = None
    global_reid_id: Optional[str] = None

# In FusionEngine.fuse():
# Boost total confidence if cross-camera ReID is high (2+ cameras)
```

### 3. output_delivery_module/delivery.py
**ADD:**
```python
@dataclass
class DeliveryRecord:
    # ... existing fields ...
    global_reid_id: Optional[str] = None
    cameras_detected_in: List[str] = field(default_factory=list)
    cross_camera_detection: bool = False
```

### 4. surveillance_backend_pipeline.py
**ADD:**
```python
# In __init__:
self.reid_engine = MultiCameraReIDEngine(config)

# In process() method:
reid_result = self.reid_engine.process_track(...)
track.global_reid_id = reid_result.matched_global_id
track.reid_confidence = reid_result.matched_confidence
```

### 5. surveillance_live_service.py
**CHANGE TO:**
```python
class MultiCameraLiveService:
    def __init__(self, camera_configs: dict):
        self.reid_engine = MultiCameraReIDEngine(config)  # Shared
        self.camera_services = {}
    
    def add_camera(self, camera_id: str, source: str):
        service = SingleCameraService(
            camera_id=camera_id,
            reid_engine=self.reid_engine
        )
```

---

## Database Changes

### Create Tables

```sql
-- Table 1: Global identities
CREATE TABLE global_identities (
    global_id UUID PRIMARY KEY,
    created_at TIMESTAMP,
    confidence_score FLOAT,
    appearance_count INT,
    camera_ids TEXT[]  -- e.g., ["entry", "hallway", "exit"]
);

-- Table 2: Appearance audit trail
CREATE TABLE reid_appearances (
    id UUID PRIMARY KEY,
    global_id UUID REFERENCES global_identities,
    camera_id TEXT,
    local_track_id INT,
    timestamp TIMESTAMP,
    confidence_score FLOAT
);

-- Update existing alerts table
ALTER TABLE alerts ADD COLUMN global_reid_id UUID;
ALTER TABLE alerts ADD COLUMN cross_camera_detection BOOLEAN;
```

---

## Testing Checklist

### Unit Tests (Per Module)

```bash
# Run all tests
pytest multi_camera_reid_module/tests/

# Individual test files
pytest multi_camera_reid_module/tests/test_embedding_extractor.py
pytest multi_camera_reid_module/tests/test_cross_camera_matcher.py
pytest multi_camera_reid_module/tests/test_identity_graph.py
```

### Integration Tests

```python
# Test: Process single track
# Expected: Returns IdentityMatchResult with valid global_id

# Test: Process two cameras sequentially
# Expected: Same person linked when confidence high

# Test: Process incompatible times
# Expected: Returns is_new_identity=True when not physically possible
```

### Performance Benchmarks

- **Embedding extraction**: <15ms per crop
- **Matching**: <10ms for 100 candidates
- **Graph operations**: <5ms
- **Full track processing**: <50ms

---

## Common Scenarios

### Scenario 1: Same Person in Two Cameras

```
Time: 10:00:00 → Camera A detects Track #3
├─ Extract person crop
├─ Generate embedding
├─ Query identity graph (first time, empty)
├─ Create new global ID: "PERSON_001"
│
Time: 10:00:45 → Camera B detects Track #7
├─ Extract person crop
├─ Generate embedding
├─ Compare with "PERSON_001" embedding
├─ Similarity: 0.75 (high match!)
├─ Temporal check: 45 seconds (valid, <120s max)
├─ Spatial check: distance OK
├─ Mark as same person → "PERSON_001"
├─ Update global identity: +1 appearance
│
Result: Unified identity "PERSON_001" seen in 2 cameras
```

### Scenario 2: Different People, Similar Appearance

```
Time: 10:05:00 → Camera C detects Track #2
├─ Extract embedding
├─ Query graph
├─ Find "PERSON_001" is closest match
├─ Similarity: 0.28 (borderline)
├─ BUT temporal conflict: Would require person to travel
│   from Camera B (10:00:45) to Camera C (10:05:00)
│   Distance: 100m, Time: 255 seconds (OK)
│   BUT person just appeared in Camera B!
│   Unlikely to also be in Camera C in same instance
├─ Temporal validator: INVALID (concurrent in 2 places)
│
Result: Create new identity "PERSON_002"
```

### Scenario 3: Long Time Gap (Same Person, Different Cameras)

```
Time: 10:00:00 → Camera A: "PERSON_001"
Time: 10:05:00 → Camera B: Potential match to "PERSON_001"
├─ Similarity: 0.65 (good match)
├─ Temporal gap: 300 seconds
├─ Max allowed: 120 seconds
├─ Status: TEMPORAL INVALID
│
Options:
A. Lower confidence, still link
B. Require higher similarity (e.g., 0.80+)
C. Manual review for long gaps
```

---

## Troubleshooting Guide

| Issue | Cause | Solution |
|-------|-------|----------|
| Low cross-camera match rate | Embedding model weights incorrect | Verify model file checksum |
| High false positive matches | Threshold too low | Increase REID_SIMILARITY_THRESHOLD |
| Memory leak in identity graph | No cleanup running | Call `graph.cleanup_expired_identities()` periodically |
| Slow embedding extraction | Model on CPU | Set device="cuda" and verify CUDA availability |
| Timestamp mismatch | Camera clocks not synced | Implement NTP time sync before deployment |
| Graph merge conflicts | Duplicate matches | Use confidence ordering to resolve conflicts |

---

## Performance Optimization Tips

### Quick Wins

1. **Batch Processing**: Extract 32 embeddings at once instead of 1
   - Speedup: 3-4x

2. **Caching**: Store recent embeddings, reuse if same track appears
   - Speedup: 10-100x for same tracks

3. **FAISS Index**: Use approximate nearest neighbor for 1000+ identities
   - Speedup: 100-1000x for large identity graphs

4. **Lazy Loading**: Only load camera config + identities for nearby cameras
   - Memory savings: 80%+

### Advanced Optimization

```python
# Use FAISS for large-scale matching
import faiss

index = faiss.IndexFlatL2(256)  # L2 distance for embeddings
index.add(embeddings_array)  # Add all embeddings
distances, indices = index.search(query_embedding, k=5)
```

---

## Deployment Steps (Quick)

1. **Create module structure** (1 hour)
2. **Install dependencies** (30 min)
3. **Download model weights** (30 min)
4. **Implement ReID engine** (2-3 days)
5. **Integrate with pipeline** (1-2 days)
6. **Test with mock data** (1 day)
7. **Deploy to staging** (1 day)
8. **Production rollout** (1 day)

**Total: ~1 week of focused development**

---

## Key Metrics to Monitor

```python
class ReIDMetrics:
    # Per camera pair
    successful_matches_per_minute: float
    average_match_confidence: float
    false_positive_rate: float
    
    # Overall
    total_global_identities: int
    avg_cameras_per_identity: float  # Should be > 1.0 for cross-camera
    graph_size_mb: float
    
    # Performance
    avg_embedding_latency_ms: float
    avg_matching_latency_ms: float
```

---

## Next Steps After Implementation

1. **Monitor performance** in staging for 1 week
2. **Collect false positive/negative examples**
3. **Retrain embedding model** with production data (if needed)
4. **Optimize thresholds** based on real-world distribution
5. **Add domain adaptation** if cameras are in new venues
6. **Collect hard examples** for future model improvements

