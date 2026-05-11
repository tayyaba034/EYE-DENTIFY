# EYE-DENTIFY PROJECT ANALYSIS AND TEMPORARY DECOUPLING REPORT

## 1. What was done

The project already had a separate Flutter app and Node.js backend, but the frontend was still directly using the `Supabase` client SDK in some places. That meant the mobile app was still partly connected to the database layer instead of depending only on backend-owned interfaces.

For temporary decoupling, the codebase was adjusted so that:

- The frontend now uses the backend REST API for auth and data operations.
- The frontend no longer initializes `Supabase` directly.
- The frontend no longer uses `Supabase` realtime for notifications.
- Notifications now refresh through the backend websocket layer instead of direct database subscription from the app.
- The database remains behind the backend, which is the correct integration boundary.

This gives you three independent parts:

1. Frontend app
2. Backend server
3. Database and storage services

They can now be developed and tested more independently, then integrated through APIs and websocket events.

---

## 2. Current system in simple words

### Frontend

The frontend is a Flutter mobile app in [eye_dentify](/d:/frontend%20test/eye_dentify). It is responsible for:

- Showing login, signup, alerts, cases, profile, map-related UI
- Calling backend APIs through `Dio`
- Holding temporary app state through `Provider`
- Receiving realtime updates through websocket
- Receiving mobile push notifications through Firebase Cloud Messaging

Important frontend layers:

- `features/`: screens and UI
- `providers/`: state management
- `services/`: API calling logic
- `models/`: app data structures
- `core/network/`: API client and websocket client

Main frontend entry:

- [main.dart](/d:/frontend%20test/eye_dentify/lib/main.dart)

Important frontend service files:

- [api_client.dart](/d:/frontend%20test/eye_dentify/lib/core/network/api_client.dart)
- [api_config.dart](/d:/frontend%20test/eye_dentify/lib/core/network/api_config.dart)
- [auth_service.dart](/d:/frontend%20test/eye_dentify/lib/services/auth_service.dart)
- [missing_person_service.dart](/d:/frontend%20test/eye_dentify/lib/services/missing_person_service.dart)
- [alert_service.dart](/d:/frontend%20test/eye_dentify/lib/services/alert_service.dart)
- [notification_provider.dart](/d:/frontend%20test/eye_dentify/lib/providers/notification_provider.dart)

### Backend

The backend is a Node.js + Express server in [eye_dentify_backend](/d:/frontend%20test/eye_dentify_backend). It is responsible for:

- Authentication
- Business logic
- Validation
- Role-based access
- Realtime event broadcasting
- Database reads and writes
- Storage uploads
- Push notification sending
- Alert generation and alert lifecycle management

Main backend layers:

- `routes/`: API endpoints
- `controllers/`: request handling
- `services/`: special logic like Firebase, AI, encryption, realtime, storage
- `middleware/`: auth, validation, security, error handling
- `config/`: database connection

Main backend entry:

- [app.js](/d:/frontend%20test/eye_dentify_backend/app.js)

Important backend files:

- [database.js](/d:/frontend%20test/eye_dentify_backend/config/database.js)
- [authController.js](/d:/frontend%20test/eye_dentify_backend/controllers/authController.js)
- [missingPersonsController.js](/d:/frontend%20test/eye_dentify_backend/controllers/missingPersonsController.js)
- [detectionsController.js](/d:/frontend%20test/eye_dentify_backend/controllers/detectionsController.js)
- [alertsController.js](/d:/frontend%20test/eye_dentify_backend/controllers/alertsController.js)
- [notificationController.js](/d:/frontend%20test/eye_dentify_backend/controllers/notificationController.js)
- [realtimeHub.js](/d:/frontend%20test/eye_dentify_backend/services/realtimeHub.js)

### Database and storage

The main data layer is Supabase/PostgreSQL plus Supabase Storage.

It stores:

- users and profiles
- missing person cases
- uploaded media
- detections
- alerts
- notifications
- device tokens
- cameras
- logs

Database setup files:

- [2026_03_03_supabase_core.sql](/d:/frontend%20test/eye_dentify_backend/migrations/2026_03_03_supabase_core.sql)
- [2026_03_03_supabase_required_setup.sql](/d:/frontend%20test/eye_dentify_backend/migrations/2026_03_03_supabase_required_setup.sql)
- [2026_02_04_alert_lifecycle.sql](/d:/frontend%20test/eye_dentify_backend/migrations/2026_02_04_alert_lifecycle.sql)

---

## 3. How the separation works now

### Before

The frontend was still doing these direct database-platform actions:

- initializing `Supabase` inside the app
- using `Supabase` auth session handling in frontend auth service
- using `Supabase` realtime in notification provider

### After

Now the boundary is cleaner:

- Frontend only knows backend HTTP endpoints and backend websocket URL
- Backend talks to Supabase/Postgres
- Backend talks to Firebase Admin
- Backend talks to storage and AI helpers

So the architecture is now:

`Flutter App -> Backend API/WebSocket -> Database/Storage/Push Services`

That is the correct temporary separation for independent work.

---

## 4. What each side can do independently

### Frontend can work independently if:

- backend API contract is available
- backend websocket contract is available
- sample JSON responses are known

Frontend team can then:

- build screens
- validate forms
- test provider logic
- connect to staging backend later

### Backend can work independently if:

- database schema is available
- environment variables are configured
- API contracts are fixed

Backend team can then:

- test controllers
- evolve business logic
- connect AI/detection pipeline
- handle auth and notifications

### Database can work independently if:

- tables, relations, RLS, and storage buckets are defined
- migrations are versioned

Database work includes:

- schema changes
- indexes
- policies
- storage bucket rules
- backup and restore

---

## 5. Main APIs in this project

Base API mount:

- `/api/auth`
- `/api/alerts`
- `/api/detections`
- `/api/missing-persons`
- `/api/cameras`
- `/api/notifications`

Health endpoint:

- `GET /health`

### Auth API

From [authRoutes.js](/d:/frontend%20test/eye_dentify_backend/routes/authRoutes.js):

- `POST /api/auth/login`
- `POST /api/auth/register`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/auth/forgot-password`

Purpose:

- login and signup
- token refresh
- logout
- get current user
- password reset

### Alerts API

From [alertsRoutes.js](/d:/frontend%20test/eye_dentify_backend/routes/alertsRoutes.js):

- `GET /api/alerts/my`
- `GET /api/alerts/snapshot`
- `GET /api/alerts/:id`
- `PATCH /api/alerts/:id/read`
- `PATCH /api/alerts/:id/acknowledge`
- `PATCH /api/alerts/:id/dismiss`
- `POST /api/alerts/:id/confirm-match`
- `POST /api/alerts/:id/reject-match`

Purpose:

- fetch user alerts
- refresh latest alert state
- mark alert state
- perform human verification

### Detections API

From [detectionsRoutes.js](/d:/frontend%20test/eye_dentify_backend/routes/detectionsRoutes.js):

- `POST /api/detections/ingest`
- `GET /api/detections/:id`
- `POST /api/detections/:id/verify`

Purpose:

- accept detection pipeline events
- fetch a detection
- manually verify detections

### Missing person API

From [missingPersonsRoutes.js](/d:/frontend%20test/eye_dentify_backend/routes/missingPersonsRoutes.js):

- `POST /api/missing-persons/upload-photo`
- `POST /api/missing-persons/generate-description`
- `POST /api/missing-persons/`
- `GET /api/missing-persons/my`
- `GET /api/missing-persons/`
- `GET /api/missing-persons/:id`
- `PUT /api/missing-persons/:id`
- `DELETE /api/missing-persons/:id`
- `GET /api/missing-persons/:id/detections`
- `POST /api/missing-persons/:id/scan-social`

Purpose:

- create and manage missing person cases
- upload case photos
- generate AI description text
- fetch detections for a case
- scan external social data

### Cameras API

From [cameraRoutes.js](/d:/frontend%20test/eye_dentify_backend/routes/cameraRoutes.js):

- `GET /api/cameras`
- `GET /api/cameras/:id`
- `POST /api/cameras`
- `PUT /api/cameras/:id`
- `DELETE /api/cameras/:id`

Purpose:

- manage surveillance cameras

### Notifications API

From [notificationRoutes.js](/d:/frontend%20test/eye_dentify_backend/routes/notificationRoutes.js):

- `POST /api/notifications/device-token`
- `POST /api/notifications`
- `POST /api/notifications/send`
- `GET /api/notifications`
- `PATCH /api/notifications/:id/read`

Purpose:

- register FCM token
- send and fetch notifications
- mark notification as read

---

## 6. Realtime flow

The backend websocket path is:

- `/ws`

Realtime is handled in:

- [realtimeHub.js](/d:/frontend%20test/eye_dentify_backend/services/realtimeHub.js)

Used for:

- alert updates
- case updates
- notification refresh events

Frontend websocket usage:

- [alert_provider.dart](/d:/frontend%20test/eye_dentify/lib/providers/alert_provider.dart)
- [missing_person_provider.dart](/d:/frontend%20test/eye_dentify/lib/providers/missing_person_provider.dart)
- [notification_provider.dart](/d:/frontend%20test/eye_dentify/lib/providers/notification_provider.dart)

Important note:

- Alerts and cases are pushed directly as websocket events.
- Notifications are now refreshed through backend websocket events instead of direct Supabase realtime in the app.

---

## 7. Main algorithms and logic used

This project is not only CRUD. It contains several decision rules and detection heuristics.

### 1. Alert deduplication algorithm

In [detectionsController.js](/d:/frontend%20test/eye_dentify_backend/controllers/detectionsController.js):

- checks `track_id`
- checks `camera_id`
- checks similarity score threshold
- checks recent time window

Purpose:

- avoid creating duplicate alerts for the same person every frame

### 2. Confidence scoring

The backend combines:

- face score
- clothing score
- camera reliability score

Purpose:

- produce a stronger effective confidence instead of trusting one score only

### 3. Multi-frame confirmation

The system checks whether the same track appears multiple times in a short window.

Purpose:

- reduce false positives
- avoid reacting to one weak frame

### 4. Multi-camera confirmation

If the same track appears across different cameras in a short time, the alert severity increases.

Purpose:

- raise confidence and urgency

### 5. Alert level classification

Levels used:

- `preliminary`
- `tracking`
- `strong_match`
- `critical`

This is based on:

- number of sightings
- face score
- clothing score
- multi-frame result
- multi-camera result

### 6. Alert expiry logic

From [alertExpiryWorker.js](/d:/frontend%20test/eye_dentify_backend/services/alertExpiryWorker.js):

- preliminary alerts expire fastest
- tracking alerts expire after a longer window
- strong matches stay longer

Purpose:

- keep dashboard clean
- reduce stale alerts

### 7. Human-in-the-loop verification

Security/admin users can:

- confirm match
- reject false alarm

Purpose:

- combine AI decisions with human judgment

### 8. AI text generation

The backend uses AI service helpers for:

- alert summaries
- case description generation

Purpose:

- create readable summaries for users

### 9. Social scan integration

The backend uses Apify-based scraping helpers to search for sightings related to a case.

Purpose:

- expand search beyond camera feeds

---

## 8. Technologies used

### Frontend

- Flutter
- Provider
- Dio
- WebSocket
- Firebase Messaging
- Shared Preferences
- Google Maps Flutter
- Geolocator / Geocoding

### Backend

- Node.js
- Express
- Supabase JS
- PostgreSQL
- Firebase Admin
- WebSocket (`ws`)
- Multer
- Zod
- Winston
- Apify

### Database and platform

- Supabase Auth
- Supabase Postgres
- Supabase Storage
- Row Level Security

---

## 9. Deployment view in simple wording

### Frontend deployment

Flutter app can be deployed as:

- Android APK/AAB
- iOS app build

Frontend needs these runtime connections:

- backend API base URL
- backend websocket URL
- Firebase project config

### Backend deployment

Backend can be deployed on:

- Render
- Railway
- VPS
- AWS EC2
- Azure App Service
- DigitalOcean

Backend needs:

- `PORT`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- optional `SUPABASE_ANON_KEY`
- `DATABASE_URL`
- Firebase admin key
- AI provider keys
- Apify token
- detection ingest secret

### Database deployment

Supabase already acts as hosted database/auth/storage platform.

Needed setup:

- tables
- indexes
- storage bucket
- RLS policies
- service role access for backend

---

## 10. How integration should be done

The proper integration order is:

1. Finalize database schema and migrations.
2. Finalize backend API request and response shapes.
3. Connect frontend only to backend URLs.
4. Use websocket only through backend.
5. Use Firebase only for push delivery, not as the business database.

Recommended final production flow:

1. User logs in from Flutter app.
2. Backend validates through Supabase Auth.
3. Backend returns access and refresh tokens.
4. Flutter stores tokens locally.
5. Flutter calls all features through backend APIs.
6. Detection pipeline sends data to backend ingest API.
7. Backend stores detections and creates alerts.
8. Backend pushes websocket updates to app.
9. Backend sends FCM push if alert is important.

---

## 11. What an evaluator can ask

### Architecture questions

- Why did you separate frontend from direct database access?
- Why is backend the correct integration point?
- Why use websocket in addition to REST?
- Why use Provider in Flutter?

### Backend questions

- How do you prevent duplicate alerts?
- How do you classify alert severity?
- How do you verify a user token?
- What is the role of middleware?
- Why do you use both Supabase and raw PostgreSQL queries?

### Database questions

- Which main tables are used?
- How are users linked with cases and alerts?
- What is stored in `notifications`, `device_tokens`, `detections`, and `alerts`?
- Why use Row Level Security?

### Realtime questions

- How does the app receive live alerts?
- What happens if websocket disconnects?
- Why was direct Supabase realtime removed from the frontend for temporary decoupling?

### AI/algorithm questions

- How is confidence calculated?
- What is multi-frame confirmation?
- What is multi-camera confirmation?
- Why do alerts expire?
- Why keep human verification in the loop?

### Deployment questions

- Where will frontend be deployed?
- Where will backend be deployed?
- Where will database and storage live?
- Which secrets are needed in production?

---

## 12. Important strengths of this project

- Clear frontend and backend folders
- Real API structure already exists
- Realtime support exists
- Push notification support exists
- Missing person workflow is complete enough to demonstrate end-to-end architecture
- Alert logic is more intelligent than simple CRUD
- Database schema already reflects real use cases

---

## 13. Important limitations still present

- Backend websocket is still broadcast-oriented, not fully user-scoped
- Full automated tests were not found for the main flows
- Some UI screens are still more polished visually than functionally
- FCM device-token registration currently happens before login, so token-to-user association may need one more cleanup pass after auth
- Existing alerts websocket events still include alert payloads broadly, so a later security hardening pass should add authenticated per-user websocket channels

---

## 14. Files changed for temporary separation

Frontend changes:

- [main.dart](/d:/frontend%20test/eye_dentify/lib/main.dart)
- [auth_service.dart](/d:/frontend%20test/eye_dentify/lib/services/auth_service.dart)
- [notification_provider.dart](/d:/frontend%20test/eye_dentify/lib/providers/notification_provider.dart)
- [api_config.dart](/d:/frontend%20test/eye_dentify/lib/core/network/api_config.dart)
- [pubspec.yaml](/d:/frontend%20test/eye_dentify/pubspec.yaml)

Backend changes:

- [notificationController.js](/d:/frontend%20test/eye_dentify_backend/controllers/notificationController.js)
- [detectionsController.js](/d:/frontend%20test/eye_dentify_backend/controllers/detectionsController.js)

Documentation:

- [file_analysis.md](/d:/frontend%20test/Code%20Audit/file_analysis.md)

---

## 15. Final short explanation

In easy words:

- Frontend is the mobile app users see.
- Backend is the brain and control center.
- Database is the memory.

Now the app is more properly separated because the frontend does not directly depend on the database platform SDK for normal app behavior. It goes through backend APIs and backend websocket events, which makes the system easier to maintain, safer to extend, and easier to deploy in a professional way.
