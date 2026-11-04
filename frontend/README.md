# YtGenius — YouTube Video Q&A Assistant (Frontend)

A production-quality React (JavaScript) frontend for a RAG-based YouTube video
Q&A backend. Users add a YouTube link, wait for processing, then ask
questions and get answers with clickable, timestamped sources.

## Stack

- React 18 + Vite (plain JavaScript, no TypeScript)
- Plain CSS with CSS Modules (no UI framework, no Tailwind)
- No client-side state library beyond React context — the app is small
  enough that `useReducer` + Context covers it cleanly

## Getting started

```bash
npm install
cp .env.example .env   # then set VITE_API_BASE_URL to your backend
npm run dev
```

The app expects a FastAPI backend implementing the endpoints below and
reads its base URL from `VITE_API_BASE_URL` — nothing is hardcoded to
`localhost`.

## Backend contract

| Method | Path                      | Purpose                                   |
|--------|---------------------------|--------------------------------------------|
| GET    | `/`                       | Health / API info                          |
| POST   | `/process-video`          | `{ url, force_reprocess }` → process a video |
| GET    | `/videos`                 | Paginated video library, optional status filter |
| GET    | `/video/{video_id}/status`| Poll processing status for one video       |
| DELETE | `/video/{video_id}`       | Delete a video and its data                |
| POST   | `/ask`                    | `{ video_id, question }` → `{ answer, sources }` |
| GET    | `/health`                 | Backend health check                       |

## Project structure

```
src/
  api/            fetch wrappers, one file per resource (videos, questions, health)
  context/        app state: video library (+ polling), chat threads, toasts
  components/
    Sidebar/       branding, add-video form, search/filter, library list
    MainPanel/      empty state, video header, Q&A thread, message, sources
    common/         StatusDot, ConfirmDialog, Spinner
  utils/          formatters, YouTube URL parsing, shared constants
```

API calls are isolated in `src/api`; UI components never call `fetch`
directly. `VideoLibraryContext` owns the video list and automatically polls
`/video/{id}/status` every few seconds for any video stuck in `processing`,
stopping itself once the video is `processed`/`already_processed`/`failed`.
`ChatContext` keeps a separate Q&A thread per video in memory for the
session, so switching videos doesn't lose earlier answers.

## Notable UX decisions

- **Reprocessing is tucked into a "⋯" menu**, not a primary button, per the
  product brief — it's an available action, not the encouraged path.
- **Relevance scores are never shown** — sources are presented as plain
  timestamp ranges the user can click to jump to that moment on YouTube.
- **"No information found" is a distinct state**, not an error — it's
  detected from the answer content and rendered as a calm, helpful message.
- **Raw backend errors are never shown.** `src/api/client.js` maps HTTP
  status codes to plain-language copy; component code only ever sees
  `ApiError.message`.

## Build

```bash
npm run build
npm run preview
```
