# EYE-DENTIFY
A smart AI based survelliance project with client side flutter application as well as the admin side dashboard reading with a through AI webcam live footage pipeline to detect a particular individual based on the input from the user and supabase database.



# Surveillance Pipeline

## High-Level Flow

```text
Camera Feed
   ↓
1. Perception (YOLOv8s Person Detection)
   ↓
2. Memory & Continuity (DeepSORT Tracking)
   ↓
3. Feature Extraction
   ├── Face Verification (InsightFace)
   ├── Clothing Features
   └── Optional Height Estimation
   ↓
4. Fusion (Combine Signals)
   ↓
5. Temporal Validation (Across Frames)
   ↓
6. Alert Decision
   ↓
7. Explainability + Output Delivery
   ↓
Web Dashboard + Database Alerts
```

## 1. Perception (Detection)

Your webcam captures a frame and hands it to the YOLOv8s neural network.

- YOLO scans the image and identifies where humans are located.
- It draws raw bounding boxes around detected people.
- It ignores tables, chairs, cups, and other objects because the pipeline is restricted to the `person` class.
- The output of this stage is only location plus confidence.

Example output:

```json
{
  "frame_id": 42,
  "detections": [
    {
      "bbox": [120.5, 80.2, 95.0, 210.3],
      "confidence": 0.8741
    }
  ]
}
```

## 2. Memory & Continuity (Tracking)

YOLO has no memory. It detects frame by frame and forgets everything when the next frame begins.

This is where DeepSORT takes over.

- DeepSORT receives the raw person boxes from YOLO.
- It uses a secondary appearance model to extract visual cues from each person region.
- It compares:
  - appearance similarity
  - motion prediction
  - spatial consistency across nearby frames
- If a detection looks like the same person from the previous frames, DeepSORT keeps the same track ID.
- This is how a person stays `Track 7`, `Track 12`, and so on across time.

Result:

- each detected person gets a persistent ID
- the system can now reason about one person over multiple frames instead of treating every frame as new

## 3. Feature Extraction

Once tracking becomes stable, the system extracts identity-supporting features for each confirmed track.

### 3.1 Face Verification

After DeepSORT locks onto a tracked ID, the system isolates that person region and sends it to the face module.

- The face module checks whether a usable face is visible.
- It rejects unusable samples such as:
  - strong blur
  - major occlusion
  - poor angle
  - very weak face crop
- If the quality gate passes, the system extracts a facial embedding.
- That embedding is compared against the known face database using cosine similarity.
- A face score is returned for that track.
- In this pipeline, a face match of `0.40` or above is treated as a meaningful positive signal.

Purpose:

- this stage does not decide by itself
- it contributes a biometric confidence signal for fusion

### 3.2 Clothing Features

The clothing module provides a secondary identity signal that is more stable when the face is weak or temporarily unavailable.

- It analyzes the upper body region of the tracked person.
- It extracts dominant clothing color.
- Colors are normalized into coarse categories such as:
  - red
  - blue
  - black
  - white
  - green
  - yellow
  - gray
- It optionally supports clothing type reasoning if available.
- It returns a clothing confidence score.

Example output:

```json
{
  "track_id": 12,
  "clothing": {
    "color": "blue",
    "confidence": 0.78
  }
}
```

Constraints:

- avoid sensitivity to lighting variation
- do not overfit very fine-grained shades
- do not make identity decisions here

### 3.3 Height Estimation

The height module provides another supporting signal.

- It estimates approximate height from pose/body geometry.
- It is treated as optional evidence, not a primary identity decision.
- It helps when face evidence is weak and clothing is common.

## 4. Fusion (Combine Signals)

At this point, the system has multiple partial signals for the same tracked person.

These signals are fused into one identity confidence score.

The fusion stage combines:

- face score
- clothing confidence
- height confidence

It produces:

- a final fused score
- a contribution breakdown showing how much each signal helped

Purpose:

- avoid trusting only one weak signal
- make the system more robust when one module is uncertain

## 5. Temporal Validation

A single strong frame is not enough for a reliable alert.

The temporal validation stage checks whether the fused confidence remains stable across consecutive frames.

- each track is monitored over time
- confidence must remain strong for enough frames
- unstable one-frame spikes are rejected

This reduces:

- false positives
- one-frame glitches
- noisy detections

Result:

- a track becomes `validated` only after it proves consistency over time

## 6. Alert Decision

Once a track is temporally validated, the system decides whether it should produce an operational alert.

This stage considers:

- final fusion score
- temporal validation status
- contribution strengths from the fused signals

It then assigns:

- alert or no alert
- confidence
- priority level

Purpose:

- convert raw model output into an actionable security decision

## 7. Explainability + Output Delivery

After an alert is triggered, the system explains why it was triggered and packages it for downstream use.

### Explainability

The explainability stage summarizes the evidence in human-readable form, for example:

- face score strength
- clothing color confidence
- whether the track was temporally validated
- how many consecutive frames supported the decision

### Output Delivery

The delivery stage then:

- saves an alert snapshot if a crop is available
- prepares a delivery record
- writes the alert into Supabase
- exposes the result to the dashboard API

## What the Dashboard Shows

The dashboard combines:

- live pipeline state from the running backend
- recent alert history from Supabase
- live stream overlay
- track list
- fusion summary
- alert queue
- delivery log

## Module Mapping

This is how the code maps to the stages above:

- Detection: `person_detection_module`
- Tracking: `multi_object_tracking_module`
- Face features: `facial_recognition_module`
- Clothing features: `clothing_feature_extraction_module`
- Height estimation: `height_estimation_module`
- Fusion: `multi_attribute_fusion_module`
- Temporal validation: `temporal_validation_module`
- Alert decision: `alert_decision_module`
- Explainability: `explainability_module`
- Output delivery: `output_delivery_module`
- Pipeline coordinator: `surveillance_backend_pipeline.py`
- Live API + dashboard server: `surveillance_live_service.py`

## Run Notes

### Person Detection Only

```bash
cd "d:\FYP MODELS\modules with skills\person_detection_module"
python run_detection.py
python run_detection.py --source "path/to/video.mp4"
python run_detection.py --source "path/to/image.jpg"
python run_detection.py --conf 0.65
```

### Tracking Only

```bash
cd "d:\FYP MODELS\modules with skills\multi_object_tracking_module"
python run_tracking.py --source 0
python run_tracking.py --source "path/to/video.mp4"
```

### Full Backend Pipeline

```bash
cd "d:\FYP MODELS\modules with skills"
python run_surveillance_pipeline.py --source 0
```

### Live Service + Dashboard

```bash
cd "d:\FYP MODELS\modules with skills"
python surveillance_live_service.py --source 0
```

## Simple Mental Model

You can think of the pipeline like this:

- YOLO says: "There is a person here."
- DeepSORT says: "This is the same person I saw before."
- Face/clothing/height say: "These are the attributes of that tracked person."
- Fusion says: "Here is the combined confidence."
- Temporal validation says: "This confidence stayed stable long enough."
- Alert decision says: "This now deserves an alert."
- Explainability says: "Here is why."
- Delivery says: "Store it, show it, and send it."

## Project Roadmap

This is the clean end-to-end build order for the full system.

### Phase 1. Core Vision Pipeline

Complete and verify the backend AI pipeline.

- webcam or video input works
- person detection works
- tracking works
- face verification works
- clothing features work
- optional height estimation works
- fusion works
- temporal validation works
- alert decision works
- explainability works
- alerts are stored in Supabase
- live web dashboard reads current state and alert history

Status:

- this phase is already in progress and mostly connected

### Phase 2. Database Integration Layer

Use Supabase as the shared system database for all clients.

- backend writes alert records to Supabase
- dashboard reads alert history from Supabase
- shared schema becomes the single source of truth
- both web and mobile clients read from the same data layer

Purpose:

- keep one backend data source
- avoid separate local-only state on each client

### Phase 3. Flutter Mobile Application

Build the client-side Flutter mobile application.

- create mobile UI for alerts, incident history, and live status
- connect Flutter app to the same Supabase database
- show recent alerts and relevant metadata
- optionally add authentication, user sessions, and role-based access
- optionally add push notifications for new alerts

Important:

- wait until the Flutter app structure is ready
- then connect it carefully to the same Supabase schema already used by the backend and dashboard

### Phase 4. External Camera Integration

Connect the pipeline to real surveillance-style camera sources instead of relying only on the local laptop webcam.

Possible camera sources:

- USB external camera
- IP camera / CCTV / RTSP stream
- Raspberry Pi camera
- Raspberry Pi acting as a stream sender

Main goal:

- make the pipeline accept a stable real-world surveillance feed as input

#### 4.1 USB or External Camera

If the camera behaves like a normal webcam:

- connect the external camera to the host machine
- identify its device index
- test it with OpenCV using `--source 0`, `--source 1`, or another index
- verify frame quality, lighting, and FPS
- confirm the pipeline can process it continuously

#### 4.2 IP Camera or CCTV Stream

If the surveillance camera provides a network stream:

- obtain the RTSP or HTTP stream URL
- test raw playback first
- connect the pipeline using that stream URL as `--source`
- verify authentication and network reachability
- verify stream stability under long-running sessions

Example idea:

```bash
python surveillance_live_service.py --source "rtsp://username:password@camera-ip:554/stream"
```

#### 4.3 Raspberry Pi Camera Integration

If using a Raspberry Pi, there are two common options.

Option A: run the camera on Raspberry Pi and stream video to the main backend

- attach Pi camera module or USB camera to Raspberry Pi
- capture frames on Raspberry Pi
- expose a stream over network
- send that stream to the main backend server
- process the stream centrally on the stronger machine or AWS instance

Option B: run lightweight capture on Raspberry Pi and send frames/events upstream

- Pi captures camera frames
- Pi forwards stream or selected frames to backend
- backend performs the heavy AI inference
- Supabase remains the shared central database

Recommended practical approach:

- use Raspberry Pi as the capture node
- use backend server or AWS as the inference node

That keeps the heavy model processing off the Pi unless you intentionally optimize for edge inference.

#### 4.4 External Camera Validation Checklist

Before treating the camera integration as complete, verify:

- camera feed opens reliably
- frame resolution is usable
- frame rate is stable
- night/low-light conditions are acceptable
- network interruptions are handled
- reconnect logic works
- stream latency is acceptable
- tracking IDs remain stable enough for the pipeline

### Phase 5. AWS Deployment

Deploy the pipeline and supporting services to AWS.

Typical deployment flow:

- package the backend pipeline
- provision compute for inference
- configure environment variables securely
- attach camera/video ingestion source
- expose backend API safely
- connect deployed backend to Supabase
- deploy the dashboard or admin interface
- test remote logging, monitoring, and alert flow

Possible AWS targets depend on final architecture:

- EC2 for direct long-running GPU/CPU service
- ECS or Docker-based deployment if containerized
- S3/CloudFront for static dashboard assets if separated
- CloudWatch for logs and monitoring

Important design decision before deployment:

- choose whether cameras send streams directly to AWS
- or cameras/Raspberry Pi send data to a local gateway first
- or a Raspberry Pi acts as the edge capture device and AWS runs the inference backend

### Phase 6. System Integration Testing

Once backend, web, mobile, and cloud deployment are all connected, run full-system validation.

- verify live alerts reach Supabase
- verify dashboard reads deployed backend data
- verify Flutter app reads the same database
- verify snapshots and metadata stay consistent
- verify latency is acceptable
- verify reconnection and failure handling
- verify alert duplication does not occur

Also verify camera-side integration:

- verify external camera feed reaches deployed backend
- verify Raspberry Pi or IP camera reconnects after temporary drop
- verify remote camera timestamps stay consistent
- verify camera source switching does not break the pipeline

### Phase 7. Final Hardening Before Submission or Production

This is the stage that is often forgotten, but it matters a lot.

- clean folder structure
- finalize `.env` and secret handling
- add backup and recovery plan
- validate database schema
- document setup and deployment steps
- define test cases and demo flow
- check performance on long-running sessions
- check logging and monitoring
- polish UI for web and mobile

## After AWS and Flutter, What Would Be Left?

Once the Flutter app is connected and the backend is deployed on AWS, the main remaining work would usually be:

- full integration testing
- bug fixing from real usage
- authentication and permissions if needed
- production hardening
- monitoring and logging improvements
- documentation
- demo/presentation preparation
- real camera reliability tuning if using external surveillance feeds

So no, the project would not be "unfinished" in a big way at that point.
What would remain is the final engineering polish layer around the already-built system.

## Collaboration Note

When your Flutter mobile application is ready, we can continue from this exact point.

Recommended next sequence after your Flutter app is prepared:

1. review Flutter project structure
2. connect Flutter to the existing Supabase schema
3. test live alert reads on mobile
4. decide the real camera source: USB, IP camera, or Raspberry Pi
5. connect the real camera feed to the backend
6. prepare AWS deployment for the backend
7. run full end-to-end testing across backend, web, mobile, camera input, and database
