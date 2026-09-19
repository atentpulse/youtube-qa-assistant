import { apiClient } from "./client";

/**
 * Fetch the authenticated user's video library.
 */
export function getVideos(opts) {
  return apiClient.get("/videos", opts);
}

export const listVideos = getVideos;

/**
 * Submit a YouTube URL for processing (or re-processing).
 * Backend contract: POST /videos/process
 */
export function processVideo(arg, opts) {
  const { url, forceReprocess = false } =
    typeof arg === "string" ? { url: arg, forceReprocess: false } : arg || {};
  return apiClient.post(
    "/videos/process",
    { url, force_reprocess: forceReprocess },
    opts,
  );
}

/**
 * Fetch the current processing status of a specific video.
 * Backend contract: GET /videos/{video_id}/status
 */
export function getVideoStatus(videoId, opts) {
  return apiClient.get(`/videos/${videoId}/status`, opts);
}

/**
 * Delete a video from the library.
 * Backend contract: DELETE /videos/{video_id}
 */
export function deleteVideo(videoId, opts) {
  return apiClient.delete(`/videos/${videoId}`, opts);
}
