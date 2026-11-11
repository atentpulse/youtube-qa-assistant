# YtGenius 2.0 — API Contracts & Integration Guide

All authenticated endpoints require an `Authorization: Bearer <access_token>` header unless explicitly marked public.

---

## 1. Authentication Endpoints

### 1.1 Register User
- **Method**: `POST`
- **Path**: `/auth/register`
- **Auth**: Public
- **Request Body**:
  ```json
  {
    "username": "alex",
    "email": "alex@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "id": 1,
    "username": "alex",
    "email": "alex@example.com",
    "email_verified": false,
    "created_at": "2026-11-01T23:00:00Z"
  }
  ```

### 1.2 Login User
- **Method**: `POST`
- **Path**: `/auth/login`
- **Auth**: Public
- **Request Body**:
  ```json
  {
    "email": "alex@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

### 1.3 Refresh Access Token
- **Method**: `POST`
- **Path**: `/auth/refresh`
- **Auth**: Flexible (Supports both standard body refresh and Bearer header renewal)
- **Request Body** (Option A — Dedicated Refresh Token Body):
  ```json
  {
    "refresh_token": "eyJhbGciOi..."
  }
  ```
- **Request Body** (Option B — Active Bearer Header renewal for React Web App):
  ```json
  {}
  ```
  *(with header `Authorization: Bearer <active_access_token>`)*
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```
- **Error Responses**:
  - `401 Unauthorized`: Token expired, tampered signature, or invalid token type (e.g. attempting to use access token in dedicated refresh body, or refresh token directly on protected API endpoints).
```

### 1.4 Get Current User Profile
- **Method**: `GET`
- **Path**: `/auth/me` (Alias: `/users/me`)
- **Auth**: Required (`Bearer <access_token>`)
- **Response** (`200 OK`):
  ```json
  {
    "id": 1,
    "username": "alex",
    "email": "alex@example.com",
    "email_verified": true,
    "created_at": "2026-11-01T23:00:00Z"
  }
  ```

### 1.5 Send Passwordless Email OTP
- **Method**: `POST`
- **Path**: `/auth/otp/send`
- **Auth**: Public (Rate-limited via sliding window)
- **Request Body**:
  ```json
  {
    "email": "alex@example.com"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "message": "Verification code sent to your email.",
    "cooldown": 60
  }
  ```

### 1.6 Verify Passwordless Email OTP
- **Method**: `POST`
- **Path**: `/auth/otp/verify`
- **Auth**: Public (Rate-limited: maximum 5 attempts per OTP)
- **Request Body**:
  ```json
  {
    "email": "alex@example.com",
    "otp": "123456"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

### 1.7 Google OAuth Authorization & Exchange
- **Initiate Flow**: `GET /auth/google/login` (Redirects to Google OAuth consent screen)
- **Callback**: `GET /auth/google/callback` (Validates Google identity, issues short-lived single-use code to frontend `/oauth/callback?code=...`)
- **Token Exchange**: `POST /auth/oauth/exchange`
  - **Request Body**: `{ "code": "<single-use-code>" }`
  - **Response** (`200 OK`): `TokenResponse` (`access_token`, `refresh_token`, `token_type`)

### 1.8 Logout
- **Method**: `POST`
- **Path**: `/auth/logout`
- **Auth**: Required (`Bearer <access_token>`)
- **Response** (`200 OK`):
  ```json
  {
    "message": "Successfully logged out. All sessions invalidated."
  }
  ```

### 1.9 Verify Email Token
- **Method**: `GET`
- **Path**: `/auth/verify-email?token=<token>`
- **Auth**: Public
- **Query Parameters**:
  - `token` (string, required): 32-byte URL-safe cryptographic token dispatched via verification email.
- **Response** (`200 OK`):
  ```json
  {
    "message": "Email verified successfully."
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Token invalid, expired (30-minute validity), or already consumed (`used_at` set).

### 1.10 Resend Verification Email
- **Method**: `POST`
- **Path**: `/auth/resend-verification`
- **Auth**: Public (Rate-limited via sliding window)
- **Request Body**:
  ```json
  {
    "email": "alex@example.com"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "message": "If an unverified account exists for this email, a verification link has been sent."
  }
  ```
  *(Generic timing-resistant response returned regardless of account existence or verification state.)*

### 1.11 Forgot Password
- **Method**: `POST`
- **Path**: `/auth/forgot-password`
- **Auth**: Public (Rate-limited via sliding window)
- **Request Body**:
  ```json
  {
    "email": "alex@example.com"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "message": "If an account exists for this email, a password reset link has been sent."
  }
  ```
  *(Timing-resistant response; generates SHA-256 hashed 30-minute token and dispatches reset URL.)*

### 1.12 Reset Password
- **Method**: `POST`
- **Path**: `/auth/reset-password`
- **Auth**: Public (Rate-limited via sliding window)
- **Request Body**:
  ```json
  {
    "token": "dGVzdC10b2tlbg...",
    "new_password": "NewSecurePassword123!"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "message": "Password reset successfully."
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Invalid/expired token, consumed token, or password under 6 characters.

### 1.13 Update Current User Profile
- **Method**: `PATCH`
- **Path**: `/auth/me`
- **Auth**: Required (`Bearer <access_token>`)
- **Request Body**:
  ```json
  {
    "username": "alex_updated"
  }
  ```
- **Response** (`200 OK`): `UserResponse` (`id`, `username`, `email`, `email_verified`, `created_at`)

### 1.14 Delete Current User Account
- **Method**: `DELETE`
- **Path**: `/auth/me`
- **Auth**: Required (`Bearer <access_token>`)
- **Response** (`200 OK`):
  ```json
  {
    "message": "Account deleted successfully."
  }
  ```
  *(Performs reference-counted cleanup of user's videos via `rag_service.delete_video` and deletes user record with cascading token removal. Note: currently accessible via API; user-facing frontend deletion UI remains a future roadmap item.)*

---

## 2. Video Endpoints

### 2.1 Process Video
- **Method**: `POST`
- **Path**: `/videos/process`
- **Auth**: Required
- **Request Body**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "force_reprocess": false
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "video_id": "dQw4w9WgXcQ",
    "segments": 0,
    "chunks": 0,
    "status": "processing"
  }
  ```
  *(If video was already processed by another user or previously by the current user, returns `status: "already_processed"` with segment/chunk counts immediately without reprocessing.)*

### 2.2 Get User Video Library
- **Method**: `GET`
- **Path**: `/videos?limit=10&offset=0&status=processed`
- **Auth**: Required
- **Response** (`200 OK`):
  ```json
  {
    "videos": [
      {
        "video_id": "dQw4w9WgXcQ",
        "title": "Rick Astley - Never Gonna Give You Up",
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "status": "processed",
        "segments": 42,
        "chunks": 14,
        "created_at": "2026-11-01T23:10:00Z",
        "updated_at": "2026-11-01T23:11:00Z"
      }
    ],
    "total": 1
  }
  ```

### 2.3 Get Video Status
- **Method**: `GET`
- **Path**: `/videos/{video_id}/status`
- **Auth**: Required
- **Response** (`200 OK`):
  ```json
  {
    "video_id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up",
    "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    "status": "processed",
    "segments": 42,
    "chunks": 14
  }
  ```

### 2.4 Delete Video (Reference-Counted Safe Deletion)
- **Method**: `DELETE`
- **Path**: `/videos/{video_id}`
- **Auth**: Required
- **Response** (`200 OK`):
  ```json
  {
    "status": "deleted",
    "video_id": "dQw4w9WgXcQ"
  }
  ```

---

## 3. Conversation & Message Endpoints (RESTful YtGenius 2.0)

### 3.1 Create Conversation
- **Method**: `POST`
- **Path**: `/conversations`
- **Auth**: Required
- **Request Body**:
  ```json
  {
    "title": "Discussion on Quantum Computing",
    "video_id": "dQw4w9WgXcQ"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "id": 10,
    "title": "Discussion on Quantum Computing",
    "video_id": "dQw4w9WgXcQ",
    "created_at": "2026-11-01T23:15:00Z",
    "updated_at": "2026-11-01T23:15:00Z"
  }
  ```

### 3.2 List Conversations
- **Method**: `GET`
- **Path**: `/conversations` (Optional filter: `/conversations?video_id=dQw4w9WgXcQ`)
- **Auth**: Required
- **Response** (`200 OK`):
  ```json
  [
    {
      "id": 10,
      "title": "Discussion on Quantum Computing",
      "video_id": "dQw4w9WgXcQ",
      "created_at": "2026-11-01T23:15:00Z",
      "updated_at": "2026-11-01T23:15:00Z"
    }
  ]
  ```

### 3.3 Send Conversation Message (Canonical RESTful Route)
- **Method**: `POST`
- **Path**: `/conversations/{conversation_id}/messages`
- **Auth**: Required
- **Request Body**:
  ```json
  {
    "content": "What was the conclusion in the video?",
    "video_id": "dQw4w9WgXcQ"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "id": 55,
    "conversation_id": 10,
    "role": "assistant",
    "content": "The conclusion of the video highlights...",
    "sources": [
      {
        "start_time": 120.5,
        "end_time": 155.0,
        "start_time_formatted": "02:00",
        "end_time_formatted": "02:35",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120s",
        "score": 0.89
      }
    ],
    "created_at": "2026-11-01T23:16:00Z"
  }
  ```

### 3.4 Get Conversation Messages
- **Method**: `GET`
- **Path**: `/conversations/{conversation_id}/messages?limit=20&before_id=55`
- **Auth**: Required
- **Response** (`200 OK`):
  ```json
  {
    "messages": [
      {
        "id": 54,
        "role": "user",
        "content": "What was the conclusion in the video?",
        "created_at": "2026-11-01T23:15:58Z"
      },
      {
        "id": 55,
        "role": "assistant",
        "content": "The conclusion of the video highlights...",
        "created_at": "2026-11-01T23:16:00Z"
      }
    ],
    "next_cursor": null
  }
  ```

---

## 4. Backward Compatibility Adapter Route

### 4.1 Ask Question (Legacy Web App Adapter)
- **Method**: `POST`
- **Path**: `/ask`
- **Auth**: Required
- **Request Body**:
  ```json
  {
    "video_id": "dQw4w9WgXcQ",
    "question": "Summarize the key points.",
    "conversation_id": 10
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "answer": "Here is the summary...",
    "sources": [
      {
        "start_time": 10.0,
        "end_time": 45.0,
        "start_time_formatted": "00:10",
        "end_time_formatted": "00:45",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s",
        "score": 0.94
      }
    ],
    "conversation_id": 10
  }
  ```
  *(If `conversation_id` is omitted, auto-creates a new conversation bound to `video_id`.)*

---

## 5. Citations, Suggestions & Verification Matrix

### 5.1 Citations vs. Follow-up Suggestions Policy
- **Citations (`sources`)**: **Supported & Verified**. Both `POST /conversations/{conversation_id}/messages` and `POST /ask` return a `sources` array containing chunk citations with `start_time`, `end_time`, `start_time_formatted`, `end_time_formatted`, `url`, and `score`.
- **Follow-up Suggestions**: **Not Supported**. Neither the backend schemas (`SendMessageResponse`, `AskQuestionResponse`) nor `RAGService` generate or return suggested follow-up questions. Clients must not depend on a `suggestions` or `follow_up_questions` field.

### 5.2 API Verification & Contract Audit Matrix

| Endpoint | Method | Auth | Primary Success Schema | Verified By | Status |
| :--- | :---: | :---: | :--- | :--- | :---: |
| `/auth/register` | `POST` | Public | `UserResponse` (`id`, `username`, `email`, `email_verified`, `created_at`) | Automated tests + source inspection | **VERIFIED** |
| `/auth/login` | `POST` | Public | `TokenResponse` (`access_token`, `refresh_token`, `token_type`) | Automated tests + source inspection | **VERIFIED** |
| `/auth/otp/send` | `POST` | Public | `SendOTPResponse` (`message`, `cooldown`) | Automated tests + source inspection | **VERIFIED** |
| `/auth/otp/verify` | `POST` | Public | `TokenResponse` (`access_token`, `refresh_token`, `token_type`) | Automated tests + source inspection | **VERIFIED** |
| `/auth/google/login` | `GET` | Public | `307 Temporary Redirect` (Google consent) | Automated tests + source inspection | **VERIFIED** |
| `/auth/google/callback` | `GET` | Public | `307 Temporary Redirect` (Single-use exchange code) | Automated tests + source inspection | **VERIFIED** |
| `/auth/oauth/exchange` | `POST` | Public | `TokenResponse` (`access_token`, `refresh_token`, `token_type`) | Automated tests + source inspection | **VERIFIED** |
| `/auth/verify-email` | `GET` | Public | `{"message": "Email verified successfully."}` | Automated tests + source inspection | **VERIFIED** |
| `/auth/resend-verification` | `POST` | Public | `{"message": "If an unverified account exists..."}` (Timing-resistant) | Automated tests + source inspection | **VERIFIED** |
| `/auth/forgot-password` | `POST` | Public | `{"message": "If an account exists..."}` (Timing-resistant) | Automated tests + source inspection | **VERIFIED** |
| `/auth/reset-password` | `POST` | Public | `{"message": "Password reset successfully."}` | Automated tests + source inspection | **VERIFIED** |
| `/auth/logout` | `POST` | Bearer | `{"message": "Successfully logged out..."}` | Automated tests + source inspection | **VERIFIED** |
| `/auth/refresh` | `POST` | Flexible | `TokenResponse` (Dedicated body or active Bearer renewal) | Automated tests + source inspection | **VERIFIED** |
| `/auth/me` | `GET` | Bearer | `UserResponse` | Automated tests + source inspection | **VERIFIED** |
| `/auth/me` | `PATCH`| Bearer | `UserResponse` (Username update) | Automated tests + source inspection | **VERIFIED** |
| `/auth/me` | `DELETE`| Bearer| `{"message": "Account deleted successfully."}` (Safe cascade) | Automated tests + source inspection | **VERIFIED** |
| `/users/me` | `GET` | Bearer | `UserResponse` (Alias) | Automated tests + source inspection | **VERIFIED** |
| `/videos/process` | `POST` | Bearer | `ProcessVideoResponse` (`video_id`, `status`, `segments`, `chunks`) | Automated tests + Live Phase 2 verification | **VERIFIED** |
| `/videos/{id}/status` | `GET` | Bearer | `VideoStatusResponse` | Automated tests + Live Phase 2 verification | **VERIFIED** |
| `/videos` | `GET` | Bearer | `VideoListResponse` (`videos`, `total`) | Automated tests + source inspection | **VERIFIED** |
| `/videos/{id}` | `DELETE`| Bearer | `{"status": "deleted", "video_id": "..."}` (Safe ref-counted) | Automated tests + source inspection | **VERIFIED** |
| `/conversations` | `POST` | Bearer | `ConversationResponse` (`id`, `title`, `video_id`, timestamps) | Automated tests + Live Phase 2 verification | **VERIFIED** |
| `/conversations` | `GET` | Bearer | `list[ConversationResponse]` (Supports optional `?video_id=`) | Automated tests + source inspection | **VERIFIED** |
| `/conversations/{id}` | `GET` | Bearer | `ConversationDetailResponse` (`messages: list[MessageResponse]`) | Automated tests + source inspection | **VERIFIED** |
| `/conversations/{id}/messages` | `GET` | Bearer | `PaginatedMessagesResponse` (`messages`, `next_cursor`) | Automated tests + source inspection | **VERIFIED** |
| `/conversations/{id}/messages` | `POST` | Bearer | `SendMessageResponse` (`id`, `role`, `content`, `sources`, `created_at`) | Automated tests + Live Phase 2 verification | **VERIFIED** |
| `/conversations/{id}` | `PATCH`| Bearer | `ConversationResponse` (Rename title) | Automated tests + source inspection | **VERIFIED** |
| `/conversations/{id}` | `DELETE`| Bearer | `{"message": "Conversation deleted successfully."}` | Automated tests + source inspection | **VERIFIED** |
| `/ask` | `POST` | Bearer | `AskQuestionResponse` (`answer`, `sources`, `conversation_id`) | Automated tests + Live Phase 2 verification | **VERIFIED** |
| `/health` | `GET` | Public | `{"status": "healthy"}` | Automated tests + source inspection | **VERIFIED** |
| `/health/live` | `GET` | Public | `{"status": "ok"}` (Liveness probe) | Automated tests + source inspection | **VERIFIED** |
| `/health/ready`| `GET` | Public | `{"status": "ready", "checks": {...}}` (Readiness probe) | Automated tests + source inspection | **VERIFIED** |
| `/` | `GET` | Public | `{"message": "YouTube Video Q&A Assistant API", "version": "2.0.0"}` | Automated tests + source inspection | **VERIFIED** |

---

### 5.3 Health Probes & Monitoring Architecture

The backend distinguishes process liveness from external service readiness:
1. **Liveness Probe (`GET /health/live`)**:
   - Lightweight endpoint returning `200 OK` (`{"status": "ok"}`).
   - Asserts that the Python process and Uvicorn event loop are responsive.
   - Used by Docker container `HEALTHCHECK` and Kubernetes liveness probes. Does not query external network dependencies, preventing transient network hiccups from killing healthy containers.
2. **Readiness Probe (`GET /health/ready`)**:
   - Actively checks database (`SELECT 1`) and Qdrant cluster (`client.get_collections()`).
   - Returns `200 OK` (`{"status": "ready", "checks": {"database": "ok", "qdrant": "ok"}}`) when all dependencies respond.
   - Returns `503 Service Unavailable` (`{"status": "unhealthy", "checks": {...}}`) if any dependency is unreachable.
   - Used by load balancers and orchestrators to control traffic ingress without restarting the container.
3. **General Ping (`GET /health`)**:
   - Standard HTTP ping returning `200 OK` (`{"status": "healthy"}`).
