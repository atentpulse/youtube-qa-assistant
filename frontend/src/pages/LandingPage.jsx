import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  Sparkles,
  Clock,
  Archive,
  Video,
  ArrowRight,
  Github,
  Linkedin,
  CheckCircle2,
  ExternalLink,
  Search,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../api/client';
import Spinner from '../components/common/Spinner';
import styles from './LandingPage.module.css';

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.87 2.7-6.62z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.9v2.33A9 9 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.16.28-1.7V4.97H.9A9 9 0 0 0 0 9c0 1.45.35 2.83.9 4.03l3.05-2.33z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .9 4.97l3.05 2.33C4.66 5.17 6.65 3.58 9 3.58z"
      />
    </svg>
  );
}

export default function LandingPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isRedirecting, setIsRedirecting] = useState(false);

  const handleContinueWithGoogle = () => {
    if (isAuthenticated) {
      navigate('/app');
      return;
    }
    setIsRedirecting(true);
    window.location.href = `${API_BASE_URL}/auth/google/login`;
  };

  const scrollToSection = (e, id) => {
    e.preventDefault();
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className={`${styles.landing} force-light-theme`}>
      {/* ---- Navigation ---- */}
      <header className={styles.nav}>
        <div className={styles.navContainer}>
          <Link to="/" className={styles.brand} data-testid="header-brand">
            <img src="/logo.svg" alt="VidMind logo" className={styles.brandLogo} />
            <span className={styles.brandName}>
              VidMind<span className={styles.brandAccent}>.</span>
            </span>
          </Link>

          <nav className={styles.navLinks} aria-label="Main Navigation">
            <a
              href="#features"
              className={styles.navLink}
              onClick={(e) => scrollToSection(e, 'features')}
            >
              Features
            </a>
            <a
              href="#how-it-works"
              className={styles.navLink}
              onClick={(e) => scrollToSection(e, 'how-it-works')}
            >
              How it works
            </a>
            {isAuthenticated ? (
              <Link to="/app" className={styles.navCta}>
                Open Workspace <ArrowRight size={14} />
              </Link>
            ) : (
              <>
                <Link to="/login" className={styles.navLink} data-testid="nav-sign-in-link">
                  Sign in
                </Link>
                <Link to="/register" className={styles.navCta} data-testid="nav-get-started-link">
                  Get Started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* ---- Hero Section ---- */}
      <section className={styles.hero}>
        <div className={styles.heroTag}>
          <span className={styles.heroTagDot} aria-hidden="true" />
          <span>YouTube Video Q&amp;A Assistant</span>
        </div>

        <h1 className={styles.heroHeadline}>Talk to any YouTube video.</h1>

        <p className={styles.heroSubtitle}>
          Turn long videos into conversations. Ask questions, understand the content, and jump
          directly to the source.
        </p>

        <div className={styles.heroCtas}>
          <button
            type="button"
            className={styles.primaryCta}
            onClick={handleContinueWithGoogle}
            disabled={isRedirecting}
            data-testid="hero-google-button"
          >
            {isRedirecting ? (
              <Spinner size={16} />
            ) : isAuthenticated ? (
              <>
                Open VidMind Workspace <ArrowRight size={16} />
              </>
            ) : (
              <>
                <GoogleIcon /> Continue with Google
              </>
            )}
          </button>

          {!isAuthenticated && (
            <Link to="/login" className={styles.secondaryCta} data-testid="hero-signin-link">
              Sign in
            </Link>
          )}

          <a
            href="#how-it-works"
            className={styles.secondaryCta}
            onClick={(e) => scrollToSection(e, 'how-it-works')}
          >
            See how it works
          </a>
        </div>

        {/* ---- Product Preview Mockup ---- */}
        <div className={styles.previewWrapper} id="preview" aria-label="VidMind Application Preview">
          <div className={styles.previewBrowserBar}>
            <div className={styles.previewDots}>
              <span className={styles.previewDot} />
              <span className={styles.previewDot} />
              <span className={styles.previewDot} />
            </div>
            <div className={styles.previewUrlBar}>
              <Search size={12} />
              <span>app.vidmind.ai/workspace</span>
            </div>
          </div>

          <div className={styles.previewBody}>
            {/* Preview Left Sidebar */}
            <div className={styles.previewSidebar}>
              <div className={styles.previewSidebarBrand}>
                <img src="/logo.svg" alt="" className={styles.previewBrandLogo} />
                <span>VidMind</span>
              </div>

              <div className={styles.previewNewChatBtn}>
                <span>+</span>
                <span>New Chat</span>
              </div>

              <div>
                <p className={styles.previewSidebarSectionTitle}>Conversations</p>
                <div className={`${styles.previewSidebarItem} ${styles.previewSidebarItemActive}`}>
                  <MessageSquare size={13} />
                  <span>Architecture deep dive</span>
                </div>
                <div className={styles.previewSidebarItem}>
                  <MessageSquare size={13} />
                  <span>Lecture takeaways</span>
                </div>
              </div>

              <div>
                <p className={styles.previewSidebarSectionTitle}>Video Library</p>
                <div className={`${styles.previewSidebarItem} ${styles.previewSidebarItemActive}`}>
                  <div className={styles.previewThumb}>
                    <img
                      src="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=80&q=80"
                      alt="AI Hardware Course"
                    />
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', fontWeight: 600 }}>AI Hardware Course</div>
                    <div style={{ fontSize: '11px', color: '#16a34a' }}>● Ready</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Preview Center/Right Workspace */}
            <div className={styles.previewMain}>
              <div className={styles.previewHeader}>
                <div className={styles.previewHeaderVideo}>
                  <div className={styles.previewThumb}>
                    <img
                      src="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=80&q=80"
                      alt=""
                    />
                  </div>
                  <div>
                    <div className={styles.previewHeaderTitle}>
                      Applied Data Science &amp; Hardware
                    </div>
                    <div style={{ fontSize: '11.5px', color: 'var(--text-500)' }}>
                      Stanford Seminar • 423 segments indexed
                    </div>
                  </div>
                </div>
                <span className={styles.previewStatusBadge}>
                  <CheckCircle2 size={11} /> Ready
                </span>
              </div>

              <div className={styles.previewChatFeed}>
                <div className={styles.previewQuestion}>
                  <span>What is this video about?</span>
                </div>

                <div className={styles.previewAnswerCard}>
                  <div className={styles.previewAiAvatar}>V</div>
                  <div className={styles.previewAnswerBody}>
                    <p style={{ margin: 0, marginBottom: '8px' }}>
                      This video explains modern neural network architectures and memory bandwidth
                      trade-offs. The instructor breaks down why memory wall limitations dominate
                      inference latency and walks through recent benchmark comparisons.
                    </p>
                    <div className={styles.previewSourcesRow}>
                      <span className={styles.previewSourcesLabel}>Sources:</span>
                      <span className={styles.previewSourceChip}>
                        00:04 <ExternalLink size={10} />
                      </span>
                      <span className={styles.previewSourceChip}>
                        01:12 <ExternalLink size={10} />
                      </span>
                      <span className={styles.previewSourceChip}>
                        04:58 <ExternalLink size={10} />
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className={styles.previewComposer}>
                <div className={styles.previewComposerBar}>
                  <span>Ask anything about this video…</span>
                  <div className={styles.previewSendBtn}>
                    <ArrowRight size={13} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---- Features Section ---- */}
      <section className={styles.featuresSection} id="features">
        <div className={styles.sectionHeader}>
          <div className={styles.sectionEyebrow}>Core Capabilities</div>
          <h2 className={styles.sectionTitle}>Everything you need to digest videos in seconds</h2>
          <p className={styles.sectionDesc}>
            Built specifically for lectures, podcasts, interviews, and deep tutorials that contain
            hours of critical knowledge.
          </p>
        </div>

        <div className={styles.featuresGrid}>
          <div className={styles.featureCard}>
            <div className={styles.featureIconBox}>
              <MessageSquare size={20} />
            </div>
            <h3 className={styles.featureTitle}>1. Ask anything</h3>
            <p className={styles.featureText}>
              Ask questions about video content naturally. VidMind searches transcript passages and
              understands conversational nuance.
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIconBox}>
              <Sparkles size={20} />
            </div>
            <h3 className={styles.featureTitle}>2. Grounded answers</h3>
            <p className={styles.featureText}>
              Answers are generated strictly from the processed video. No generic hallucinations or
              unsupported assertions.
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIconBox}>
              <Clock size={20} />
            </div>
            <h3 className={styles.featureTitle}>3. Timestamp sources</h3>
            <p className={styles.featureText}>
              Jump directly to relevant moments. Every claim links straight to the exact second in
              the YouTube video.
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIconBox}>
              <Archive size={20} />
            </div>
            <h3 className={styles.featureTitle}>4. Persistent conversations</h3>
            <p className={styles.featureText}>
              Continue conversations later. Your multi-turn dialogs are saved so you can pick up
              your research anytime.
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIconBox}>
              <Video size={20} />
            </div>
            <h3 className={styles.featureTitle}>5. Video library</h3>
            <p className={styles.featureText}>
              Keep processed videos organized in one unified workspace with title indexing and
              quick access.
            </p>
          </div>
        </div>
      </section>

      {/* ---- How It Works Section ---- */}
      <section className={styles.howSection} id="how-it-works">
        <div className={styles.howContainer}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionEyebrow}>Process</div>
            <h2 className={styles.sectionTitle}>How VidMind works</h2>
            <p className={styles.sectionDesc}>
              Three simple steps to unlock deep video insights without scrubbing through hours of
              footage.
            </p>
          </div>

          <div className={styles.stepsGrid}>
            <div className={styles.stepCard}>
              <div className={styles.stepNumber}>01</div>
              <h3 className={styles.stepTitle}>Paste a YouTube video</h3>
              <p className={styles.stepDesc}>
                Drop in any public YouTube video link. VidMind retrieves metadata and prepares the
                transcript for indexing.
              </p>
            </div>

            <div className={styles.stepCard}>
              <div className={styles.stepNumber}>02</div>
              <h3 className={styles.stepTitle}>VidMind processes it</h3>
              <p className={styles.stepDesc}>
                The content is segmented and indexed into vector embeddings for precision retrieval
                and context alignment.
              </p>
            </div>

            <div className={styles.stepCard}>
              <div className={styles.stepNumber}>03</div>
              <h3 className={styles.stepTitle}>Ask anything</h3>
              <p className={styles.stepDesc}>
                Get instantaneous, grounded answers with interactive timestamps linking to the
                exact lecture segment.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ---- Final CTA Section ---- */}
      <section className={styles.finalCtaSection}>
        <h2 className={styles.finalCtaHeadline}>Start with VidMind</h2>
        <p className={styles.finalCtaSubtitle}>
          Connect with your Google account or email to start processing videos and asking questions today.
        </p>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            className={styles.primaryCta}
            onClick={handleContinueWithGoogle}
            disabled={isRedirecting}
          >
            {isRedirecting ? (
              <Spinner size={16} />
            ) : isAuthenticated ? (
              <>
                Go to Workspace <ArrowRight size={16} />
              </>
            ) : (
              <>
                <GoogleIcon /> Continue with Google
              </>
            )}
          </button>
          {!isAuthenticated && (
            <Link to="/login" className={styles.secondaryCta}>
              Sign in
            </Link>
          )}
        </div>
      </section>

      {/* ---- Footer (the single landing-page footer) ---- */}
      <footer className={styles.footer}>
        <div className={styles.footerContainer}>
          <div className={styles.footerGrid}>
            <div className={styles.footerBrandCol}>
              <div className={styles.footerBrand}>
                <img src="/logo.svg" alt="VidMind logo" className={styles.footerLogo} />
                <span className={styles.footerBrandName}>VidMind</span>
              </div>
              <p className={styles.footerTagline}>Turn videos into conversations.</p>
              <div className={styles.footerSocial}>
                <a
                  href="https://github.com/rajashik-web"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.socialLink}
                  aria-label="VidMind on GitHub"
                  data-testid="footer-github-link"
                >
                  <Github size={16} />
                </a>
                <a
                  href="https://www.linkedin.com/in/ashik-raj-000598396"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.socialLink}
                  aria-label="VidMind on LinkedIn"
                  data-testid="footer-linkedin-link"
                >
                  <Linkedin size={16} />
                </a>
              </div>
            </div>

            <div className={styles.footerCol}>
              <h3 className={styles.footerColTitle}>Product</h3>
              <a
                href="#features"
                className={styles.footerLink}
                onClick={(e) => scrollToSection(e, 'features')}
              >
                Features
              </a>
              <a
                href="#how-it-works"
                className={styles.footerLink}
                onClick={(e) => scrollToSection(e, 'how-it-works')}
              >
                How it works
              </a>
              <Link to="/register" className={styles.footerLink}>
                Get Started
              </Link>
            </div>

            <div className={styles.footerCol}>
              <h3 className={styles.footerColTitle}>Account</h3>
              <Link to="/login" className={styles.footerLink} data-testid="footer-sign-in-link">
                Sign in
              </Link>
              <Link to="/register" className={styles.footerLink}>
                Create account
              </Link>
            </div>

            <div className={styles.footerCol}>
              <h3 className={styles.footerColTitle}>Resources</h3>
              <a
                href="#features"
                className={styles.footerLink}
                onClick={(e) => scrollToSection(e, 'features')}
              >
                YouTube Video Q&amp;A
              </a>
              <a
                href="https://github.com/rajashik-web"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.footerLink}
              >
                Documentation
              </a>
            </div>
          </div>

          <div className={styles.footerBottom}>
            <p className={styles.footerMeta}>© 2026 VidMind. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
