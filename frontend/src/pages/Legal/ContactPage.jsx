import React from 'react';
import LegalLayout from './LegalLayout';
import { Github, Bug, ExternalLink, AlertTriangle } from 'lucide-react';
import styles from './LegalLayout.module.css';

export default function ContactPage() {
  return (
    <LegalLayout
      title="Contact &amp; Support"
      subtitle="Have questions, technical feedback, or need assistance? Reach out through our public channels."
      lastUpdated="November 11, 2026"
    >
      <p>
        Whether you are experiencing playback issues, have suggestions for new research features, or want to contribute to our open-source codebase, we welcome technical feedback and bug reports.
      </p>

      {/* Public Channel Security Warning */}
      <div className={`${styles.noticeBox} ${styles.noticeBoxAlert}`}>
        <AlertTriangle size={20} className={styles.noticeBoxIcon} />
        <div>
          <strong>Public Channel Notice &amp; Security Warning:</strong> Our GitHub Issues tracker and repository discussions are completely public and accessible to anyone on the internet. Never submit email addresses, account identifiers, passwords, verification codes (OTPs), access or session tokens, API keys, or confidential personal information in an issue or comment. Do not submit account deletion requests containing personal information through public GitHub Issues. Please note that no private support ticketing channel is currently available.
        </div>
      </div>

      <div className={styles.cardGrid}>
        {/* Community & Issue Support Card */}
        <div className={styles.card}>
          <div className={styles.cardIcon}>
            <Github size={20} />
          </div>
          <h3 className={styles.cardTitle}>GitHub Issues Support</h3>
          <p className={styles.cardDesc}>
            For general technical inquiries, open-source feedback, feature suggestions, and public discussion.
          </p>
          <a
            href="https://github.com/rajashik-web/youtube-qa-assistant/issues"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.cardAction}
            aria-label="Open GitHub Issues"
          >
            Open GitHub Issues <ExternalLink size={12} />
          </a>
        </div>

        {/* GitHub Repository Card */}
        <div className={styles.card}>
          <div className={styles.cardIcon}>
            <ExternalLink size={20} />
          </div>
          <h3 className={styles.cardTitle}>GitHub Repository</h3>
          <p className={styles.cardDesc}>
            Explore the open-source codebase, review architecture documentation, propose enhancements, or contribute.
          </p>
          <a
            href="https://github.com/rajashik-web/youtube-qa-assistant"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.cardAction}
            aria-label="View Source Code on GitHub"
          >
            View Repository <ExternalLink size={12} />
          </a>
        </div>

        {/* Issue & Bug Tracker Card */}
        <div className={styles.card}>
          <div className={styles.cardIcon}>
            <Bug size={20} />
          </div>
          <h3 className={styles.cardTitle}>Issue &amp; Bug Tracker</h3>
          <p className={styles.cardDesc}>
            Encountered a transcript extraction error, ingestion failure, or unexpected behavior? Submit an issue on our tracker.
          </p>
          <a
            href="https://github.com/rajashik-web/youtube-qa-assistant/issues/new"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.cardAction}
            aria-label="Report an Issue on GitHub"
          >
            Report an Issue <ExternalLink size={12} />
          </a>
        </div>
      </div>

      <h2>Frequently Asked Questions</h2>

      <h3>Why did my YouTube video fail to process?</h3>
      <p>
        YtGenius requires closed captions (transcripts) to index video content. A video cannot be processed if:
      </p>
      <ul>
        <li>The video is set to Private on YouTube.</li>
        <li>The creator has disabled closed captions and YouTube has not generated automatic subtitles.</li>
        <li>The video URL is malformed or inaccessible in your region.</li>
      </ul>

      <h3>Is YtGenius free to use?</h3>
      <p>
        Yes! YtGenius is built as a publicly accessible, free-to-use research tool. You can index videos and conduct interactive research chats without subscription fees.
      </p>

      <h3>How do I request deletion of my account or data?</h3>
      <p>
        While our backend API provides a programmatic <code>DELETE /auth/me</code> endpoint, YtGenius does not currently provide an in-app graphical interface for self-service account deletion, nor does it currently operate a private support desk or confidential ticketing system.
      </p>
      <p>
        <strong>Privacy notice:</strong> Because our GitHub issue tracker is completely public, do NOT submit account deletion requests, email addresses, usernames, or any personal account identifiers through GitHub Issues. A secure private deletion workflow is not currently available.
      </p>

      <h3>How is my research history stored?</h3>
      <p>
        Your queries, answers, and timestamp citations are securely stored in our relational database and associated exclusively with your authenticated user account.
      </p>
    </LegalLayout>
  );
}
