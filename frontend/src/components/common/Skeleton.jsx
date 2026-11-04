import React from 'react';
import styles from './Skeleton.module.css';

export default function Skeleton({
  variant = 'rect', // 'rect' | 'text' | 'circle' | 'video'
  width,
  height,
  borderRadius,
  className = '',
  style = {},
  ...props
}) {
  const customStyles = {
    ...(width ? { width } : {}),
    ...(height ? { height } : {}),
    ...(borderRadius ? { borderRadius } : {}),
    ...style,
  };

  const variantClass = {
    rect: styles.rect,
    text: styles.text,
    circle: styles.circle,
    video: styles.video,
  }[variant] || styles.rect;

  return (
    <div
      className={`${styles.skeleton} ${variantClass} ${className}`}
      style={customStyles}
      aria-hidden="true"
      {...props}
    />
  );
}
