# YtGenius 2.0 — Implementation Progress & State Checkpoint

## 1. Project Metadata
- **Project**: YtGenius — AI-powered YouTube Video Q&A Assistant (Backend v2.0)
- **Primary Repository**: `C:\Users\ashik\OneDrive\Desktop\youtube-qa-assistant` (`rajashik-web/youtube-qa-assistant` on `main`)
- **Protocol File**: [`AGENTS.md`](file:///c:/Users/ashik/OneDrive/Desktop/youtube-qa-assistant/AGENTS.md)
- **Current Phase**: **Phase 2: Docker Runtime Verification, Host Port Resolution & OAuth Hardening COMPLETED**
- **Last Updated**: 2026-11-11 21:05 IST
- **Verification Status**: **182/182 Automated Backend Tests Passing (100% Full Regression Pass Rate) + 20/20 Frontend Unit Tests Passing (100%)**

---

## 2. Phase-by-Phase Progress & Status

| Phase / Remediation | Description | Status | Evidence / Verification |
| :--- | :--- | :--- | :--- |
| **Phase A** | Read-Only Audit & Baseline | **COMPLETE** | Verified 8 database tables, Qdrant Cloud cluster, Groq LLM integration, SentenceTransformers embeddings, and identified 6 core architectural defects. |
| **Phase B** | Architecture & API Contract Review | **COMPLETE** | Documented inventory of 14 endpoints, detailed P1-P8 prioritized remediation plan, proposed Canonical `videos` + `user_videos` architecture. |
| **Phase C** | Foundation, Config & Test Infrastructure | **COMPLETE** | 1. Created [`backend/app/core/config.py`](file:///backend/app/core/config.py) (Pydantic BaseSettings).<br>2. Updated [`backend/app/main.py`](file:///backend/app/main.py) with dynamic CORS support for Chrome extensions (`settings.all_cors_origins`).<br>3. Installed `pytest` and created [`pytest.ini`](file:///pytest.ini).<br>4. Established unit test suite [`tests/test_unit_services.py`](file:///tests/test_unit_services.py). |
| **Phase D** | Database Schema & Safe Migrations | **COMPLETE** | 1. Created `UserVideo` model in [`backend/app/models/user_video.py`](file:///backend/app/models/user_video.py).<br>2. Updated `Video`, `User`, and `Conversation` models with `video_id` FK and relationships.<br>3. Created Alembic migration `d4f81a792e31` and applied to PostgreSQL via `alembic upgrade head`. |
| **Phase E** | Video Ingestion & RAG Reliability | **COMPLETE** | 1. Implemented canonical video reuse in [`backend/app/services/video_storage_service.py`](file:///backend/app/services/video_storage_service.py).<br>2. Built reference-counted safe deletion in `video_storage_service.delete_video` (preserves Qdrant vectors and canonical row until all referencing users/conversations are deleted). |
| **Phase F** | RESTful API Contracts & Compatibility | **COMPLETE** | 1. Added RESTful message endpoint `POST /conversations/{conversation_id}/messages` in [`backend/app/routers/conversations.py`](file:///backend/app/routers/conversations.py).<br>2. Added `POST /auth/refresh` in [`backend/app/routers/auth.py`](file:///backend/app/routers/auth.py) matching frontend auth client.<br>3. Added `GET /users/me` alias in [`backend/app/main.py`](file:///backend/app/main.py).<br>4. Added cross-video leakage validation to `POST /ask` and `POST /conversations/{id}/messages` (rejects mismatched queries with HTTP 400).<br>5. Retained 100% backward compatibility for existing React frontend `/ask` and `/videos` endpoints. |
| **Fix 1: Security** | Production Config Secret Key Safeguard | **COMPLETE** | Added `@model_validator` in [`app.core.config`](file:///backend/app/core/config.py) rejecting default, empty, or <32 character secret keys when `ENVIRONMENT` is production, while preserving convenient local dev default. Verified in [`tests/test_config.py`](file:///tests/test_config.py) (4/4 tests passed). |
| **Fix 2: Email** | Unconfigured SMTP Handling & Token Sanitization | **COMPLETE** | Added `is_configured` check to `send_password_reset_email` in [`app.services.email_service`](file:///backend/app/services/email_service.py); removed full verification/reset URLs from application logs. Verified in [`tests/test_email.py`](file:///tests/test_email.py) (2/2 tests passed). |
| **Fix 3: Auth** | Refresh Token Lifecycle & Type Boundaries | **COMPLETE** | Added distinct token types (`access` vs `refresh`), dual-mode `POST /auth/refresh` supporting dedicated JSON body rotation and active Bearer header renewal; enforced 401 on expired tokens and prohibited refresh tokens on API endpoints in [`app.auth.dependencies`](file:///backend/app/auth/dependencies.py). Verified in [`tests/test_auth.py`](file:///tests/test_auth.py) (14/14 tests passed). |
| **Fix 4: Ingestion** | Distributed PostgreSQL Advisory Locks | **COMPLETE** | Built [`app.services.lock_service.VideoIngestionLock`](file:///backend/app/services/lock_service.py) using `pg_try_advisory_lock` with SHA-256 derived 64-bit lock IDs. Integrated into `rag_service.process_video` and `process_video_background` with automatic release and error rollback. Verified in [`tests/test_concurrency.py`](file:///tests/test_concurrency.py) (7/7 tests passed). |
| **Fix 5: Migration** | Downgrade Safety & Disposable DB Verification | **COMPLETE** | Updated `d4f81a792e31` downgrade to backfill `videos.user_id` from `user_videos` and prune orphans before restoring `nullable=False`; used SQLite-safe batch operations. Verified upgrade -> downgrade -> re-upgrade cycle on disposable database in [`tests/test_migration.py`](file:///tests/test_migration.py) (1/1 test passed). |
| **Phase 2: Live AI** | Core AI Pipeline Live Verification | **COMPLETE** | Tested full pipeline against real dependencies (YouTube API, Qdrant Cloud cluster in AWS sa-east-1, Groq LLM `openai/gpt-oss-20b`, and live PostgreSQL). Verified 16/16 steps (100% pass rate). |
| **Phase 3: API Contracts** | API Contract Verification & Alignment | **COMPLETE** | Inspected all 17 REST endpoints, resolved `UserResponse` schema omission (`email_verified`, `created_at`), verified citation sources and confirmed no follow-up suggestions generated, added 8 contract regression tests (54/54 passed). |
| **Phase 4: Gmail SMTP** | SMTP Registration Diagnostics & Hardening | **COMPLETE** | Resolved Gmail SMTP handshake failure: sanitized Google 4x4 app password whitespace, enforced mutually exclusive TLS modes per port (465 vs 587), updated `AuthService.register_user` to permit retry for unverified users, and wrapped SMTP calls in HTTP 503 error handlers with zero credential leakage. Added 5 tests (59/59 passed). |
| **Phase 1 Final: Passwordless OTP** | Email OTP & Claude-style Login UI | **COMPLETE** | Added passwordless 6-digit OTP generation, SHA-256 hashing, rate limiting, and Alembic migration `a1b2c3d4e5f6`. Frontend Claude-style dark UI. Committed in `fdddc96`. Verified in [`tests/test_otp_auth.py`](file:///tests/test_otp_auth.py) and frontend unit tests. |
| **Phase 1 Final: Hardening & Vector Parity** | JWT Algorithm Lockdown & Qdrant Dimension Parity | **COMPLETE** | Added JWT algorithm validation (`HS256`, `HS384`, `HS512` whitelist), non-destructive vector dimension checks in `EmbeddingService` and `QdrantVectorStore`, and truthful GitHub support channels across legal pages. 158 backend tests passing. |
| **Commit 4: Legal & Footer** | Legal Pages and Shared Footer | **COMPLETE** | Committed `8165778`. Added Privacy, Terms, Disclaimer, Contact, Docs pages and shared Footer component with truthful disclosures on public GitHub issues. |
| **Commit 5: Frontend Core & Auth** | Shell, Routing & Password Reset | **COMPLETE** | Committed `5d19bcc`. Added `VerifyEmailPage`, `ResetPasswordPage`, dark-theme persistence, storage key migration, and clean 20/20 test pass (`npm --prefix frontend test`). |
| **Commit 6: Containerization** | Hardened Production Docker & Compose | **COMPLETE** | Committed `6bc1db7`. Multi-stage Python 3.12 Dockerfile with non-root user `ytgenius`, Debian-slim runtime with `libgomp1`, Linux `pywin32` exclusion, and loopback-bound Compose orchestration. Validated via `docker-compose config --quiet` (exit code 0). |
| **Phase 2: Docker & OAuth Hardening** | Host Port Resolution, OAuth Security & Full Regression | **COMPLETE** | 1. Built multi-stage backend container, verified non-root user `ytgenius`, PyTorch/SentenceTransformer imports, and Qdrant container startup.<br>2. Resolved host port 5432 conflict via `${POSTGRES_PORT:-5432}` parameterization in `docker-compose.yml`.<br>3. Hardened `GOOGLE_REDIRECT_URI` validation: enforced HTTPS, non-global IP rejection (`not ip.is_global or ip.is_multicast`), exact path `/auth/google/callback`, and bracket-aware empty/invalid port rejection.<br>4. Dynamic Compose callback port tracking `${PORT:-8000}` with test isolation.<br>5. Full backend regression passed: 182/182 tests across 21 test files in 58.78s; bytecode compilation passed cleanly. |

---

## 3. Phase 2: Live Core AI Pipeline Verification Findings

### Tested Environment:
- **YouTube API**: Live transcript and metadata retrieval for public video `jNQXAC9IVRw` ("Me at the zoo", 6 transcript segments).
- **Embeddings**: Live SentenceTransformer `all-MiniLM-L6-v2` generating 384-dimensional dense vectors.
- **Vector Database**: Real Qdrant Cloud cluster (`https://a6ee4c54-91fa-4739-a016-0e3b51b36fe4.sa-east-1-0.aws.cloud.qdrant.io`) collection `youtube_video_chunks`.
- **Reranker**: Live CrossEncoder `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- **LLM**: Live Groq Cloud API using `openai/gpt-oss-20b` (temperature 0.1).
- **Relational DB**: Live PostgreSQL (`youtube_qa_assistant` on localhost:5432).

### Step-by-Step Live Verification Results:

| # | Check / Step | Target Endpoint / Service | Observed Result & Metrics | Status |
|---|:---|:---|:---|:---:|
| 1 | Test User Setup | PostgreSQL User Table | Created dedicated User A (id=8) & User B (id=9) with verified status. | **PASS** |
| 2 | RAG Engine Startup | Lifespan Entry | Initialized real RAGService with local models and Qdrant Cloud in 16.14s. | **PASS** |
| 3 | Video Submission | `POST /videos/process` | Extracted `video_id=jNQXAC9IVRw`, returned `status='processing'` in 3.66s. | **PASS** |
| 4 | Background Ingestion | YouTube + SentenceTransformers + PostgreSQL | Extracted 6 segments, created 1 chunk, embedded and saved to DB in 2.66s. | **PASS** |
| 5 | Qdrant Cloud Storage | Qdrant Cloud AWS `sa-east-1` | 1 point indexed with payload (`text`, `start_time`, `end_time`, `video_id`). | **PASS** |
| 6 | Vector Semantic Search | Qdrant Vector Search | Retrieved 1 chunk for query "elephants" in 0.357s (Cosine score: 0.3745). | **PASS** |
| 7 | Cross-Encoder Rerank | CrossEncoder Model | Scored and reranked candidate in 0.054s (Rerank score: -4.8615). | **PASS** |
| 8 | Conversation Creation | `POST /conversations` | Created conversation id=10 bound to `video_id='jNQXAC9IVRw'`. | **PASS** |
| 9 | Live LLM Question 1 | `POST /conversations/{id}/messages` | Answered: *"The speaker discusses elephants and points out that they have really long trunks..."* in 1.35s with valid timestamp citation. | **PASS** |
| 10 | Contextual Follow-up | `POST /conversations/{id}/messages` | Successfully resolved ambiguous pronoun *"them"* to elephants; answered *"The cool thing about them is that they have really, really, really long trunks."* in 1.28s. | **PASS** |
| 11 | Legacy /ask Adapter | `POST /ask` | Answered: *"According to the transcript, the speaker is standing in front of the elephants at the zoo."* in 1.48s. | **PASS** |
| 12 | Unauthorized Access | `GET & POST /conversations/{id}` | User B access to User A conversation strictly rejected with `HTTP 404 Not Found`. | **PASS** |
| 13 | Cross-Video Isolation | `POST /conversations/{id}/messages` | Querying mismatched video inside bound conversation rejected with `HTTP 400 Bad Request`. | **PASS** |
| 14 | Canonical Video Reuse | `POST /videos/process` | User B linked to existing canonical record (`status='already_processed'`) without re-transcribing; User B cannot see User A chats. | **PASS** |
| 15 | Idempotent Submission | `POST /videos/process` | Repeated submission returns `already_processed`; no duplicate ingestion triggered. | **PASS** |
| 16 | Failed Video Handling | YouTube API & Video Storage | Video with unavailable transcript retried 3 times, marked `status='failed'`, never marked `processed`. | **PASS** |

### Data Cleanliness:
- All test vectors in Qdrant Cloud for `jNQXAC9IVRw` and `invalid_id_99999` were pruned upon test completion.
- All test users (ids 8, 9), test conversations, test messages, and test video metadata records in PostgreSQL were cleanly purged.
- No production or real user data was touched or modified.

---

## 4. Phase 3: Backend API Contract Verification Findings

### Summary:
- Inspected all 17 REST endpoints across Authentication, Videos, Conversations, Questions, and Health.
- Verified request and response schemas, Pydantic field validators, query parameters, and serialization behavior.
- Documented policy for Citations vs. Follow-up Suggestions: Citations (`sources`) are fully supported and returned; follow-up suggestions are intentionally not generated by the backend.
- Added comprehensive contract test suite [`tests/test_api_contracts.py`](file:///tests/test_api_contracts.py) covering 8 contract areas (all passed).
- Updated [`backend/app/schemas/auth.py`](file:///backend/app/schemas/auth.py) `UserResponse` model to serialize `email_verified` (bool) and `created_at` (datetime) from SQLAlchemy `User` models, fulfilling the documented contract.
- Verified clean error handling: 401 for unauthenticated/malformed tokens, 404 for missing/cross-user isolated resources, 405 for unsupported HTTP methods, 422 for malformed request bodies, with zero stack trace or secret disclosure.

---

## 5. Phase 4: Gmail SMTP Registration Diagnostics & Hardening

### Root Cause Analysis:
1. **Password Whitespace Format**: Google App Passwords display in four 4-character chunks separated by spaces (`xxxx xxxx xxxx xxxx`). Storing this verbatim in `.env` causes authentication and protocol stream issues with SMTP RFC/SASL implementations.
2. **Mutually Exclusive TLS Settings**: `fastapi_mail.ConnectionConfig` requires mutually exclusive TLS configurations (`MAIL_STARTTLS` vs `MAIL_SSL_TLS`). Simultaneous `True` flags or port mismatches (such as port 465 with `MAIL_STARTTLS=True` or port 587 with `MAIL_SSL_TLS=True`) cause stream resets or `Unexpected EOF received` during TLS negotiation.
3. **Registration Transaction Limbo**: If verification email delivery failed after user insertion, the user row remained committed with `email_verified=False`. Subsequent registration attempts were rejected with `ValueError("Email is already registered.")`, locking the user out permanently.
4. **Unhandled Exceptions**: SMTP transport failures (`ConnectionErrors`) bubbled up as unhandled HTTP 500 exceptions instead of being communicated cleanly to the caller.

### Key Changes Implemented:
1. **[`backend/app/services/email_service.py`](file:///backend/app/services/email_service.py)**:
   - Sanitized `MAIL_PASSWORD` by stripping all whitespace and spaces (`raw_password.strip().replace(" ", "")`).
   - Cleaned leading/trailing whitespace from `MAIL_USERNAME`, `MAIL_FROM`, and `MAIL_SERVER`.
   - Enforced port-appropriate TLS protocol flags automatically:
     - Port 465: `MAIL_SSL_TLS=True, MAIL_STARTTLS=False`
     - Port 587: `MAIL_STARTTLS=True, MAIL_SSL_TLS=False`
2. **[`backend/app/services/auth_service.py`](file:///backend/app/services/auth_service.py)**:
   - Updated `register_user` to detect existing unverified users (`email_verified == False`) and allow them to re-register with updated credentials, invalidating old unused verification tokens and generating a fresh token.
   - Strictly preserved duplicate prevention for verified accounts (`email_verified == True`).
3. **[`backend/app/routers/auth.py`](file:///backend/app/routers/auth.py)**:
   - Wrapped `email_service.send_email_verification` in `register_user` and `resend_verification` with explicit `try...except (ConnectionErrors, Exception)` blocks.
   - Return clean `HTTP 503 Service Unavailable` with informative error messages.
   - Logged failure reason without echoing secrets, credentials, or verification tokens.
4. **Automated Test Coverage**:
   - [`tests/test_email.py`](file:///tests/test_email.py): Added tests for password whitespace sanitization, TLS mode per port, and exception propagation.
   - [`tests/test_auth.py`](file:///tests/test_auth.py): Added tests for SMTP failure returning 503, user record persistence as unverified, successful unverified re-registration, rejection of verified accounts, and `test_real_registration_to_verification_flow` proving that dynamic 32-byte tokens are generated, stored as SHA-256 hashes, received by the email service, and verified by the backend.
   - Full regression suite: **60/60 tests passing (100%)**.

### Verification of Registration-to-Verification Flow:
- **Investigation of `test_token_123`**: Direct inspection of session execution logs confirmed that the email containing `token=test_token_123` was dispatched by a diagnostic test script executed during SMTP connection diagnosis (step 2650), **not** by the `POST /auth/register` endpoint.
- **Dynamic Token Verification**: `POST /auth/register` creates a 32-byte cryptographic token via `secrets.token_urlsafe(32)` (length >= 40), commits its SHA-256 hash to `email_verification_tokens`, and passes the dynamic URL `http://localhost:3000/verify-email?token=<token>` to `EmailService`.
- **Backend Acceptance**: `GET /auth/verify-email?token=<token>` accepts the dynamic token, sets `user.email_verified=True`, marks `used_at=now`, and rejects reused or hardcoded test tokens with HTTP 400.

---

## 6. Phase 5: YouTube Video Ingestion Cloud Timeout & Batching Hardening

### Root Cause Analysis (Video `aZglGvBPQGs`):
1. **Unbatched Upserts**: `QdrantVectorStore.add_documents` attempted to upload all vector points in a single unbatched HTTP request. For video `aZglGvBPQGs`, this was 84 384-dimensional dense vectors with metadata payloads.
2. **QdrantClient Default Timeout (5.0s)**: `QdrantVectorStore.__init__` initialized `QdrantClient(url=..., api_key=...)` without an explicit `timeout` argument. The underlying `httpx.Client` defaulted to a 5.0-second write/read timeout.
3. **Network Latency & Timeout**: The remote Qdrant Cloud cluster is hosted in AWS `sa-east-1` (São Paulo, Brazil). Transmitting and indexing 84 vector payloads across international network latency exceeded 5.0s, raising `ResponseHandlingException: The write operation timed out`.
4. **Exception Swallowing in Logs**: In `RAGService.process_video_background`, the exception was caught with `except Exception as error:` and only printed to stdout via `print(f"Video processing failed: {error}")`, omitting the full traceback and logging context.
5. **Database Consistency**: The background task pruned partial vectors and correctly set `video.status = 'failed'` with `segments=0` and `chunks=0` in the database, preventing stale or broken vector records.

### Key Changes Implemented:
1. **[`backend/app/services/qdrant_service.py`](file:///backend/app/services/qdrant_service.py)**:
   - Added `timeout: float = 60.0` parameter to `QdrantVectorStore.__init__`, explicitly passed to `QdrantClient(url=..., api_key=..., timeout=timeout)`.
   - Updated `add_documents(embeddings, chunks, batch_size: int = 64)` to upsert points in bounded batches (`points[i : i + batch_size]`). This guarantees that payloads stay small and do not hit connection or payload limits on videos of any duration.
2. **[`backend/app/services/rag_service.py`](file:///backend/app/services/rag_service.py)**:
   - Initialized `logger = logging.getLogger(__name__)`.
   - Replaced stdout `print` with `logger.error("Video processing failed for %s: %s", video_id, error, exc_info=True)` to record full tracebacks.
   - Wrapped vector cleanup (`vector_store.delete_video`) and database status update (`video_storage.create_or_update_video`) in separate defensive `try...except` blocks so a cleanup failure cannot prevent updating the status to `failed`.
3. **Automated Test Coverage**:
   - [`tests/test_videos.py`](file:///tests/test_videos.py):
     - `test_qdrant_add_documents_batching_and_timeout`: verifies that `QdrantVectorStore` configures a 60s timeout and batches upserts into chunks of at most 64.
     - `test_rag_process_video_background_timeout_failure_handling`: verifies that write timeouts are logged and safely transition video status to `failed`.
     - `test_failed_video_can_be_retried`: verifies that calling `process_video` on an existing failed video updates status to `processing` and re-dispatches background ingestion.
   - Full automated test suite: **63/63 tests passing (100%)**.
4. **Live Verification**:
   - Re-processed YouTube video `aZglGvBPQGs` ("Jev Course – Prefill-Only Inference & Decision Models from Scratch") live against PostgreSQL and Qdrant Cloud.
   - Ingestion completed successfully:
     - 2,295 segments formatted.
     - 84 chunks created.
     - 84 vectors generated and uploaded across 2 batches (64 + 20) with 0 timeouts.
     - Video status in database updated to `processed` (`segments=2295`, `chunks=84`).
   - Verified end-to-end RAG question answering: retrieved relevant chunks, reranked with cross-encoder, and generated accurate context-grounded response via Groq LLM API.

---

## 7. Known Limitations & Operational Bounds

1. **Process-Local Rate Limiting**:
   - The sliding-window rate limiter (`app.core.rate_limiter.RateLimiter`) uses an in-memory dictionary.
   - It is process-local and is **not distributed** across multiple Uvicorn workers or container replicas.
   - Distributed cluster-wide rate limiting requires a centralized store such as Redis.
2. **Docker Runtime Verification & Host Port Boundaries**:
   - Multi-stage Docker image build and static Compose configuration passed (`docker-compose config --quiet`, exit code `0`).
   - Host PostgreSQL port is parameterized via `${POSTGRES_PORT:-5432}` to avoid conflicts with native PostgreSQL instances.
   - Container verification confirmed non-root user `ytgenius`, runtime dependencies, and local Qdrant startup.
3. **Qdrant Collection Initialization on Boot**:
   - `QdrantVectorStore.create_collection` catches errors during startup and logs a warning so backend boot is not blocked if Qdrant is still spinning up.
   - It does **not automatically retry** collection creation on subsequent user queries; manual restart or subsequent API trigger is required if initial boot failed.
4. **Qdrant Query Retries**:
   - Ingestion (`add_documents`) implements a 3-attempt retry loop with linear backoff.
   - However, query-time search (`search()`) has **no internal retry loop**; transient network timeouts propagate directly to the API handler.
5. **Multi-Worker PyTorch Memory Allocation**:
   - Running Uvicorn with 4 worker processes (`--workers 4`) creates 4 independent PyTorch + SentenceTransformer model instances in memory.
   - Container environments should be allocated at least 2GB–3GB RAM to avoid Out-Of-Memory (OOM) termination.
6. **Deferred Browser Extension**:
   - The repository provides CORS regex whitelisting (`chrome-extension://*`) and unified REST endpoints.
   - However, the Chrome Extension package itself remains **deferred** and is not bundled or implemented in the current repository scope.
7. **Real Google OAuth End-to-End Authentication Boundary**:
   - While OAuth redirect URI configuration validation, token redirection logic, and state verification pass automated unit and integration tests, **real Google OAuth end-to-end authentication using actual Google credentials has not been verified** against live Google accounts. Automated tests with simulated responses are not equivalent to a real production OAuth login.
8. **Backend Linting**:
   - Backend linting was **NOT RUN — tool unavailable** because backend lint tools (`ruff`, `flake8`, `black`, `mypy`) are not installed or configured in the project's virtual environment.



