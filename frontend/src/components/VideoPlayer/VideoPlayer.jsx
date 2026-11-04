import React, { forwardRef, useImperativeHandle, useRef, useState } from 'react';
import { AlertTriangle, Check, Copy, ExternalLink, RefreshCw } from 'lucide-react';
import { VIDEO_STATUS } from '../../utils/constants';
import Spinner from '../common/Spinner';
import Skeleton from '../common/Skeleton';
import styles from './VideoPlayer.module.css';

const VideoPlayer = forwardRef(function VideoPlayer(
  { video, reprocessVideo, onSwitchToResearch },
  ref
) {
  const iframeRef = useRef(null);
  const [copied, setCopied] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [showRestrictedNotice, setShowRestrictedNotice] = useState(false);
  const [iframeLoaded, setIframeLoaded] = useState(false);

  useImperativeHandle(ref, () => ({
    seekTo: (seconds) => {
      const targetSec = Math.max(0, Math.floor(seconds));
      setCurrentTime(targetSec);
      if (iframeRef.current && iframeRef.current.contentWindow) {
        try {
          iframeRef.current.contentWindow.postMessage(
            JSON.stringify({
              event: 'command',
              func: 'seekTo',
              args: [targetSec, true],
            }),
            '*'
          );
        } catch {
          // Ignore postMessage cross-origin errors
        }
      }
    },
  }));

  if (!video) return null;

  const videoId = video.video_id;
  const isProcessing = video.status === VIDEO_STATUS.PROCESSING;
  const isFailed = video.status === VIDEO_STATUS.FAILED;
  const isReady =
    video.status === VIDEO_STATUS.PROCESSED ||
    video.status === VIDEO_STATUS.ALREADY_PROCESSED;

  const currentOrigin = typeof window !== 'undefined' ? window.location.origin : '';
  const embedUrl = videoId
    ? `https://www.youtube-nocookie.com/embed/${videoId}?enablejsapi=1&origin=${encodeURIComponent(currentOrigin)}&rel=0`
    : null;

  const timestampParam = currentTime > 0 ? `&t=${currentTime}s` : '';
  const externalWatchUrl = video.url || `https://www.youtube.com/watch?v=${videoId}${timestampParam}`;

  const handleCopyLink = async () => {
    try {
      const linkToCopy = timestampParam
        ? `https://www.youtube.com/watch?v=${videoId}&t=${currentTime}s`
        : externalWatchUrl;
      await navigator.clipboard.writeText(linkToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const statusColors = {
    [VIDEO_STATUS.PROCESSED]: 'var(--success-600, #16a34a)',
    [VIDEO_STATUS.ALREADY_PROCESSED]: 'var(--success-600, #16a34a)',
    [VIDEO_STATUS.PROCESSING]: 'var(--warning-600, #d97706)',
    [VIDEO_STATUS.FAILED]: 'var(--danger-600, #dc2626)',
  };

  const statusLabels = {
    [VIDEO_STATUS.PROCESSED]: 'Ready',
    [VIDEO_STATUS.ALREADY_PROCESSED]: 'Ready',
    [VIDEO_STATUS.PROCESSING]: 'Processing…',
    [VIDEO_STATUS.FAILED]: 'Failed',
  };

  return (
    <div className={styles.playerStage} data-testid="video-player-stage">
      {/* 16:9 Video Embed Container */}
      <div className={styles.embedContainer}>
        {embedUrl && isReady ? (
          <>
            {!iframeLoaded && (
              <div className={styles.embedSkeletonWrap}>
                <Skeleton variant="video" className={styles.playerSkeleton} />
              </div>
            )}
            <iframe
              ref={iframeRef}
              src={embedUrl}
              title={video.title || 'YouTube video player'}
              className={`${styles.iframe} ${!iframeLoaded ? styles.iframeHidden : ''}`}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
              onLoad={() => setIframeLoaded(true)}
              data-testid="video-player-iframe"
            />
          </>
        ) : isProcessing ? (
          <div className={styles.embedStatePlaceholder}>
            <Spinner size={28} />
            <p className={styles.placeholderText}>
              Processing this video… ready shortly.
            </p>
          </div>
        ) : isFailed ? (
          <div className={styles.embedStatePlaceholder}>
            <AlertTriangle size={28} className={styles.errorIcon} />
            <p className={styles.placeholderText}>Video processing failed</p>
            {reprocessVideo && (
              <button
                type="button"
                className={styles.retryBtn}
                data-testid="retry-processing-button"
                onClick={() => reprocessVideo(videoId, video.url)}
              >
                <RefreshCw size={14} /> Retry processing
              </button>
            )}
          </div>
        ) : (
          <div className={styles.embedStatePlaceholder}>
            <p className={styles.placeholderText}>No video loaded</p>
          </div>
        )}
      </div>

      {/* Video Details Card */}
      <div className={styles.detailsCard}>
        <div className={styles.titleRow}>
          <h2
            className={styles.videoTitle}
            title={video.title}
            data-testid="video-header-title"
          >
            {video.title || 'Untitled video'}
          </h2>
          <span
            className={styles.statusBadge}
            style={{ color: statusColors[video.status] || 'var(--text-500)' }}
            data-testid="video-header-status"
          >
            <span
              className={styles.statusDot}
              style={{ background: statusColors[video.status] || 'var(--text-500)' }}
            />
            {statusLabels[video.status] || video.status}
          </span>
        </div>

        {/* Action Controls */}
        <div className={styles.actionsRow}>
          <a
            href={externalWatchUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.actionBtn}
            data-testid="video-external-link"
            title="Open video on YouTube"
          >
            <ExternalLink size={13} />
            <span>Watch on YouTube</span>
          </a>

          <button
            type="button"
            className={styles.actionBtn}
            onClick={handleCopyLink}
            data-testid="copy-video-link-button"
            title="Copy video link with current timestamp"
          >
            {copied ? <Check size={13} style={{ color: 'var(--success)' }} /> : <Copy size={13} />}
            <span>{copied ? 'Copied!' : 'Copy Link'}</span>
          </button>

          <button
            type="button"
            className={styles.textLinkBtn}
            onClick={() => setShowRestrictedNotice((v) => !v)}
          >
            {showRestrictedNotice ? 'Hide embed help' : 'Playback issues?'}
          </button>
        </div>

        {/* Fallback Notice for Restricted Embeds (Error 150/101) */}
        {showRestrictedNotice && (
          <div className={styles.restrictedNotice}>
            <div className={styles.restrictedHeader}>
              <AlertTriangle size={14} className={styles.warningIcon} />
              <span>Third-party embedding restricted by creator</span>
            </div>
            <p className={styles.restrictedBody}>
              Some video creators or copyright owners disable playback on external
              websites (YouTube Error 150/101). You can still analyze the transcript and ask
              questions in YtGenius while viewing the video directly on YouTube.
            </p>
            <a
              href={`https://www.youtube.com/watch?v=${videoId}${timestampParam}`}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.restrictedAction}
            >
              Open on YouTube {currentTime > 0 ? `at ${currentTime}s` : ''} ↗
            </a>
          </div>
        )}

        {/* Mobile helper to switch to research */}
        {onSwitchToResearch && (
          <div className={styles.mobileResearchSwitch}>
            <button
              type="button"
              className={styles.mobileSwitchBtn}
              onClick={onSwitchToResearch}
            >
              💬 Open AI Research Chat & Citations →
            </button>
          </div>
        )}
      </div>
    </div>
  );
});

export default VideoPlayer;
