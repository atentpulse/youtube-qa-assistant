import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Copy, Check, ThumbsUp, ThumbsDown } from 'lucide-react';
import SourceChip from './SourceChip';
import Skeleton from '../common/Skeleton';
import Spinner from '../common/Spinner';
import Tooltip from '../common/Tooltip';
import { usePreferences } from '../../context/PreferencesContext';
import styles from './MainPanel.module.css';

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

                {/* ChatGPT-style minimal action toolbar: Copy, Like, Dislike */}
                <div className={styles.messageToolbar} role="toolbar" aria-label="Response actions">
                  <Tooltip content={copied ? 'Copied!' : 'Copy'}>
                    <button
                      type="button"
                      className={styles.toolbarBtn}
                      onClick={handleCopy}
                      aria-label={copied ? 'Copied to clipboard' : 'Copy response'}
                      data-testid="copy-response-button"
                    >
                      {copied ? (
                        <Check size={14} className={styles.checkIcon} />
                      ) : (
                        <Copy size={14} />
                      )}
                    </button>
                  </Tooltip>

                  <Tooltip content="Good response">
                    <button
                      type="button"
                      className={`${styles.toolbarBtn} ${feedback === 'like' ? styles.toolbarBtnActiveLike : ''}`}
                      onClick={() => setFeedback((f) => (f === 'like' ? null : 'like'))}
                      aria-label="Good response"
                      aria-pressed={feedback === 'like'}
                      data-testid="feedback-like-button"
                    >
                      <ThumbsUp size={14} />
                    </button>
                  </Tooltip>

                  <Tooltip content="Bad response">
                    <button
                      type="button"
                      className={`${styles.toolbarBtn} ${feedback === 'dislike' ? styles.toolbarBtnActiveDislike : ''}`}
                      onClick={() => setFeedback((f) => (f === 'dislike' ? null : 'dislike'))}
                      aria-label="Bad response"
                      aria-pressed={feedback === 'dislike'}
                      data-testid="feedback-dislike-button"
                    >
                      <ThumbsDown size={14} />
                    </button>
                  </Tooltip>
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
