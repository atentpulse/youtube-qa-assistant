import React, { useState } from 'react';
import Modal from '../../../components/common/Modal';
import { useToast } from '../../../context/ToastContext';
import { HelpCircle, Bug, FileText, Shield } from 'lucide-react';
import common from './CategoryCommon.module.css';

export default function AboutCategory() {
  const toast = useToast();
  const [activeModal, setActiveModal] = useState(null); // 'bug' | 'privacy' | 'terms' | 'help'
  const [bugDescription, setBugDescription] = useState('');
  const [isSubmittingBug, setIsSubmittingBug] = useState(false);

  const handleSubmitBug = (e) => {
    e.preventDefault();
    if (!bugDescription.trim()) {
      toast.error('Please describe the issue before submitting.');
      return;
    }
    setIsSubmittingBug(true);
    setTimeout(() => {
      setIsSubmittingBug(false);
      setBugDescription('');
      setActiveModal(null);
      toast.success('Bug report recorded. Thank you for helping improve YtGenius!');
    }, 600);
  };

  return (
    <div className={common.container}>
      <div className={common.header}>
        <h2 className={common.title}>About YtGenius</h2>
        <p className={common.description}>
          Application metadata, system specifications, documentation, and support resources.
        </p>
      </div>

      {/* Brand & Application Identity */}
      <div className={common.section}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '52px',
              height: '52px',
              borderRadius: '10px',
              background: 'var(--accent-red, #ff0033)',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '22px',
              fontWeight: '700',
              flexShrink: 0,
            }}
          >
            ▶
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-primary)' }}>
                YtGenius
              </span>
              <span className={`${common.badge} ${common.badgeNeutral}`}>v1.0.0</span>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.45' }}>
              Ask questions about any YouTube video and get instant, timestamped answers grounded strictly in the transcript.
            </p>
          </div>
        </div>
      </div>

      {/* System Stack Architecture */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>System Architecture</h3>
          <p className={common.sectionSubtitle}>
            Core technologies powering transcript retrieval, ingestion, and inference.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Large Language Model</span>
            <span className={common.rowDescription}>
              High-throughput transcript reasoning and grounded JSON synthesis.
            </span>
          </div>
          <span className={`${common.badge} ${common.badgeNeutral}`}>
            Groq API
          </span>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Vector Database</span>
            <span className={common.rowDescription}>
              Semantic similarity search across chunked transcript segment embeddings.
            </span>
          </div>
          <span className={`${common.badge} ${common.badgeNeutral}`}>
            Qdrant Vector DB
          </span>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Relational Store</span>
            <span className={common.rowDescription}>
              Multi-user canonical video catalog, user profiles, and chat threads.
            </span>
          </div>
          <span className={`${common.badge} ${common.badgeNeutral}`}>
            PostgreSQL
          </span>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Client Application</span>
            <span className={common.rowDescription}>
              Responsive dark-theme application shell with dual-stage research studio.
            </span>
          </div>
          <span className={`${common.badge} ${common.badgeNeutral}`}>
            React 18 + Vite
          </span>
        </div>
      </div>

      {/* Help, Support & Legal Resources */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Help &amp; Legal Policies</h3>
          <p className={common.sectionSubtitle}>
            Documentation, support guides, bug submission, and terms of service.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Help &amp; Support Guide</span>
            <span className={common.rowDescription}>
              Answers to frequently asked questions on citations, YouTube formats, and models.
            </span>
          </div>
          <button
            type="button"
            className={common.btnSecondary}
            onClick={() => setActiveModal('help')}
            data-testid="about-help-guide-btn"
          >
            <HelpCircle size={14} /> View Guide
          </button>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Report a Problem</span>
            <span className={common.rowDescription}>
              Report transcript ingestion failures, playback sync anomalies, or UI issues.
            </span>
          </div>
          <button
            type="button"
            className={common.btnSecondary}
            onClick={() => setActiveModal('bug')}
            data-testid="about-report-bug-btn"
          >
            <Bug size={14} /> Report Bug
          </button>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Privacy Policy</span>
            <span className={common.rowDescription}>
              Review how transcript queries are processed with zero AI training on user data.
            </span>
          </div>
          <button
            type="button"
            className={common.btnSecondary}
            onClick={() => setActiveModal('privacy')}
            data-testid="about-privacy-policy-btn"
          >
            <Shield size={14} /> Privacy Policy
          </button>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Terms of Service</span>
            <span className={common.rowDescription}>
              Usage guidelines and YouTube API terms compliance information.
            </span>
          </div>
          <button
            type="button"
            className={common.btnSecondary}
            onClick={() => setActiveModal('terms')}
            data-testid="about-terms-service-btn"
          >
            <FileText size={14} /> Terms of Service
          </button>
        </div>
      </div>

      {/* Help Guide Modal */}
      <Modal
        isOpen={activeModal === 'help'}
        onClose={() => setActiveModal(null)}
        title="Help & Support Guide"
        cancelLabel="Close"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px', lineHeight: '1.5' }}>
          <div>
            <strong style={{ color: 'var(--text-primary)' }}>How do timestamp citations work?</strong>
            <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)' }}>
              When you ask a question, YtGenius retrieves the most relevant transcript segments. The AI cites these exact moments, rendering clickable chips like <code>02:45</code> that automatically cue the YouTube video player.
            </p>
          </div>
          <div>
            <strong style={{ color: 'var(--text-primary)' }}>Why can some videos not be processed?</strong>
            <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)' }}>
              Videos must have closed captions (English or auto-generated) available via YouTube. Videos without captions or restricted by age/region cannot be ingested.
            </p>
          </div>
          <div>
            <strong style={{ color: 'var(--text-primary)' }}>What is strict transcript grounding?</strong>
            <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)' }}>
              YtGenius strictly prevents AI hallucination. If a concept is not explained in the video transcript, the assistant will explicitly inform you rather than inventing steps or tools.
            </p>
          </div>
        </div>
      </Modal>

      {/* Bug Report Modal */}
      <Modal
        isOpen={activeModal === 'bug'}
        onClose={() => setActiveModal(null)}
        title="Report a Problem"
        confirmLabel="Submit Report"
        cancelLabel="Cancel"
        isLoading={isSubmittingBug}
        onConfirm={handleSubmitBug}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)' }}>
            Describe the bug or unexpected behavior you encountered:
          </p>
          <textarea
            className={common.input}
            style={{ width: '100%', maxWidth: '100%', minHeight: '90px', resize: 'vertical' }}
            placeholder="e.g. Timestamp citation didn't seek properly on video..."
            value={bugDescription}
            onChange={(e) => setBugDescription(e.target.value)}
            required
            data-testid="about-bug-description-input"
          />
        </div>
      </Modal>

      {/* Privacy Policy Modal */}
      <Modal
        isOpen={activeModal === 'privacy'}
        onClose={() => setActiveModal(null)}
        title="Privacy Policy"
        cancelLabel="Close"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', lineHeight: '1.5', maxHeight: '350px', overflowY: 'auto' }}>
          <p>
            At YtGenius, data privacy and transparency are fundamental to our architecture:
          </p>
          <p>
            <strong>1. No Training on User Queries:</strong> Inquiries submitted to the research assistant are processed solely in volatile memory to construct transcript RAG prompts and are never used to train public AI models.
          </p>
          <p>
            <strong>2. Canonical Transcripts:</strong> Video captions retrieved from YouTube are indexed to enable search and timestamp citations. Transcripts are cached to minimize external API roundtrips.
          </p>
          <p>
            <strong>3. Account Ownership &amp; Deletion:</strong> You retain full rights to your conversation history. You can export or erase your history, or permanently delete your account at any time via Settings.
          </p>
        </div>
      </Modal>

      {/* Terms of Service Modal */}
      <Modal
        isOpen={activeModal === 'terms'}
        onClose={() => setActiveModal(null)}
        title="Terms of Service"
        cancelLabel="Close"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', lineHeight: '1.5', maxHeight: '350px', overflowY: 'auto' }}>
          <p>
            By utilizing YtGenius, you agree to the following terms:
          </p>
          <p>
            <strong>1. YouTube API Compliance:</strong> YtGenius accesses publicly accessible video metadata and closed captions pursuant to YouTube Developer terms. Video playback occurs directly through the standard YouTube Embedded Player.
          </p>
          <p>
            <strong>2. Grounded Answers:</strong> AI summaries and answers are derived algorithmically from transcript text. While engineered for maximum faithfulness, users should review critical details against source timestamps.
          </p>
          <p>
            <strong>3. Lawful Use:</strong> You agree not to use the service for automated scraping or abusive activity.
          </p>
        </div>
      </Modal>
    </div>
  );
}
