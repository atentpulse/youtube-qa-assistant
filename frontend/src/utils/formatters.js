/**
 * Sanitizes video processing error messages so internal stack traces, database
 * errors, or low-level exceptions are never exposed to the user.
 */
export function sanitizeErrorMessage(errorMessage, fallback = 'Video processing failed. Please try again.') {
  if (!errorMessage || typeof errorMessage !== 'string') {
    return fallback;
  }

  const trimmed = errorMessage.trim();
  if (!trimmed) {
    return fallback;
  }

  const stackIndicators = [
    'traceback',
    'file "',
    'psycopg2',
    'sqlalchemy',
    'operationalerror',
    'internalservererror',
    'syntaxerror',
    'exception:',
    'connection refused',
    'password authentication failed',
  ];

  const lower = trimmed.toLowerCase();
  for (const indicator of stackIndicators) {
    if (lower.includes(indicator)) {
      return fallback;
    }
  }

  // If error has multiple lines (typical of unhandled error logs), use the first line only
  const firstLine = trimmed.split(/\r?\n/)[0].trim();
  if (firstLine.length > 200) {
    return `${firstLine.slice(0, 197)}…`;
  }

  return firstLine || fallback;
}

/**
 * Formats a video processing start timestamp into a friendly human-readable string.
 */
export function formatProcessingStartedAt(dateString) {
  if (!dateString) return null;
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return null;

  try {
    const timeFormatted = date.toLocaleTimeString([], {
      hour: 'numeric',
      minute: '2-digit',
    });
    return `Started at ${timeFormatted}`;
  } catch {
    return null;
  }
}
