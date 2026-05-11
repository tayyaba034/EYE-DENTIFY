# EYE-DENTIFY: Smart Surveillance System 👁️

**EYE-DENTIFY** is a full-stack AI-powered surveillance platform designed for missing person tracking and real-time security alerts. It consists of a robust **Flutter mobile application** and a **production-ready Node.js backend** built with an uncompromising focus on security and privacy.

---

## 🏗️ System Architecture

The project follows a **Layered Modular Architecture** on both the frontend and backend to ensure scalability, maintainability, and security.

### 📱 Frontend (Flutter)
The frontend is organized into feature-centric layers:
- **UI Layer (Features)**: Atomic screens and widgets (Auth, Alerts, Case Management).
- **State Layer (Providers)**: Managed state via `Provider` package (e.g., `AuthProvider`, `AlertProvider`).
- **Service Layer**: Business logic (Auth, API calls, Location tracking).
- **Core Layer**: Infrastructure including theme, custom widgets, and network utilities.

### 🌐 Backend (Node.js/Express)
The backend follows a strict modular separation of concerns:
- **Routes Layer**: Endpoint definitions with specific rate limiters and validation.
- **Controller Layer**: Handles HTTP requests and business logic flow.
- **Service Layer**: Handles specialized logic like AES encryption, AWS S3 interaction, and database queries.
- **Middleware Layer**: Enforces security, authentication, and global error handling.

### 🔄 Communication Layer
- **REST API**: Secure communication over HTTPS using JSON.
- **Authentication**: JWT-based session management with **Access Tokens (15m)** and **Refresh Tokens (7d)**.
- **Token Rotation**: Implements refresh token rotation to prevent session hijacking.
- **Image Handling**: Uses **Pre-signed URLs** (PUT/GET) via AWS S3 to ensure no private media is ever exposed to the public internet.

---

## 🔐 Security & Privacy Layer

Security is baked into every layer of the EYE-DENTIFY system:

### 1. Authentication Security
- **Hashing**: Passwords are never stored in plain text. We use `bcryptjs` with **12+ salt rounds**.
- **Brute Force**: **Account Locking** is enforced after 5 failed login attempts.
- **JWT Protection**: Tokens contain encrypted payloads (`userId`, `role`) and are signed with unique secrets.

### 2. Role-Based Access Control (RBAC)
Server-side authorization ensures every request is validated against the user's role:
- **Guardians**: Can only access cases they personally reported via Ownership Enforcement.
- **Security Personnel**: Access to live detection alerts and surveillance map data.
- **Admin**: Full system management and auditing capabilities.

### 3. Data Protection (PII)
- **AES-256-CBC Encryption**: Sensitive data like parent phone numbers and precise location coordinates are encrypted before entering the database.
- **API Hardening**: Uses `helmet` for security headers, strict `CORS` origin restrictions, and `express-rate-limit` to prevent DDoS/Scraping.
- **Logging**: A custom Winston-based logger is used that automatically masks passwords and tokens to prevent accidental data leaks in logs.

### 4. Media Security (AWS S3)
- **Zero Public Access**: The S3 bucket is strictly private. 
- **Temporary Access**: The app requests a signed URL (valid for 60s) just to upload an image and another short-lived URL to view it.
- **Anonymity**: Filenames is randomized using UUIDs to prevent enumeration attacks.

---

## 📂 Project Structure

### Frontend (`/eye_dentify`)
```
lib/
├── core/                   # Network client, theme, validators
├── features/               # Auth, Alerts, Cases, Report Stepper
├── models/                 # AlertModel, MissingPersonModel
├── providers/              # AuthProvider, AlertProvider
└── services/               # AuthService, S3Service
```

### Backend (`/eye_dentify_backend`)
```
├── controllers/            # Auth, Case, Alert controllers
├── middleware/             # Auth, RBAC, Validation, Security filters
├── routes/                 # API endpoint definitions
├── services/               # Encryption, S3 Signed URLs, Logger
└── app.js                  # Entry point with consolidated security layer
```

---

## 🚀 Recent Accomplishments

1.  **Full UI Integration**: Connected the Flutter app to real-time providers, replacing all mock data with functional states.
2.  **API Hardening**: Implemented multiple rate limiters and secure headers.
3.  **Encrypted PII Storage**: Added server-side encryption utilities for sensitive data.
4.  **S3 Signed URL Flow**: Replaced direct public image links with secure temporary access URLs.
5.  **Lint-Free Frontend**: Resolved 100+ linting issues following the latest Flutter 3.27+ standards.

---

**EYE-DENTIFY: Professional AI Surveillance Platform.**
