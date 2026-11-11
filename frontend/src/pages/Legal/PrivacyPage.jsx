import React from 'react';
import LegalLayout from './LegalLayout';
import { ShieldCheck } from 'lucide-react';
import styles from './LegalLayout.module.css';

export default function PrivacyPage() {
  return (
    <LegalLayout
      title="Privacy Policy"
      subtitle="How YtGenius collects, processes, stores, and protects your information."
      lastUpdated="November 11, 2026"
    >
      <div className={styles.noticeBox}>
        <ShieldCheck size={20} className={styles.noticeBoxIcon} />
        <div>
          <strong>Privacy First Architecture:</strong> Your inquiries are used to retrieve relevant transcript passages and synthesize answers, and are never sold or used by YtGenius to train public AI models. You retain control over your personal data.
        </div>
      </div>

      <h2>1. Overview</h2>
      <p>
        YtGenius (&quot;we&quot;, &quot;our&quot;, or &quot;the service&quot;) provides an intelligent YouTube video research assistant that extracts, indexes, and answers questions using publicly accessible video transcripts. This Privacy Policy describes how personal information and video data are handled when you access or use our platform.
      </p>

      <h2>2. Information We Collect</h2>
      <p>
        We collect only the minimum data required to authenticate users, index requested YouTube video transcripts, and provide persistent research chat sessions:
      </p>
      <ul>
        <li>
          <strong>Account &amp; Authentication Data:</strong> When signing in with Google OAuth 2.0, we receive your Google user identifier, email address, display name, and avatar image URL. When creating an account directly, we store your email address and a salted, cryptographically hashed representation of your password using bcrypt. We never store plain-text passwords.
        </li>
        <li>
          <strong>Video &amp; Transcript Data:</strong> When you add a YouTube URL to your workspace, we retrieve publicly available video metadata (video title, channel name, video duration, and thumbnail) and publicly accessible closed captions (transcripts) using YouTube Developer APIs.
        </li>
        <li>
          <strong>Semantic Vector Embeddings:</strong> Video transcripts are segmented into sequential passage chunks and processed locally using the SentenceTransformers model (<code>all-MiniLM-L6-v2</code>) to produce 384-dimensional dense vector embeddings. These embeddings are stored in our vector database (Qdrant) to enable fast similarity search.
        </li>
        <li>
          <strong>Conversations &amp; Query History:</strong> Your research queries, AI-generated responses, and associated timestamp citation ranges are stored in our relational database so you can revisit, continue, or search your previous chats.
        </li>
        <li>
          <strong>Technical Session Data:</strong> We use secure, HTTP-only authentication cookies and local browser storage strictly for session validation and client-side preferences (such as theme and video player synchronization settings).
        </li>
      </ul>

      <h2>3. How We Use Information</h2>
      <p>Your information is used exclusively to operate and improve the service:</p>
      <ul>
        <li>To authenticate your identity and safeguard your account against unauthorized access.</li>
        <li>To index video transcripts and perform vector retrieval matching your questions with relevant transcript segments.</li>
        <li>To generate grounded answers with precise timestamp citations through inference with third-party LLM providers.</li>
        <li>To allow you to manage your saved video library and research conversations across sessions.</li>
      </ul>
      <p>
        <strong>We do NOT sell, rent, or trade your personal information.</strong> We do not engage in behavioral advertising or user tracking across external websites.
      </p>

      <h2>4. Multi-User Canonical Video Storage Architecture</h2>
      <p>
        YtGenius utilizes a reference-counted canonical video storage model to optimize computational and storage resources:
      </p>
      <ul>
        <li>
          When a user adds a YouTube video, its transcript and vector embeddings are stored in a canonical shared repository.
        </li>
        <li>
          Each user who adds the same video receives an independent personal reference link in their library. Your conversations, notes, and queries remain strictly private to your account.
        </li>
        <li>
          When you delete a video from your library, your reference is removed. If other users also reference that video, their access remains unaffected.
        </li>
        <li>
          When the active reference count for a video reaches zero (no user references it), all associated vector embeddings in Qdrant and cached transcript records are permanently deleted.
        </li>
      </ul>

      <h2>5. Third-Party Services &amp; Subprocessors</h2>
      <p>
        To provide real-time inference, authentication, and video playback, YtGenius integrates with the following third-party infrastructure providers:
      </p>
      <ul>
        <li>
          <strong>Google OAuth 2.0:</strong> Used for secure single-sign-on. Your interaction with Google authentication is governed by the Google Privacy Policy.
        </li>
        <li>
          <strong>YouTube Data API &amp; Embedded Player:</strong> Video metadata and captions are accessed pursuant to YouTube Developer terms. Video playback is rendered directly via the standard YouTube IFrame Player.
        </li>
        <li>
          <strong>Groq Cloud:</strong> Used for high-speed large language model inference to synthesize answers from retrieved transcript chunks. Prompts transmitted to Groq are governed by Groq&apos;s API privacy policies and data protection standards, and are not used by YtGenius to train public models.
        </li>
        <li>
          <strong>Qdrant Cloud:</strong> Vector database used for indexed transcript similarity search. Vector collections store transcript passage embeddings and metadata; no personally identifiable user profile data is stored in Qdrant.
        </li>
      </ul>

      <h2>6. Data Retention &amp; User Autonomy</h2>
      <p>
        You maintain authority over your personal information, video library, and research conversations:
      </p>
      <ul>
        <li>
          <strong>Conversation Records:</strong> Research conversations and query histories are stored in our relational database and linked exclusively to your authenticated account.
        </li>
        <li>
          <strong>Video Associations:</strong> Adding a video creates a reference in your personal library. The shared canonical transcript and embeddings are retained only while referenced by active users.
        </li>
        <li>
          <strong>Account Deletion &amp; Known Limitations:</strong> While the backend API provides an authenticated programmatic deletion endpoint (<code>DELETE /auth/me</code>), YtGenius does not currently offer a user-facing self-service account deletion interface in the frontend application. Furthermore, YtGenius does not currently maintain a private customer support desk or confidential email ticketing system.
          <br /><br />
          <em>Privacy Warning:</em> Public GitHub Issues are <strong>not</strong> a safe or appropriate channel for personal account deletion requests. Users must never post email addresses, usernames, account identifiers, passwords, verification codes, or personal data to public repositories. Because no secure private request mechanism is currently integrated, a supported private account deletion workflow is currently unavailable until a dedicated in-app deletion interface is implemented.
        </li>
      </ul>

      <h2>7. Security Practices</h2>
      <p>
        We employ industry-standard technical safeguards to protect your information:
      </p>
      <ul>
        <li>All client-server communications are encrypted in transit using Transport Layer Security (TLS/HTTPS).</li>
        <li>User passwords are protected with strong bcrypt cryptographic hashing with per-user salt.</li>
        <li>Database operations utilize parameterized queries through SQLAlchemy ORM to prevent SQL injection.</li>
        <li>Cross-Site Request Forgery (CSRF) protections and single-use authorization code exchange protocols guard authentication flows.</li>
      </ul>

      <h2>8. Children&apos;s Privacy</h2>
      <p>
        YtGenius is not directed toward children under 13 years of age. We do not knowingly collect personal information from children under 13.
      </p>

      <h2>9. Policy Updates</h2>
      <p>
        We may update this Privacy Policy periodically to reflect service enhancements or changes in regulatory requirements. When changes are made, the effective date at the top of this page will be updated.
      </p>

      <h2>10. Contact Us &amp; Channel Privacy Limitations</h2>
      <p>
        For general open-source development discussions, technical feedback, and bug reports, you may visit our public repository:
      </p>
      <ul>
        <li>Public Issue Tracker: <a href="https://github.com/rajashik-web/youtube-qa-assistant/issues" target="_blank" rel="noopener noreferrer">GitHub Issues (Public)</a></li>
        <li>Documentation Hub: <a href="/docs">YtGenius Documentation</a></li>
      </ul>
      <p>
        <strong>Notice on Channel Privacy:</strong> YtGenius is an open-source project and does not operate a private customer support desk, confidential ticketing portal, or private communication channel. All communications submitted through GitHub Issues are public records. Do not disclose email addresses, account identifiers, confidential personal information, or authentication credentials in public repository issues.
      </p>
    </LegalLayout>
  );
}
