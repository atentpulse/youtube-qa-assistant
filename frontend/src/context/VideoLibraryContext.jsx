import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { listVideos, processVideo as apiProcessVideo, deleteVideo as apiDeleteVideo } from '../api/videos';
import { useAuth } from './AuthContext';
import { VIDEO_STATUS } from '../utils/constants';

export const VideoLibraryContext = createContext(null);

export function VideoLibraryProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [videos, setVideos] = useState([]);
  const [selectedVideoId, setSelectedVideoId] = useState(null);
  const [libraryStatus, setLibraryStatus] = useState('idle'); // 'idle' | 'loading' | 'ready' | 'error'
  const [libraryError, setLibraryError] = useState(null);

  const fetchVideos = useCallback(async (isBackground = false) => {
    if (!isAuthenticated) {
      setVideos([]);
      setSelectedVideoId(null);
      setLibraryStatus('idle');
      return;
    }

    if (!isBackground) {
      setLibraryStatus('loading');
    }
    setLibraryError(null);
    try {
      const data = await listVideos();
      const list = Array.isArray(data) ? data : data?.videos || [];
      setVideos(list);
      setLibraryStatus('ready');
      setSelectedVideoId((prev) => {
        // Preserve the user's current selection only if it still exists.
        // Never auto-select the first (or any) video after login/refresh —
        // the user must explicitly choose a video from the library.
        if (prev && list.some((v) => v.video_id === prev)) {
          return prev;
        }
        return null;
      });
    } catch (err) {
      if (!isBackground) {
        setLibraryStatus('error');
      }
      setLibraryError(err?.message || 'Failed to load videos.');
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchVideos();
  }, [fetchVideos]);

  // Poll the library while any video is processing so ready/failed
  // states appear without a manual reload. Use background fetch to
  // avoid resetting libraryStatus to 'loading' and causing workspace flicker.
  useEffect(() => {
    if (!videos.some((v) => v.status === VIDEO_STATUS.PROCESSING)) return undefined;
    const interval = setInterval(() => {
      fetchVideos(true);
    }, 5000);
    return () => clearInterval(interval);
  }, [videos, fetchVideos]);

  const selectVideo = useCallback((videoId) => {
    setSelectedVideoId(videoId);
  }, []);

  const addVideo = useCallback(async (url) => {
    const res = await apiProcessVideo(url);
    const newVideo = res?.video || res;
    if (newVideo?.video_id) {
      setVideos((prev) => {
        const filtered = prev.filter((v) => v.video_id !== newVideo.video_id);
        return [newVideo, ...filtered];
      });
      setSelectedVideoId(newVideo.video_id);
    }
    return newVideo;
  }, []);

  const reprocessVideo = useCallback(async (videoId, url) => {
    const videoUrl = url || `https://www.youtube.com/watch?v=${videoId}`;
    const res = await apiProcessVideo({ url: videoUrl, forceReprocess: true });
    const updated = res?.video || res;
    if (updated?.video_id) {
      setVideos((prev) =>
        prev.map((v) => (v.video_id === updated.video_id ? updated : v))
      );
    }
    return updated;
  }, []);

  const removeVideo = useCallback(async (videoId) => {
    await apiDeleteVideo(videoId);
    setVideos((prev) => prev.filter((v) => v.video_id !== videoId));
    setSelectedVideoId((prev) => (prev === videoId ? null : prev));
  }, []);

  const updateVideoStatus = useCallback((videoId, status, details = {}) => {
    setVideos((prev) =>
      prev.map((v) =>
        v.video_id === videoId ? { ...v, status, ...details } : v
      )
    );
  }, []);

  const selectedVideo = videos.find((v) => v.video_id === selectedVideoId) || null;

  return (
    <VideoLibraryContext.Provider
      value={{
        videos,
        selectedVideoId,
        selectedVideo,
        libraryStatus,
        libraryError,
        fetchVideos,
        selectVideo,
        addVideo,
        reprocessVideo,
        removeVideo,
        updateVideoStatus,
      }}
    >
      {children}
    </VideoLibraryContext.Provider>
  );
}

export function useVideoLibrary() {
  const ctx = useContext(VideoLibraryContext);
  if (!ctx) {
    throw new Error('useVideoLibrary must be used within VideoLibraryProvider');
  }
  return ctx;
}
