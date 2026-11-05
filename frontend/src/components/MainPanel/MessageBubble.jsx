import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import SourceChip from './SourceChip';
import Skeleton from '../common/Skeleton';
import Spinner from '../common/Spinner';
import { usePreferences } from '../../context/PreferencesContext';
import styles from './MainPanel.module.css';

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function ThumbsUpIcon() {
  return (
    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
    </svg>
  );
}

function ThumbsDownIcon() {
  return (
    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3" />
    </svg>
  );
}

/**
 * Renders one Q&A thread entry produced by ChatContext:
 * { question, answer, status: 'loading'|'done'|'error', sources, notFound, errorMessage }
 * ChatGPT-style clean flowing conversation layout.
 */
export default function MessageBubble({ message, onSeek }) {
  const { preferences } = usePreferences();
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(null); // 'like' | 'dislike' | null

  const isLoading = message.status === 'loading';
  const isError = message.status === 'error';
  const showNotFound = !isLoading && !isError && message.notFound && !message.answer;
  const showCitations = preferences?.showCitations !== false;

  const handleCopy = () => {
    if (message.answer) {
      navigator.clipboard.writeText(message.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className={styles.message} data-testid="message-bubble">
      {/* User Question — Right aligned, clean YouTube blue highlight */}
      {message.question && (
        <div className={styles.messageQuestion}>
          <div className={styles.userQuestionBubble}>
            <p className={styles.messageQuestionText} data-testid="message-question">
              {message.question}
            </p>
          </div>
        </div>
      )}

      {/* AI Answer & Citations — Flowing directly on canvas without card container */}
      <div className={styles.messageAnswer}>
        <div className={styles.messageAnswerBody}>
          <div className={styles.aiCard}>
            {isLoading && (
              <div className={styles.messageLoading} data-testid="message-loading">
                <div className={styles.streamingHeader}>
                  <Spinner size={14} />
                  <span>Analyzing transcript & citations…</span>
                </div>
                <div className={styles.streamingSkeletons}>
                  <Skeleton variant="text" width="92%" height="13px" />
                  <Skeleton variant="text" width="82%" height="13px" />
                  <Skeleton variant="text" width="65%" height="13px" />
                  <div className={styles.streamingCitations}>
                    <Skeleton width="105px" height="26px" borderRadius="6px" />
                    <Skeleton width="125px" height="26px" borderRadius="6px" />
                  </div>
                </div>
              </div>
            )}

            {isError && (
              <div className={styles.messageError} data-testid="message-error">
                <span>{message.errorMessage || 'Something went wrong.'}</span>
              </div>
            )}

            {showNotFound && (
              <p className={styles.messageNotFound} data-testid="message-not-found">
                I could not find the answer in the video transcript.
              </p>
            )}

            {!isLoading && !isError && message.answer && (
              <>
                <div className={styles.messageAnswerText} data-testid="message-answer">
                  <ReactMarkdown>{message.answer}</ReactMarkdown>
                </div>

                {/* Compact action buttons: Copy, Like, Dislike */}
                <div className={styles.messageActions}>
                  <button
                    type="button"
                    className={styles.actionBtn}
                    onClick={handleCopy}
                    title={copied ? 'Copied to clipboard!' : 'Copy response'}
                    aria-label="Copy response"
                  >
                    <CopyIcon />
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                  <button
                    type="button"
                    className={`${styles.actionBtn} ${feedback === 'like' ? styles.actionBtnActive : ''}`}
                    onClick={() => setFeedback((f) => (f === 'like' ? null : 'like'))}
                    title="Good response"
                    aria-label="Good response"
                  >
                    <ThumbsUpIcon />
                  </button>
                  <button
                    type="button"
                    className={`${styles.actionBtn} ${feedback === 'dislike' ? styles.actionBtnActive : ''}`}
                    onClick={() => setFeedback((f) => (f === 'dislike' ? null : 'dislike'))}
                    title="Bad response"
                    aria-label="Bad response"
                  >
                    <ThumbsDownIcon />
                  </button>
                </div>
              </>
            )}

            {!isLoading &&
              !isError &&
              showCitations &&
              Array.isArray(message.sources) &&
              message.sources.length > 0 && (
                <div className={styles.sourcesBlock}>
                  <span className={styles.sourcesHeading}>Citations:</span>
                  <div className={styles.sourcesList}>
                    {message.sources.map((src, idx) => (
                      <SourceChip key={idx} source={src} onSeek={onSeek} />
                    ))}
                  </div>
                </div>
              )}
          </div>
        </div>
      </div>
    </div>
  );
}
