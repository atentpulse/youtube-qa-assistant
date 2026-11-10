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
  ExternalLink,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Menu,
  Copy,
  ThumbsUp,
  ThumbsDown,
  Minimize2,
  ArrowUp,
  Search,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../api/client';
import Spinner from '../components/common/Spinner';
import Modal from '../components/common/Modal';
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
  const [activeModal, setActiveModal] = useState(null);
  const [previewMobileTab, setPreviewMobileTab] = useState('research');

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
    <div className={styles.landing}>
      {/* ---- Navigation ---- */}
      <header className={styles.nav}>
        <div className={styles.navContainer}>
          <Link to="/" className={styles.brand} data-testid="header-brand">
            <div className={styles.brandLogoIcon}>▶</div>
            <span className={styles.brandName}>
              <span className={styles.brandYt}>Yt</span><span className={styles.brandGenius}>Genius</span>
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
              <button
                type="button"
                className={styles.navCta}
                onClick={handleContinueWithGoogle}
                disabled={isRedirecting}
                data-testid="nav-get-started-link"
              >
                Get Started
              </button>
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

        <h1 className={styles.heroHeadline}>
          Understand More.
          <br className={styles.headlineBreak} />
          Watch Less.
        </h1>

        <p className={styles.heroSubtitle}>
          Turn long videos into conversations. Ask questions, understand nuanced points, and jump
          directly to exact timestamps.
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
                Open YtGenius Workspace <ArrowRight size={16} />
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

        {/* ---- Product Preview Mockup (Illustrative Example) ---- */}
        <div className={styles.previewWrapper} id="preview" aria-label="YtGenius Application Preview">
          <div className={styles.previewBody}>
            {/* Mobile Workspace Top Header (Visible only on mobile <= 768px) */}
            <div className={styles.previewMobileBar}>
              <div className={styles.previewMobileMenuBtn} aria-hidden="true">
                <Menu size={16} />
              </div>
              <div className={styles.previewMobileBrand}>
                <span className={styles.brandYt}>Yt</span><span className={styles.brandGenius}>Genius</span>
                <span className={styles.previewBrandRedPlay}>▶</span>
              </div>
            </div>

            {/* Mobile Workspace Segmented Tabs: [ 🎬 Video Stage | 💬 Research ] (Visible only on mobile <= 768px) */}
            <div className={styles.previewMobileSegmentedBar}>
              <div className={styles.previewSegmentedControl}>
                <button
                  type="button"
                  className={`${styles.previewSegmentBtn} ${previewMobileTab === 'video' ? styles.previewSegmentBtnActive : ''}`}
                  onClick={() => setPreviewMobileTab('video')}
                  aria-label="Show video preview"
                >
                  🎬 Video Stage
                </button>
                <button
                  type="button"
                  className={`${styles.previewSegmentBtn} ${previewMobileTab === 'research' ? styles.previewSegmentBtnActive : ''}`}
                  onClick={() => setPreviewMobileTab('research')}
                  aria-label="Show research studio preview"
                >
                  💬 Research
                </button>
              </div>
            </div>

            {/* 1. Preview Left Sidebar */}
            <div className={styles.previewSidebar}>
              <div className={styles.previewSidebarBrand}>
                <div className={styles.previewBrandGroup}>
                  <div className={styles.previewBrandBadge}>▶</div>
                  <span className={styles.previewBrand}>
                    <span className={styles.brandYt}>Yt</span><span className={styles.brandGenius}>Genius</span>
                  </span>
                </div>
                <div className={styles.previewSidebarCollapseBtn} aria-label="Collapse sidebar">
                  ◀
                </div>
              </div>

              <div className={styles.previewNewChatBtn}>
                <span>+</span>
                <span>New Chat</span>
              </div>

              {/* Collapsed Conversations Section */}
              <div className={styles.previewSidebarSection}>
                <div className={styles.previewSectionHeader}>
                  <ChevronRight size={12} className={styles.previewSectionChevron} />
                  <span className={styles.previewSidebarSectionTitle}>CONVERSATIONS (6)</span>
                </div>
              </div>

              {/* Expanded Video Library Section */}
              <div className={styles.previewSidebarSection}>
                <div className={styles.previewLibraryHeaderRow}>
                  <div className={styles.previewSectionHeader}>
                    <ChevronDown size={12} className={styles.previewSectionChevron} />
                    <span className={styles.previewSidebarSectionTitle}>VIDEO LIBRARY (4)</span>
                  </div>
                  <span className={styles.previewAddLink}>+ Add</span>
                </div>

                {/* Library search bar */}
                <div className={styles.previewSearchWrap}>
                  <Search size={11} className={styles.previewSearchIcon} />
                  <span className={styles.previewSearchPlaceholder}>Search your library...</span>
                </div>

                {/* Status filter chips */}
                <div className={styles.previewFilterRow}>
                  <span className={`${styles.previewFilterChip} ${styles.previewFilterChipActive}`}>All</span>
                  <span className={styles.previewFilterChip}>Ready</span>
                  <span className={styles.previewFilterChip}>Processing</span>
                  <span className={styles.previewFilterChip}>Failed</span>
                </div>

                {/* 4 Video Library Items */}
                <div className={styles.previewVideoList}>
                  {/* Item 1: Active video */}
                  <div className={`${styles.previewVideoItem} ${styles.previewVideoItemActive}`}>
                    <div className={`${styles.previewVideoThumb} ${styles.previewThumbAi}`}>
                      <span className={styles.previewThumbPlay}>▶</span>
                    </div>
                    <div className={styles.previewVideoItemBody}>
                      <span className={styles.previewVideoItemTitle}>AI Engineering Full Cou...</span>
                      <div className={styles.previewVideoItemMeta}>
                        <span className={styles.previewStatusReady}>
                          <span className={styles.previewStatusDot} /> Ready
                        </span>
                        <span className={styles.previewChatCount}>💬 1 chat</span>
                      </div>
                    </div>
                  </div>

                  {/* Item 2 */}
                  <div className={styles.previewVideoItem}>
                    <div className={`${styles.previewVideoThumb} ${styles.previewThumbData}`}>
                      <span className={styles.previewThumbPlay}>▶</span>
                    </div>
                    <div className={styles.previewVideoItemBody}>
                      <span className={styles.previewVideoItemTitle}>WALMART Data Engine...</span>
                      <div className={styles.previewVideoItemMeta}>
                        <span className={styles.previewStatusReady}>
                          <span className={styles.previewStatusDot} /> Ready
                        </span>
                        <span className={styles.previewChatCount}>💬 2 chats</span>
                      </div>
                    </div>
                  </div>

                  {/* Item 3 */}
                  <div className={styles.previewVideoItem}>
                    <div className={`${styles.previewVideoThumb} ${styles.previewThumbRank}`}>
                      <span className={styles.previewThumbPlay}>▶</span>
                    </div>
                    <div className={styles.previewVideoItemBody}>
                      <span className={styles.previewVideoItemTitle}>RANK 1 Fireball Super...</span>
                      <div className={styles.previewVideoItemMeta}>
                        <span className={styles.previewStatusReady}>
                          <span className={styles.previewStatusDot} /> Ready
                        </span>
                        <span className={styles.previewChatCount}>💬 2 chats</span>
                      </div>
                    </div>
                  </div>

                  {/* Item 4 */}
                  <div className={styles.previewVideoItem}>
                    <div className={`${styles.previewVideoThumb} ${styles.previewThumbSql}`}>
                      <span className={styles.previewThumbPlay}>▶</span>
                    </div>
                    <div className={styles.previewVideoItemBody}>
                      <span className={styles.previewVideoItemTitle}>SQL Full Course 2026-...</span>
                      <div className={styles.previewVideoItemMeta}>
                        <span className={styles.previewStatusReady}>
                          <span className={styles.previewStatusDot} /> Ready
                        </span>
                        <span className={styles.previewChatCount}>💬 1 chat</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* User Profile Footer in Sidebar */}
              <div className={styles.previewSidebarUser}>
                <div className={styles.previewUserAvatar}>A</div>
                <div className={styles.previewUserInfo}>
                  <span className={styles.previewUserName}>Ash</span>
                  <span className={styles.previewUserEmail}>ash09876ik@gmail.com</span>
                </div>
                <ChevronUp size={13} className={styles.previewUserChevron} />
              </div>
            </div>

            {/* 2. Preview Center Video Player Stage */}
            <div className={`${styles.previewVideoStage} ${previewMobileTab === 'video' ? styles.previewPanelActive : styles.previewPanelHidden}`}>
              <div className={styles.previewPlayerBox}>
                {/* Header overlay inside video */}
                <div className={styles.previewPlayerHeaderOverlay}>
                  <div className={styles.previewChannelAvatar}>🌐</div>
                  <div className={styles.previewChannelMeta}>
                    <span className={styles.previewPlayerVideoTitle}>AI Engineering Full Course for Beginners</span>
                    <span className={styles.previewChannelName}>Tech With Mala</span>
                  </div>
                </div>

                {/* Banner illustration */}
                <div className={styles.previewPlayerBanner}>
                  <div className={styles.previewBannerContent}>
                    <div className={styles.previewBannerHeading}>AI ENGINEERING</div>
                    <div className={styles.previewBannerSub}>MASTER COURSE</div>
                    <div className={styles.previewBannerBadges}>
                      <span>LLMS</span>
                      <span className={styles.bannerArrow}>→</span>
                      <span>RAG</span>
                      <span className={styles.bannerArrow}>→</span>
                      <span>AGENTS</span>
                    </div>
                  </div>
                  <div className={styles.previewBannerAiGraphic} aria-hidden="true">
                    <div className={styles.previewBrainGlow} />
                  </div>
                </div>

                {/* Center YouTube Play Button */}
                <div className={styles.previewPlayerOverlay}>
                  <div className={styles.previewBigPlayBtn}>▶</div>
                </div>

                {/* Bottom Overlay Link & YouTube Pill */}
                <div className={styles.previewPlayerBottomOverlay}>
                  <div className={styles.previewPlayerLinkIcon} title="Video Link">🔗</div>
                  <div className={styles.previewPlayerYtBadge}>
                    <span>Watch on</span>
                    <span className={styles.previewYtLogo}>▶ YouTube</span>
                  </div>
                </div>
              </div>

              <div className={styles.previewVideoDetails}>
                <div className={styles.previewVideoTitleRow}>
                  <h4 className={styles.previewVideoMainTitle}>
                    AI Engineering Full Course for Beginners | LLMs, RAG, LangChain, Agents &amp; GenAI
                  </h4>
                  <span className={styles.previewReadyTag}>● Ready</span>
                </div>
                <div className={styles.previewVideoActions}>
                  <span className={styles.previewActionBtn}>
                    <ExternalLink size={11} /> Watch on YouTube
                  </span>
                  <span className={styles.previewActionBtn}>
                    Copy Link
                  </span>
                  <span className={styles.previewPlaybackIssuesLink}>
                    Playback issues?
                  </span>
                </div>
                <div className={styles.previewCollapsePlayerRow}>
                  <span className={styles.previewCollapsePlayerBtn}>
                    <Minimize2 size={11} /> Collapse Player
                  </span>
                </div>
                <div className={styles.previewMobileResearchSwitch}>
                  <button
                    type="button"
                    className={styles.previewMobileSwitchBtn}
                    onClick={() => setPreviewMobileTab('research')}
                  >
                    💬 Open AI Research Chat &amp; Citations →
                  </button>
                </div>
              </div>
            </div>

            {/* 3. Preview Right AI Research Studio */}
            <div className={`${styles.previewResearchStudio} ${previewMobileTab === 'research' ? styles.previewPanelActive : styles.previewPanelHidden}`}>
              <div className={styles.previewStudioHeader}>
                <div className={styles.previewStudioTitleWrap}>
                  <span className={styles.previewStudioTitle}>AI Research Studio</span>
                </div>
                <div className={styles.previewStudioActions}>
                  <span className={styles.previewNewChatMiniBtn}>+ New Chat</span>
                </div>
              </div>

              <div className={styles.previewChatFeed}>
                {/* Previous Turn Excerpt */}
                <div className={styles.previewAssistantTurn}>
                  <p className={styles.previewAnswerText}>
                    <strong>Start chatting</strong> – Send user messages to the chain; the LLM replies, and the conversation is recorded in memory for future turns.
                  </p>
                  <p className={styles.previewAnswerText}>
                    These steps collectively allow the chatbot to maintain context across interactions and generate coherent, context-aware responses.
                  </p>
                  <div className={styles.previewActionToolbar}>
                    <span className={styles.previewToolbarIconBtn} title="Copy">
                      <Copy size={12} />
                    </span>
                    <span className={styles.previewToolbarIconBtn} title="Helpful">
                      <ThumbsUp size={12} />
                    </span>
                    <span className={styles.previewToolbarIconBtn} title="Not helpful">
                      <ThumbsDown size={12} />
                    </span>
                  </div>
                </div>

                {/* Grounded Citations with Timestamp Chips */}
                <div className={styles.previewCitationsBlock}>
                  <div className={styles.previewCitationsHeading}>CITATIONS:</div>
                  <div className={styles.previewCitationsList}>
                    <div className={styles.previewCitationChip}>
                      <span className={styles.previewChipTime}>⏱ 04:52:12 - 04:53:08</span>
                      <span className={styles.previewChipSnippet}>And then here we ini...</span>
                    </div>
                    <div className={styles.previewCitationChip}>
                      <span className={styles.previewChipTime}>⏱ 05:34:52 - 05:35:45</span>
                      <span className={styles.previewChipSnippet}>somebody and you int...</span>
                    </div>
                    <div className={styles.previewCitationChip}>
                      <span className={styles.previewChipTime}>⏱ 05:48:23 - 05:49:23</span>
                      <span className={styles.previewChipSnippet}>we installed all the...</span>
                    </div>
                  </div>
                </div>

                {/* User Message on Right */}
                <div className={styles.previewUserMessage}>
                  <span>How can AI agents use tools to perform tasks?</span>
                </div>

                {/* Assistant Flowing Response */}
                <div className={styles.previewAssistantTurn}>
                  <p className={styles.previewAnswerText}>
                    AI agents perform tasks by calling external utilities called tools. A tool is a LangChain-based utility that can interact with outside systems—such as web crawlers, search engines, or browser automation tools. When you define a task, you pass a list of tools to the task constructor. The agent assigned to that task can then invoke those tools to execute the required actions (e.g., crawl a web page, scrape a site, or download an email). The crew framework orchestrates the agents, tasks, and tools; when the crew is started, each agent runs its task and uses the specified tools to carry out the work.
                  </p>
                </div>
              </div>

              {/* Composer at Bottom */}
              <div className={styles.previewComposer}>
                <div className={styles.previewComposerBar}>
                  <span className={styles.previewComposerPlaceholder}>Ask anything about this video...</span>
                  <div className={styles.previewSendBtn}>
                    <ArrowUp size={13} />
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
          <h2 className={styles.sectionTitle}>Engineered for Deep Video Understanding</h2>
          <p className={styles.sectionDesc}>
            Built specifically for lectures, podcasts, technical interviews, and deep tutorials that
            contain hours of critical knowledge.
          </p>
        </div>

        <div className={styles.featuresGrid}>
          <div className={styles.featureCard}>
            <div className={styles.featureIconBox}>
              <MessageSquare size={20} />
            </div>
            <h3 className={styles.featureTitle}>1. Ask anything</h3>
            <p className={styles.featureText}>
              Ask questions about video content naturally. YtGenius searches transcript passages and
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
            <h2 className={styles.sectionTitle}>How YtGenius works</h2>
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
                Drop in any public YouTube video link. YtGenius retrieves metadata and prepares the
                transcript for indexing.
              </p>
            </div>

            <div className={styles.stepCard}>
              <div className={styles.stepNumber}>02</div>
              <h3 className={styles.stepTitle}>YtGenius processes it</h3>
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
        <h2 className={styles.finalCtaHeadline}>Start with YtGenius</h2>
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

      {/* ---- Footer (Appropriate for Final-Year Student Project) ---- */}
      <footer className={styles.footer}>
        <div className={styles.footerContainer}>
          <div className={styles.footerGrid}>
            {/* Col 1: Project Identity & Developer Attribution */}
            <div className={styles.footerBrandCol}>
              <div className={styles.footerBrand}>
                <div className={styles.brandLogoIconSmall}>▶</div>
                <span className={styles.footerBrandName}>
                  <span className={styles.brandYt}>Yt</span><span className={styles.brandGenius}>Genius</span>
                </span>
              </div>
              <p className={styles.footerTagline}>
                Intelligent YouTube video Q&amp;A system grounded strictly in transcript context with interactive timestamp citations.
              </p>
              <p className={styles.footerAttribution}>
                Final-Year Engineering Project
                <br />
                <span className={styles.footerAuthor}>Developed by Ashik Raj</span>
              </p>
              <div className={styles.footerSocial}>
                <a
                  href="https://github.com/rajashik-web/youtube-qa-assistant"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.socialLink}
                  aria-label="YtGenius on GitHub"
                  data-testid="footer-github-link"
                  title="Source Code on GitHub"
                >
                  <Github size={16} />
                </a>
                <a
                  href="https://www.linkedin.com/in/ashik-raj-000598396"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.socialLink}
                  aria-label="Ashik Raj on LinkedIn"
                  data-testid="footer-linkedin-link"
                  title="Ashik Raj on LinkedIn"
                >
                  <Linkedin size={16} />
                </a>
              </div>
            </div>

            {/* Col 2: Product */}
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
                How It Works
              </a>
              <button
                type="button"
                className={styles.footerLinkBtn}
                onClick={handleContinueWithGoogle}
                disabled={isRedirecting}
                data-testid="footer-get-started-btn"
              >
                Get Started
              </button>
            </div>

            {/* Col 3: Resources & Tech Stack */}
            <div className={styles.footerCol}>
              <h3 className={styles.footerColTitle}>Resources</h3>
              <a
                href="https://github.com/rajashik-web/youtube-qa-assistant"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.footerLink}
                data-testid="footer-repo-link"
              >
                GitHub Repository
              </a>
              <a
                href="https://github.com/rajashik-web/youtube-qa-assistant#readme"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.footerLink}
                data-testid="footer-docs-link"
              >
                Documentation
              </a>
              <button
                type="button"
                className={styles.footerLinkBtn}
                onClick={() => setActiveModal('tech')}
                data-testid="footer-tech-stack-btn"
              >
                Technology Stack
              </button>
            </div>

            {/* Col 4: Legal & Notice */}
            <div className={styles.footerCol}>
              <h3 className={styles.footerColTitle}>Legal &amp; Notice</h3>
              <button
                type="button"
                className={styles.footerLinkBtn}
                onClick={() => setActiveModal('privacy')}
                data-testid="footer-privacy-btn"
              >
                Privacy Policy
              </button>
              <button
                type="button"
                className={styles.footerLinkBtn}
                onClick={() => setActiveModal('terms')}
                data-testid="footer-terms-btn"
              >
                Terms of Service
              </button>
              <button
                type="button"
                className={styles.footerLinkBtn}
                onClick={() => setActiveModal('academic')}
                data-testid="footer-academic-btn"
              >
                Academic Notice
              </button>
            </div>
          </div>

          <div className={styles.footerBottom}>
            <p className={styles.footerMeta}>© {new Date().getFullYear()} YtGenius • Ashik Raj. All rights reserved.</p>
            <p className={styles.footerMeta}>Academic Capstone Project • Built with React, FastAPI, Qdrant &amp; Groq.</p>
          </div>
        </div>
      </footer>

      {/* Privacy Policy Modal */}
      <Modal
        isOpen={activeModal === 'privacy'}
        onClose={() => setActiveModal(null)}
        title="Privacy Policy"
        cancelLabel="Close"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', lineHeight: '1.5', maxHeight: '350px', overflowY: 'auto' }}>
          <p>
            At YtGenius, data privacy and transparency are fundamental design principles:
          </p>
          <p>
            <strong>1. Ephemeral Query Processing:</strong> Questions submitted to YtGenius are processed in volatile server memory solely to perform retrieval and synthesize transcript citations. User inquiries are never sold or used for public AI model training.
          </p>
          <p>
            <strong>2. Canonical Transcript Caching:</strong> Public closed captions from YouTube are indexed to enable semantic search and timestamp citations. Transcripts are cached locally to minimize redundant external API roundtrips.
          </p>
          <p>
            <strong>3. User Data Ownership:</strong> You retain full rights to your conversation history. You can view, export, or permanently erase your history and account at any time via Settings.
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
            By using YtGenius, you agree to the following conditions:
          </p>
          <p>
            <strong>1. YouTube Developer Terms Compliance:</strong> YtGenius accesses publicly available YouTube metadata and closed captions in accordance with YouTube Developer policies. Video playback occurs via the official embedded YouTube player.
          </p>
          <p>
            <strong>2. Grounded Answers:</strong> AI summaries and answers are derived algorithmically based on retrieved transcript text. Users should review critical assertions against source timestamps.
          </p>
          <p>
            <strong>3. Educational &amp; Research Use:</strong> This application is intended for personal research, educational study, and engineering demonstration. Automated abusive querying or scraping is prohibited.
          </p>
        </div>
      </Modal>

      {/* Technology Stack Modal */}
      <Modal
        isOpen={activeModal === 'tech'}
        onClose={() => setActiveModal(null)}
        title="System Architecture &amp; Technology Stack"
        cancelLabel="Close"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px', lineHeight: '1.5', maxHeight: '350px', overflowY: 'auto' }}>
          <p>
            YtGenius is engineered with a modern high-performance decoupled architecture:
          </p>
          <div>
            <strong style={{ color: 'var(--text-primary)' }}>• Frontend:</strong>
            <p style={{ margin: '2px 0 0', color: 'var(--text-secondary)' }}>
              React 18, Vite, React Router, CSS Modules with custom dark design system and responsive layout.
            </p>
          </div>
          <div>
            <strong style={{ color: 'var(--text-primary)' }}>• Backend API:</strong>
            <p style={{ margin: '2px 0 0', color: 'var(--text-secondary)' }}>
              Python FastAPI with asynchronous endpoints, SQLAlchemy ORM, and JWT + Google OAuth 2.0 authentication.
            </p>
          </div>
          <div>
            <strong style={{ color: 'var(--text-primary)' }}>• Vector &amp; Relational Storage:</strong>
            <p style={{ margin: '2px 0 0', color: 'var(--text-secondary)' }}>
              Qdrant Cloud vector database for fast semantic similarity search over transcript chunks; PostgreSQL for relational user and conversation state.
            </p>
          </div>
          <div>
            <strong style={{ color: 'var(--text-primary)' }}>• AI &amp; Embeddings:</strong>
            <p style={{ margin: '2px 0 0', color: 'var(--text-secondary)' }}>
              SentenceTransformers (all-MiniLM-L6-v2) for 384-dimensional dense embeddings and Groq LLM API for low-latency cited synthesis.
            </p>
          </div>
        </div>
      </Modal>

      {/* Academic Notice Modal */}
      <Modal
        isOpen={activeModal === 'academic'}
        onClose={() => setActiveModal(null)}
        title="Academic Project Information"
        cancelLabel="Close"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', lineHeight: '1.5' }}>
          <p>
            <strong>Final-Year Engineering Capstone Project</strong>
          </p>
          <p style={{ color: 'var(--text-secondary)' }}>
            YtGenius was conceived, designed, and developed by <strong>Ashik Raj</strong> as an undergraduate final-year engineering capstone project.
          </p>
          <p style={{ color: 'var(--text-secondary)' }}>
            This project explores vector retrieval-augmented generation (RAG), transcript segmentation algorithms, and citation verification for long-form video knowledge extraction.
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '4px' }}>
            Disclaimer: YtGenius is an independent student academic project and is not affiliated with, sponsored by, or endorsed by Google LLC or YouTube.
          </p>
        </div>
      </Modal>
    </div>
  );
}
