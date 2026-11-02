# VidMind 2.0 — Backend Test Suite & Verification Guide

## 1. Test Architecture

The backend test suite is organized into modular suites under `tests/`:

| Test Suite | Purpose | Target Endpoints / Components |
| :--- | :--- | :--- |
| `tests/test_unit_services.py` | Unit tests for pure algorithmic services | YouTube ID extraction, word-based chunking, timestamp formatters |
| `tests/test_auth.py` | Authentication, token lifecycle, password recovery | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`, `/users/me`, `/auth/forgot-password`, `/auth/reset-password` |
| `tests/test_cors.py` | CORS policy validation & origin whitelisting | Web client origins, untrusted domain rejection, Chrome extensions |
| `tests/test_videos.py` | Video processing, multi-user reuse, safe deletion | `/videos/process`, `/videos`, `/videos/{id}/status`, `DELETE /videos/{id}`, canonical reuse |
| `tests/test_conversations.py` | Conversation lifecycle, RESTful messaging, leak prevention | `/conversations`, `/conversations/{id}/messages`, `POST /ask` adapter, cross-video validation |
| `tests/test_e2e_workflow.py` | End-to-end integration lifecycle | Full user registration -> Login -> Video ingestion -> Discussion -> Q&A -> Token Refresh -> Cleanup |

---

## 2. Running the Test Suite

### Running All Automated Tests:
```powershell
$env:PYTHONPATH="backend"; .venv\Scripts\python.exe -m pytest tests/ -v
```

### Running Specific Test Suites:
```powershell
# Authentication tests
$env:PYTHONPATH="backend"; .venv\Scripts\python.exe -m pytest tests/test_auth.py -v

# Video and reference counting tests
$env:PYTHONPATH="backend"; .venv\Scripts\python.exe -m pytest tests/test_videos.py -v

# Conversation & message tests
$env:PYTHONPATH="backend"; .venv\Scripts\python.exe -m pytest tests/test_conversations.py -v

# End-to-end workflow test
$env:PYTHONPATH="backend"; .venv\Scripts\python.exe -m pytest tests/test_e2e_workflow.py -v
```

---

## 3. Verified Test Results

All 26 automated backend tests pass cleanly with 100% success rate:
- `test_register_success` PASSED
- `test_register_duplicate_email` PASSED
- `test_login_success` PASSED
- `test_login_invalid_password` PASSED
- `test_get_current_user_me` PASSED
- `test_get_users_me_alias` PASSED
- `test_refresh_token` PASSED
- `test_forgot_and_reset_password` PASSED
- `test_create_and_list_conversations` PASSED
- `test_send_conversation_message_restful` PASSED
- `test_prevent_cross_video_leakage_in_messages` PASSED
- `test_ask_backward_compatibility_and_video_binding` PASSED
- `test_update_and_delete_conversation` PASSED
- `test_cors_preflight_allowed_web_origin` PASSED
- `test_cors_preflight_rejected_origin` PASSED
- `test_cors_chrome_extension_origin` PASSED
- `test_complete_e2e_workflow` PASSED
- `test_extract_video_id` PASSED
- `test_split_text` PASSED
- `test_create_chunks` PASSED
- `test_time_utils` PASSED
- `test_process_video_endpoint` PASSED
- `test_canonical_video_multi_user_reuse` PASSED
- `test_reference_counted_safe_deletion` PASSED
- `test_get_video_status_endpoint` PASSED
- `test_list_videos_endpoint` PASSED
