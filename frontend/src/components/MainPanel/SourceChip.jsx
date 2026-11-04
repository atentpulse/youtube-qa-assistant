import React from 'react';
import styles from './MainPanel.module.css';

export default function SourceChip({ source, onSeek }) {
  const handleClick = (e) => {
    if (onSeek && typeof source.start_time === 'number') {
      e.preventDefault();
      onSeek(source.start_time);
    }
  };

  const timeLabel = source.start_time_formatted
    ? `${source.start_time_formatted}${source.end_time_formatted ? ' - ' + source.end_time_formatted : ''}`
    : `${Math.floor(source.start_time || 0)}s`;

  const tooltipText = source.text
    ? `Jump to ${timeLabel}: "${source.text.slice(0, 140)}..."`
    : `Jump to ${timeLabel} in video`;

  return (
    <a
      href={source.url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className={styles.sourceChip}
      data-testid="source-chip"
      onClick={handleClick}
      title={tooltipText}
      aria-label={tooltipText}
    >
      <span className={styles.sourceChipIcon}>⏱</span>
      <span className={styles.sourceTime}>{timeLabel}</span>
      {source.text && (
        <span className={styles.sourceSnippet}>
          {source.text.slice(0, 24)}…
        </span>
      )}
    </a>
  );
}
