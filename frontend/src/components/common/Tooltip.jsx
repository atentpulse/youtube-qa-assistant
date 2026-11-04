import React from 'react';
import styles from './Tooltip.module.css';

export default function Tooltip({ children, content, disabled = false, className = '' }) {
  if (disabled || !content) {
    return <>{children}</>;
  }

  return (
    <div className={`${styles.wrapper} ${className}`}>
      {children}
      <div className={styles.tooltip} role="tooltip" aria-hidden="true">
        {content}
      </div>
    </div>
  );
}
