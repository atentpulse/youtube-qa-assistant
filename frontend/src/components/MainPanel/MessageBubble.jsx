import React from 'react';
import ReactMarkdown from 'react-markdown';
import SourceChip from './SourceChip';
import Spinner from '../common/Spinner';
import styles from './MainPanel.module.css';

/**
 * Renders one Q&A thread entry produced by ChatContext:
 * { question, answer, status: 'loading'|'done'|'error', sources, notFound, errorMessage }
 * Styles come from the existing MainPanel.module.css Q&A classes.
 */
export default function MessageBubble({ message, onSeek }) {
  const isLoading = message.status === 'loading';
  const isError = message.status === 'error';
  const showNotFound =
    !isLoading && !isError && message.notFound && !message.answer;

  return (
    <div className={styles.message} data-testid="message-bubble">
      {message.question && (
        <div className={styles.messageQuestion}>
          <div className={styles.qaLabel} aria-hidden="true">
            Q
          </div>
          <div className={styles.messageAnswerBody}>
            <p className={styles.messageAnswerText} data-testid="message-question">
              {message.question}
            </p>
          </div>
        </div>
      )}

      <div className={styles.messageAnswer}>
        <div className={`${styles.qaLabel} ${styles.qaLabelAnswer}`} aria-hidden="true">
          A
        </div>
        <div className={styles.messageAnswerBody}>
          {isLoading && (
            <div className={styles.messageLoading} data-testid="message-loading">
              <Spinner size={14} />
              <span>Thinking…</span>
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
            <div className={styles.messageAnswerText} data-testid="message-answer">
              <ReactMarkdown>{message.answer}</ReactMarkdown>
            </div>
          )}

          {!isLoading &&
            !isError &&
            Array.isArray(message.sources) &&
            message.sources.length > 0 && (
              <div className={styles.sourcesBlock}>
                <p className={styles.sourcesLabel}>Sources</p>
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
  );
}
