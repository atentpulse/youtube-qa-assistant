# VidMind 2.0 — API Contracts & Integration Guide

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
  }
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

## 3. Conversation & Message Endpoints (RESTful VidMind 2.0)

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
| `/auth/refresh` | `POST` | Flexible | `TokenResponse` (Dedicated body or active Bearer renewal) | Automated tests + source inspection | **VERIFIED** |
| `/auth/me` | `GET` | Bearer | `UserResponse` | Automated tests + source inspection | **VERIFIED** |
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
| `/` | `GET` | Public | `{"message": "YouTube Video Q&A Assistant API", "version": "2.0.0"}` | Automated tests + source inspection | **VERIFIED** |
