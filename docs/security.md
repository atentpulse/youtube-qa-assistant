# YtGenius 2.0 — Security Architecture & Threat Model

## 1. Authentication & Session Security

- **Production Configuration Safeguards**:
  - Centralized settings in [`app.core.config.Settings`](file:///backend/app/core/config.py) automatically validate that when running in production (`ENVIRONMENT="production"` or `"prod"`), the default insecure placeholder `SECRET_KEY` is strictly rejected at startup.
  - Production configurations enforce a cryptographically strong secret with a minimum length of 32 characters.
  - Convenient local development setups are preserved without weakening production safeguards.

- **JWT Signing, Token Types & Refresh Lifecycle**:
  - Signed using configurable HMAC algorithm strictly validated against `{"HS256", "HS384", "HS512"}` (default `HS256`). Insecure algorithms (e.g. `none`, arbitrary strings) and asymmetric algorithms without key-pair infrastructure are strictly rejected at startup by Pydantic field validators.
  - Symmetrical unified encoding and decoding: both `jwt.py` and `dependencies.py` dynamically reference `settings.ALGORITHM`.
  - Distinct token types encoded in the payload (`type: "access"` and `type: "refresh"`).
  - Short-lived **Access Tokens** (`ACCESS_TOKEN_EXPIRE_MINUTES = 60`) protect API endpoints.
  - Long-lived **Refresh Tokens** (`REFRESH_TOKEN_EXPIRE_DAYS = 7`) enable renewal without credential re-entry.
  - Strict scope boundary: `app.auth.dependencies.get_current_user` explicitly inspects `token_type` and rejects refresh tokens attempting API access with `HTTP 401 Unauthorized`.
  - Dual-mode `POST /auth/refresh`:
    - **Dedicated Body Flow**: Accepts `{ "refresh_token": "..." }`, validates type/signature/expiry, and issues a rotated new refresh token + access token.
    - **Active Bearer Flow**: Accepts active Bearer header token for seamless backward compatibility with the existing React frontend client (`AuthContext`).
    - Expired or tampered tokens are rejected with `HTTP 401 Unauthorized`.

- **Passwordless Email OTP Security**:
  - 6-digit numeric OTPs generated cryptographically (`secrets.randbelow`).
  - Stored strictly as SHA-256 hashes (`email_otps.otp_hash`); plaintext OTPs are never stored in the database.
  - Short validity window (`OTP_EXPIRE_MINUTES = 5`).
  - Brute-force protection: bounded verification attempts (`OTP_MAX_ATTEMPTS = 5`), after which the OTP record is permanently invalidated.
  - Single-use consumption: verification immediately sets `used_at = datetime.now(timezone.utc)`, preventing replay attacks.
  - Rate limiting on OTP dispatch (`OTP_RESEND_COOLDOWN_SECONDS = 60`) preventing email flooding and denial of wallet attacks.
  - Automatic email verification: verifying a valid OTP immediately sets `email_verified = True` for the user.

- **Password Reset & Email Verification Token Lifecycle**:
  - Verification tokens (`email_verification_tokens`) and password reset tokens (`password_reset_tokens`) are generated as 32-byte cryptographic random strings (`secrets.token_urlsafe(32)`).
  - Stored strictly as unique SHA-256 hashes (`token_hash = Column(String(255), unique=True, index=True)`); raw tokens are only transmitted to the user's verified inbox.
  - Bounded token expiration: 30-minute validity window (`settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES = 30`, `settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30`).
  - Single-use invalidation: tokens record a `used_at` timestamp upon consumption; consumed or expired tokens are rejected with `HTTP 400 Bad Request`.
  - Database integrity: cascade-deleted upon user account removal (`ForeignKey("users.id", ondelete="CASCADE")`).

- **Account Lifecycle & Support Privacy Limitations**:
  - The backend provides authenticated account deletion (`DELETE /auth/me`) which cascades reference-counted video unlinking and permanent user record removal.
  - **User-Facing UI Limitation**: No frontend user interface currently exposes the deletion action; deletion is currently supported via the authenticated API client.
  - **Public Support Channel Disclosure**: Public GitHub Issues are utilized for open-source bug reporting and community support. Public issues are visible to everyone and must **never** be used as a private support channel or for transmitting passwords, tokens, API keys, or personal identity verification data.

- **Password Protection**:
  - Passwords are salted and hashed using `bcrypt` via PassLib.
  - Plaintext passwords are never logged, cached, or returned in API responses.

- **Enumeration Prevention & Email Security**:
  - Verification and password-reset endpoints (`/auth/forgot-password`, `/auth/resend-verification`) return identical timing-resistant generic responses regardless of whether the requested email exists in the database.
  - `EmailService` handles absence of SMTP credentials gracefully without crashing or throwing unhandled 500 errors.
  - Logs are sanitized: sensitive verification tokens, password reset tokens, and full reset URLs are never printed to logs or standard streams.

- **Google OAuth Redirect URI Security & Production Hardening**:
  - Centralized validation in [`app.core.config.Settings`](file:///backend/app/core/config.py) (`validate_production_security`) strictly enforces production callback policies for `GOOGLE_REDIRECT_URI`:
    - **HTTPS Scheme Required**: In production (`ENVIRONMENT="production"` or `"prod"`), the redirect URI must strictly use the `https://` scheme. Insecure `http://` schemes are rejected at startup.
    - **Public Hostname / IP Required**: Localhost (`localhost`, `*.localhost`), IPv4 loopback (`127.0.0.0/8`), IPv6 loopback (`::1`), RFC 1918 private IPv4 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), unique-local IPv6 (`fc00::/7`), and link-local addresses (`169.254.0.0/16`, `fe80::/10`) are strictly rejected.
    - **Non-Global & Multicast IP Rejection**: Enforces `(not ip.is_global) or ip.is_multicast`, rejecting RFC 6598 Carrier-Grade NAT / Shared Address Space (`100.64.0.0/10`), unspecified addresses (`0.0.0.0`, `::`), reserved addresses (`240.0.0.0/4`), documentation ranges, and multicast addresses (`224.0.0.0/4`, `ff00::/8`).
    - **Exact Callback Path Matching**: Path must strictly match `/auth/google/callback`. Subpaths, alternative paths, and trailing slashes (`/auth/google/callback/`) are rejected with `ValueError`.
    - **Port Validation & Empty Port Rejection**: Port must fall strictly in the range `1 <= port <= 65535`. Explicitly empty ports (e.g. `example.com:`), zero (`:0`), non-numeric (`:abc`), and out-of-range (`:65536`) ports are rejected using bracket-aware authority parsing that correctly handles IPv6 bracket syntax (`[2606:4700:4700::1111]`).
    - **No Embedded Credentials or Query/Fragments**: URLs bearing username/password (`https://user:pass@...`), query strings (`?query=1`), or fragments (`#hash`) are rejected.
  - **Development Localhost Compatibility**: When running in development (`ENVIRONMENT="development"`), `http://localhost:8000/auth/google/callback` and `http://127.0.0.1:8000/auth/google/callback` are permitted, and trailing slashes are cleaned automatically for developer convenience without relaxing production requirements.
  - **Testing & Real OAuth Boundary Disclosure**: Automated unit and integration tests verify OAuth initiation, state handling, code exchange logic, and configuration validation. However, **real Google OAuth end-to-end authentication using actual Google credentials has not been verified** against live Google accounts. Automated tests with simulated responses are not equivalent to a real production OAuth login.

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

---

## 5. Vector Store & Embedding Integrity

- **Dynamic Vector Dimension Introspection**:
  - `EmbeddingService` introspects the active SentenceTransformer model dimension and verifies parity with `VECTOR_DIMENSION` (384).
- **Non-Destructive Qdrant Collection Validation**:
  - `QdrantVectorStore.create_collection` introspects existing collection vector size without deleting or recreating the collection.
  - Dimension conflicts fail safely and loudly with `ValueError`, preserving existing vectors and prevent silent corruption.
- **Batch Vector Dimension Enforcement**:
  - `QdrantVectorStore.add_documents` strictly asserts each chunk vector's dimension before issuing batch upserts to Qdrant Cloud.

---

## 6. Rate Limiting Architecture & Process-Local Scope

- **Sliding-Window Implementation**:
  - Managed by `app.core.rate_limiter.RateLimiter`.
  - Maintains an in-memory dictionary of request timestamps per client IP (`Dict[str, List[float]]`), synchronized with thread locks.
  - Automatically filters expired timestamps outside the configured time window.
- **Process-Local Scope Disclosure**:
  - The rate limiter is strictly **in-memory and process-local**.
  - In multi-worker Uvicorn configurations (e.g. `--workers 4`) or multi-container deployments, **each worker process maintains its own independent rate-limiting table**. State is not shared across processes.
- **Distributed Limitation & Future Requirements**:
  - Global cluster-wide rate limiting across multiple server instances or replicas is not natively implemented and would require a centralized, shared key-value store such as Redis (e.g., executing Redis Lua scripts). Redis is not part of the active repository stack.
- **Reverse Proxy Client IP Resolution**:
  - Rate limiting extracts client IP safely using `get_client_ip()`.
  - Only when the immediate connecting IP matches `TRUSTED_PROXIES` (default `["127.0.0.1", "::1"]`) is the `X-Forwarded-For` header parsed (reading hops from right to left) to prevent header spoofing from untrusted public clients.
