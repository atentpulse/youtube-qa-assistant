# VidMind 2.0 — Security Architecture & Threat Model

## 1. Authentication & Session Security

- **Production Configuration Safeguards**:
  - Centralized settings in [`app.core.config.Settings`](file:///backend/app/core/config.py) automatically validate that when running in production (`ENVIRONMENT="production"` or `"prod"`), the default insecure placeholder `SECRET_KEY` is strictly rejected at startup.
  - Production configurations enforce a cryptographically strong secret with a minimum length of 32 characters.
  - Convenient local development setups are preserved without weakening production safeguards.

- **JWT Signing, Token Types & Refresh Lifecycle**:
  - Signed using `HS256` with distinct token types encoded in the payload (`type: "access"` and `type: "refresh"`).
  - Short-lived **Access Tokens** (`ACCESS_TOKEN_EXPIRE_MINUTES = 15`) protect API endpoints.
  - Long-lived **Refresh Tokens** (`REFRESH_TOKEN_EXPIRE_DAYS = 7`) enable renewal without credential re-entry.
  - Strict scope boundary: `app.auth.dependencies.get_current_user` explicitly inspects `token_type` and rejects refresh tokens attempting API access with `HTTP 401 Unauthorized`.
  - Dual-mode `POST /auth/refresh`:
    - **Dedicated Body Flow**: Accepts `{ "refresh_token": "..." }`, validates type/signature/expiry, and issues a rotated new refresh token + access token.
    - **Active Bearer Flow**: Accepts active Bearer header token for seamless backward compatibility with the existing React frontend client (`AuthContext`).
    - Expired or tampered tokens are rejected with `HTTP 401 Unauthorized`.

- **Password Protection**:
  - Passwords are salted and hashed using `bcrypt` via PassLib.
  - Plaintext passwords are never logged, cached, or returned in API responses.

- **Enumeration Prevention & Email Security**:
  - Verification and password-reset endpoints (`/auth/forgot-password`, `/auth/resend-verification`) return identical timing-resistant generic responses regardless of whether the requested email exists in the database.
  - `EmailService` handles absence of SMTP credentials gracefully without crashing or throwing unhandled 500 errors.
  - Logs are sanitized: sensitive verification tokens, password reset tokens, and full reset URLs are never printed to logs or standard streams.

---

## 2. Distributed Advisory Locking & Ingestion Safety

- **PostgreSQL Session Advisory Locks**:
  - Implemented in [`app.services.lock_service.VideoIngestionLock`](file:///backend/app/services/lock_service.py).
  - Derives a deterministic signed 64-bit integer from `video_id` using SHA-256 (`video_id_to_lock_id`).
  - Calls `pg_try_advisory_lock(lock_id)` non-blockingly across multiple worker processes or Uvicorn instances.
  - Ensures exactly one background worker processes a given YouTube video (transcription, chunking, and embedding generation), preventing race conditions, wasted compute, duplicate Qdrant upserts, or cache thrashing without requiring Redis.
  - Includes SQLite thread-safe fallback for test harnesses and defensive rollback recovery during release.

---

## 3. Cross-Origin Resource Sharing (CORS) & Dual-Client Security

- **Origin Isolation**:
  - Preflight `OPTIONS` requests from unapproved origins (e.g., untrusted websites) are rejected with `400 Bad Request`.
  - Whitelist origins are dynamically aggregated from:
    1. `FRONTEND_URL` (React Web app).
    2. `CORS_ALLOWED_ORIGINS` (Configurable multi-environment URLs).
    3. `CHROME_EXTENSION_IDS` (Specific extension IDs).
  - Explicit regex pattern `^chrome-extension://[a-zA-Z0-9_-]+$` ensures only authentic Chrome extension origins can communicate with the backend API.

---

## 4. Data Isolation & Multi-Tenancy

- **User Video Isolation**:
  - All video library queries (`GET /videos`, `GET /videos/{video_id}/status`) join on `user_videos.user_id == current_user.id`.
  - Users cannot access, query, or view processing states of videos not linked to their account.

- **Conversation Isolation & Cross-Video Protection**:
  - Conversations belong strictly to `user_id == current_user.id`.
  - Cross-video query attempts (asking about Video B inside Video A's conversation thread) are rejected with `HTTP 400 Bad Request`, preventing prompt injection and context contamination across different video transcripts.

- **Reference-Counted Safe Purge**:
  - Deleting a video from a user's library only severs that user's association (`user_videos`).
  - Shared vectors and canonical metadata are retained until all referencing users and conversations have ceased to exist, preventing data-denial attacks against other users.
