import React from 'react';
import styles from './MainPanel.module.css';

export default function SourceChip({ source, onSeek }) {
  const handleClick = (e) => {
    if (onSeek && typeof source.start_time === 'number') {
      e.preventDefault();
      onSeek(source.start_time);
    }
  };

  const label = source.start_time_formatted
    ? `${source.start_time_formatted}${source.end_time_formatted ? ' - ' + source.end_time_formatted : ''}`
    : `${Math.floor(source.start_time || 0)}s`;

  return (
    <a
      href={source.url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className={styles.sourceChip}
      data-testid="source-chip"
      onClick={handleClick}
      title={source.text ? source.text.slice(0, 120) : 'Jump to timestamp'}
    >
      <span className={styles.sourceTime}>{label}</span>
    </a>
  );
}
