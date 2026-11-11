# YtGenius 2.0 — Test Suite & Verification Guide

## 1. Test Architecture

The test suite covers end-to-end functionality, security controls, API contracts, concurrency, RAG pipeline correctness, migrations, and frontend UI behaviors:

### Backend Test Suites (`tests/`):

| Test Suite | Purpose | Target Endpoints / Components |
| :--- | :--- | :--- |
| `tests/test_unit_services.py` | Unit tests for pure algorithmic services | YouTube ID extraction, word-based chunking, timestamp formatters |
| `tests/test_auth.py` | Authentication, token lifecycle, password recovery | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`, `/users/me`, `/auth/forgot-password`, `/auth/reset-password` |
| `tests/test_otp_auth.py` | Passwordless Email OTP authentication | `/auth/otp/send`, `/auth/otp/verify`, rate limiting, attempt bounds |
| `tests/test_auth_security.py` | Token tampering, invalid signatures, enumeration | Security boundaries, timing resistance, token versions |
| `tests/test_config.py` | Settings & validator enforcement | `SECRET_KEY` strength, `ALGORITHM` validation (`HS256/384/512`), Google OAuth redirect URI production HTTPS validation, non-global IP & multicast rejection, empty/invalid port checks, Docker Compose port interpolation (35 tests) |
| `tests/test_cors.py` | CORS policy validation & origin whitelisting | Web client origins, untrusted domain rejection, Chrome extensions |
| `tests/test_concurrency.py` | Distributed PostgreSQL advisory locks | Single-worker ingestion lock, lock ID hashing, retry handling |
| `tests/test_videos.py` | Video processing, multi-user reuse, safe deletion | `/videos/process`, `/videos`, `/videos/{id}/status`, `DELETE /videos/{id}`, canonical reuse |
| `tests/test_shared_video_deletion.py` | Reference-counted multi-tenant deletion | Zero-reference purge vs non-zero reference preservation |
| `tests/test_conversations.py` | Conversation lifecycle, RESTful messaging, leak prevention | `/conversations`, `/conversations/{id}/messages`, `POST /ask` adapter, cross-video validation |
| `tests/test_qdrant_consistency.py` | Vector store compatibility & dimension checks | SentenceTransformer dimension introspection, collection dimension verification |
| `tests/test_api_contracts.py` | Schema parity & contract enforcement | Pydantic response models, HTTP status codes, error payload schemas |
| `tests/test_health_probes.py` | Health and readiness monitoring | `/health`, `/` root endpoint, database ping |
| `tests/test_ingestion_reliability.py` | YouTube fetching & error handling | Transient error retries, transcript extraction failure recovery |
| `tests/test_rag_correctness.py` | Semantic search and prompt composition | Qdrant vector retrieval, context augmentation, LLM prompt bounds |
| `tests/test_cache_integrity.py` | Question-answering semantic caching | Question hashing, cache hit/miss behavior, cache eviction |
| `tests/test_postgresql_integrity.py` | Relational constraints & foreign keys | Cascades, nullability, unique constraints |
| `tests/test_migration.py` | Alembic migration cycle safety | Upgrade -> Downgrade -> Upgrade on disposable test database |
| `tests/test_email.py` | SMTP transport handling & log sanitization | Unconfigured SMTP safety, sensitive token log redaction |
| `tests/test_support.py` | Support and contact link integrity | Support issue links, external link target validation |
| `tests/test_e2e_workflow.py` | End-to-end integration lifecycle | Full user registration -> Login -> Video ingestion -> Discussion -> Q&A -> Token Refresh -> Cleanup |

### Frontend Test Suites (`frontend/tests/`):
- `frontend/tests/auth_and_theme.test.js`: Dark-only theme persistence, storage migration (`vidmind_*` -> `ytgenius_*`), OTP input interaction, token persistence, error message formatting (13 tests).
- `frontend/tests/oauth_callback.test.js`: Google OAuth code exchange, single-flight request promise deduplication, React StrictMode double-mount simulation, session navigation guards (7 tests).

---

## 2. Running the Test Suite

### Running All Automated Backend Tests:
```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

### Running Frontend Tests:
```powershell
npm --prefix frontend test
```
*(Executes Node native test runner `node --test tests/**/*.test.js` across both test files)*

### Running Frontend Linter and Production Build:
```powershell
cd frontend; npm run lint; npm run build; cd ..
```

### Running Docker Compose Static Validation:
```powershell
docker-compose config --quiet
```

### Running Python Environment Verification:
```powershell
.venv\Scripts\python.exe -m pip check
```

---

## 3. Verified Test Results

- **Backend Pytest Full Regression Suite**: **182 passed**, 0 failed, 7 warnings across 21 test files in 58.78s (100% pass rate).
  - All 35 tests in [`tests/test_config.py`](file:///tests/test_config.py) passed, verifying settings validators, production HTTPS callback enforcement, non-global IP/multicast rejection, empty/invalid port checks, and Docker Compose port interpolation.
  - All 17 tests in [`tests/test_auth.py`](file:///tests/test_auth.py) passed, including all 10 Google OAuth integration tests.
- **Python Bytecode Compilation**: Verified cleanly (`python -m py_compile backend/app/core/config.py tests/test_config.py`, exit code `0`).
- **Frontend Node Tests**: **20 passed**, 0 failed (100% pass rate in ~220ms across both test files).
- **ESLint (Frontend)**: Passed with **0 errors, 0 warnings**.
- **Frontend Build**: Vite production build succeeded cleanly (`built in 11.53s`, 1824 modules transformed).
- **Pip Check**: Passed cleanly with **"No broken requirements found"**.
- **Docker Container Build & Startup**: Dockerfile multi-stage build succeeded, validating the non-root `ytgenius` user, PyTorch/SentenceTransformer dependency imports, and Qdrant container startup. Static Compose configuration passed via `docker-compose config --quiet` (exit code `0`).

---

## 4. Verification Boundaries & Disclosed Limitations

- **Real Google OAuth End-to-End Verification**: Real Google OAuth authentication using actual Google credentials and live Google consent screens **has not been verified**. Automated tests execute with mock responses, token generation, state verification, and simulated redirect flows. Automated test passes are not equivalent to a real production OAuth login.
- **Backend Linting**: Backend linting was **NOT RUN — tool unavailable** because backend lint tools (`ruff`, `flake8`, `black`, `mypy`) are not installed or configured in the project virtual environment (`.venv\Scripts`).
- **Process-Local Rate Limiting**: The in-memory rate limiter is process-local and does not synchronize state across multi-worker Uvicorn processes or container replicas. Distributed rate limiting requires an external store (e.g. Redis).
