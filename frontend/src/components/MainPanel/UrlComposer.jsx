import React, { useMemo, useState } from 'react';
import { ArrowRight, Link as LinkIcon, X, Film } from 'lucide-react';
import Spinner from '../common/Spinner';
import { useVideoLibrary } from '../../context/VideoLibraryContext';
import { useConversations } from '../../context/ConversationContext';
import { useUI } from '../../context/UIContext';
import { useToast } from '../../context/ToastContext';
import { ApiError } from '../../api/client';
import { VIDEO_STATUS } from '../../utils/constants';
import styles from './UrlComposer.module.css';

function extractYouTubeVideoId(url) {
  if (!url) return null;
  const str = url.trim();
  if (/^[a-zA-Z0-9_-]{11}$/.test(str)) {
    return str;
  }
  const regExp = /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
  const match = str.match(regExp);
  return match ? match[1] : null;
}

export default function UrlComposer({ variant = 'welcome', onClose }) {
  const [url, setUrl] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [infoMessage, setInfoMessage] = useState(null);

  const { videos, addVideo, selectVideo } = useVideoLibrary();
  const { createConversation, selectConversation, clearActiveConversation } = useConversations();
  const { closeComposer, composerMode = 'new_chat' } = useUI();
  const toast = useToast();

  const isPanel = variant === 'panel';
  const isAddVideoOnly = composerMode === 'add_video';
  const handleClose = onClose || closeComposer;

  // Ready library videos available for quick-start in new_chat mode
  const readyVideos = useMemo(() => {
    return videos.filter(
      (v) =>
        v.status === VIDEO_STATUS.PROCESSED ||
        v.status === VIDEO_STATUS.ALREADY_PROCESSED
    );
  }, [videos]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const clean = url.trim();
    if (!clean || isProcessing) return;

    setIsProcessing(true);
    setError(null);
    setInfoMessage(null);

    const extractedId = extractYouTubeVideoId(clean);

    try {
      // 1. Check whether video already exists in the user's accessible library
      const existingVideo = extractedId
        ? videos.find((v) => v.video_id === extractedId)
        : null;

      if (isAddVideoOnly) {
        // Section 6: Add Video Action (+ Add inside Video Library)
        if (existingVideo) {
          // Video already exists: Inform user and reuse existing record. Do NOT create conversation.
          toast.info(`"${existingVideo.title || 'Video'}" is already in your library.`);
          setInfoMessage('This video is already in your library.');
          selectVideo(existingVideo.video_id);
          setUrl('');
          handleClose();
          return;
        }

        // Process and add the video to Video Library without creating a conversation
        await addVideo(clean);
        toast.success('Video added to library.');
        setUrl('');
        handleClose();
      } else {
        // Section 5: Global New Chat Button
        if (existingVideo) {
          // Video exists: Reuse record, do not re-ingest, create a new conversation for it
          selectVideo(existingVideo.video_id);

          if (
            existingVideo.status === VIDEO_STATUS.PROCESSED ||
            existingVideo.status === VIDEO_STATUS.ALREADY_PROCESSED
          ) {
            const newConv = await createConversation('New Chat', existingVideo.video_id);
            selectConversation(newConv.id);
          } else {
            clearActiveConversation();
          }

          setUrl('');
          handleClose();
          return;
        }

        // Ingest new video
        const newVideo = await addVideo(clean);
        selectVideo(newVideo?.video_id || extractedId);

        if (
          newVideo?.status === VIDEO_STATUS.PROCESSED ||
          newVideo?.status === VIDEO_STATUS.ALREADY_PROCESSED
        ) {
          const newConv = await createConversation('New Chat', newVideo.video_id);
          selectConversation(newConv.id);
        } else {
          clearActiveConversation();
        }

        setUrl('');
        handleClose();
      }
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Could not process this video. Please check the URL and try again.'
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handlePickExistingVideo = async (video) => {
    try {
      selectVideo(video.video_id);
      const newConv = await createConversation('New Chat', video.video_id);
      selectConversation(newConv.id);
      handleClose();
    } catch (err) {
      setError('Could not start conversation for this video.');
    }
  };

  return (
    <form
      className={`${styles.composer} ${isPanel ? styles.composerPanel : styles.composerWelcome}`}
      onSubmit={handleSubmit}
      data-testid="video-url-composer"
    >
      {isPanel && (
        <div className={styles.panelHeader}>
          <h2 className={styles.panelTitle}>
            {isAddVideoOnly ? 'Add a YouTube Video' : 'Start a New Chat'}
          </h2>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={handleClose}
            aria-label="Close"
            data-testid="composer-close-button"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {isPanel && (
        <p className={styles.panelSubtitle}>
          {isAddVideoOnly
            ? 'Add a YouTube video to your library without creating a conversation.'
            : 'Enter a YouTube video URL or select an existing video to start a fresh conversation.'}
        </p>
      )}

      <div className={styles.inputWrap}>
        <LinkIcon size={18} className={styles.icon} />
        <input
          type="text"
          className={styles.input}
          placeholder="Paste YouTube video URL (e.g. https://www.youtube.com/watch?v=...)"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (error) setError(null);
            if (infoMessage) setInfoMessage(null);
          }}
          disabled={isProcessing}
          aria-label="YouTube video URL"
          data-testid="video-url-input"
        />
        <button
          type="submit"
          className={styles.submitBtn}
          disabled={!url.trim() || isProcessing}
          aria-label={isAddVideoOnly ? 'Add video to library' : 'Start conversation'}
          data-testid="add-video-submit-button"
        >
          {isProcessing ? <Spinner size={16} /> : <ArrowRight size={16} />}
        </button>
      </div>

      {infoMessage && (
        <p className={styles.infoMessage} data-testid="composer-info-message">
          {infoMessage}
        </p>
      )}

      {error && (
        <p className={styles.error} data-testid="video-url-error">
          {error}
        </p>
      )}

      {/* In New Chat mode, allow quick-picking an existing video from library */}
      {!isAddVideoOnly && isPanel && readyVideos.length > 0 && (
        <div className={styles.libraryPickSection}>
          <p className={styles.libraryPickTitle}>Or choose a video from your library</p>
          <div className={styles.pickGrid}>
            {readyVideos.slice(0, 6).map((vid) => (
              <button
                key={vid.video_id}
                type="button"
                className={styles.pickChip}
                onClick={() => handlePickExistingVideo(vid)}
                title={vid.title || vid.video_id}
                data-testid={`quick-pick-${vid.video_id}`}
              >
                <Film size={12} aria-hidden="true" />
                <span className={styles.pickChipTitle}>{vid.title || vid.video_id}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </form>
  );
}
