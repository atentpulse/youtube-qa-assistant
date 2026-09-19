import React, { useState } from 'react';
import { ArrowRight, Link as LinkIcon, X } from 'lucide-react';
import Spinner from '../common/Spinner';
import { useVideoLibrary } from '../../context/VideoLibraryContext';
import { useUI } from '../../context/UIContext';
import { ApiError } from '../../api/client';
import styles from './UrlComposer.module.css';

export default function UrlComposer({ variant = 'welcome', onClose }) {
  const [url, setUrl] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const { addVideo } = useVideoLibrary();
  const { closeComposer } = useUI();

  const isPanel = variant === 'panel';
  const handleClose = onClose || closeComposer;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const clean = url.trim();
    if (!clean || isProcessing) return;
    setIsProcessing(true);
    setError(null);
    try {
      await addVideo(clean);
      setUrl('');
      handleClose();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Could not start processing this video. Please try again.'
      );
    } finally {
      setIsProcessing(false);
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
          <h2 className={styles.panelTitle}>Add a YouTube video</h2>
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
          }}
          disabled={isProcessing}
          aria-label="YouTube video URL"
          data-testid="video-url-input"
        />
        <button
          type="submit"
          className={styles.submitBtn}
          disabled={!url.trim() || isProcessing}
          aria-label="Add video"
          data-testid="add-video-submit-button"
        >
          {isProcessing ? <Spinner size={16} /> : <ArrowRight size={16} />}
        </button>
      </div>
      {error && (
        <p className={styles.error} data-testid="video-url-error">
          {error}
        </p>
      )}
    </form>
  );
}
