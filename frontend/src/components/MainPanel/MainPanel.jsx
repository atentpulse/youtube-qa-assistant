import React, { useRef, useEffect, useState, useMemo } from "react";
import { useVideoLibrary } from "../../context/VideoLibraryContext";
import { useConversations } from "../../context/ConversationContext";
import { useUI } from "../../context/UIContext";
import { useChat } from "../../context/ChatContext";
import { VIDEO_STATUS } from "../../utils/constants";
import MessageBubble from "./MessageBubble";
import UrlComposer from "./UrlComposer";
import VideoPlayer from "../VideoPlayer/VideoPlayer";
import ConversationSelectionView from "./ConversationSelectionView";
import Spinner from "../common/Spinner";
import Skeleton from "../common/Skeleton";
import { MessageSquare } from "lucide-react";
import styles from "./MainPanel.module.css";

const STARTER_PROMPTS = [
  "Summarize key takeaways in 3 bullet points",
  "Explain the core concept and methodology",
  "What are the main formulas and definitions?",
];

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
      <path
        d="M3 12h18M3 6h18M3 18h18"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function QAComposer({ videoId, hasMessages }) {
  const [question, setQuestion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { askAboutVideo } = useChat();
  const textareaRef = useRef(null);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isSubmitting) return;
    setQuestion("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    setIsSubmitting(true);
    try {
      await askAboutVideo(videoId, trimmed);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInputChange = (e) => {
    setQuestion(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  };

  const handleSelectStarter = (prompt) => {
    setQuestion(prompt);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  return (
    <div className={styles.composerWrap}>
      {/* Starter Prompts with static pinned label and hidden scrollbar */}
      {!hasMessages && (
        <div className={styles.startersWrap}>
          <span className={styles.startersLabel}>Suggested:</span>
          <div className={styles.startersScroll}>
            {STARTER_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                className={styles.starterChip}
                onClick={() => handleSelectStarter(prompt)}
              >
                💡 {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      <div
        className={`${styles.composerBar} ${isSubmitting ? styles.composerBarDisabled : ""}`}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          value={question}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about this video…"
          disabled={isSubmitting}
          className={styles.composerInput}
          aria-label="Ask a question about this video"
          data-testid="question-input"
        />
        <button
          type="button"
          className={styles.composerSubmit}
          disabled={isSubmitting || !question.trim()}
          onClick={handleSubmit}
          aria-label="Send question"
          data-testid="question-submit-button"
        >
          {isSubmitting ? (
            <Spinner size={15} />
          ) : (
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none">
              <path
                d="M12 19V5M12 5L6 11M12 5L18 11"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </button>
      </div>

      <div className={styles.composerFooterText}>
        <span>Press Enter to send, Shift+Enter for newline</span>
      </div>
    </div>
  );
}

export default function MainPanel() {
  const { selectedVideo, libraryStatus, reprocessVideo } = useVideoLibrary();
  const {
    conversations,
    activeConversationId,
    selectConversation,
    clearActiveConversation,
  } = useConversations();
  const {
    isComposerOpen,
    closeComposer,
    openMobileSidebar,
    selectionVideoId,
    openConversationSelection,
    closeConversationSelection,
  } = useUI();
  const { getThread, clearThread } = useChat();
  const threadEndRef = useRef(null);
  const playerRef = useRef(null);
  const [mobileTab, setMobileTab] = useState("video"); // 'video' | 'research'

  // Derive thread using the same key logic as ChatContext
  const activeConvKey = activeConversationId
    ? `conv_${activeConversationId}`
    : `draft_${selectedVideo?.video_id || "default"}`;

  const thread = activeConvKey ? getThread(activeConvKey) : [];

  // Filter conversations belonging to the currently selected video
  const videoConversations = useMemo(() => {
    if (!selectedVideo?.video_id) return [];
    return conversations.filter((c) => c.video_id === selectedVideo.video_id);
  }, [conversations, selectedVideo?.video_id]);

  // Auto-scroll to bottom when new messages arrive.
  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread.length]);

  const isReady =
    selectedVideo &&
    (selectedVideo.status === VIDEO_STATUS.PROCESSED ||
      selectedVideo.status === VIDEO_STATUS.ALREADY_PROCESSED);

  const isProcessing = selectedVideo?.status === VIDEO_STATUS.PROCESSING;
  const isFailed = selectedVideo?.status === VIDEO_STATUS.FAILED;

  const handleSeek = (seconds) => {
    playerRef.current?.seekTo(seconds);
    if (typeof window !== "undefined" && window.innerWidth <= 768) {
      setMobileTab("video");
    }
  };

  // Section 4: Start a new conversation within the same video
  const handleNewConversationForVideo = () => {
    clearActiveConversation();
    closeConversationSelection();
    if (selectedVideo?.video_id) {
      clearThread(`draft_${selectedVideo.video_id}`);
    }
  };

  // Selecting a conversation from Case 3 selection view
  const handleSelectFromPicker = (convId) => {
    selectConversation(convId);
    closeConversationSelection();
  };

  return (
    <main className={styles.main}>
      {/* Mobile top header bar */}
      <div className={styles.mobileBar}>
        <button
          type="button"
          className={styles.mobileMenuBtn}
          onClick={openMobileSidebar}
          aria-label="Open sidebar"
        >
          <MenuIcon />
        </button>
        <span className={styles.mobileBrand}>
          <span className={styles.brandYt}>Yt</span><span className={styles.brandGenius}>Genius</span>
        </span>
      </div>

      {/* Workspace Loading Skeletons */}
      {libraryStatus === "loading" && (
        <div className={styles.workspaceLoadingSkeleton} aria-label="Loading workspace">
          <div className={styles.dualPanelSplit}>
            <div className={styles.videoStageWrap}>
              <div style={{ padding: "16px" }}>
                <Skeleton variant="video" style={{ marginBottom: "16px" }} />
                <Skeleton variant="text" width="80%" height="18px" style={{ marginBottom: "8px" }} />
                <Skeleton variant="text" width="45%" height="14px" style={{ marginBottom: "16px" }} />
                <div style={{ display: "flex", gap: "8px" }}>
                  <Skeleton width="120px" height="28px" borderRadius="6px" />
                  <Skeleton width="90px" height="28px" borderRadius="6px" />
                </div>
              </div>
            </div>
            <div className={styles.researchStudioWrap}>
              <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <Skeleton width="65%" height="42px" borderRadius="16px" />
                </div>
                <div style={{ display: "flex", gap: "12px" }}>
                  <Skeleton variant="circle" width="28px" height="28px" />
                  <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "8px" }}>
                    <Skeleton variant="text" width="90%" height="14px" />
                    <Skeleton variant="text" width="75%" height="14px" />
                    <Skeleton variant="text" width="50%" height="14px" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* No video selected — clean dashboard welcome / empty state */}
      {libraryStatus !== "loading" && !selectedVideo && !isComposerOpen && (
        <div className={styles.dashboardWelcome} data-testid="dashboard-empty-state">
          <img src="/logo.svg" alt="" className={styles.welcomeLogo} />
          <h2 className={styles.welcomeTitle}>Welcome to YtGenius</h2>
          <p className={styles.welcomeBody}>
            Select a video from your library to start asking questions — or add a
            new YouTube video to get started.
          </p>
          <UrlComposer variant="welcome" />
        </div>
      )}

      {/* Composer panel (Add video / New chat) */}
      {isComposerOpen && (
        <UrlComposer variant="panel" onClose={closeComposer} />
      )}

      {/* Dual-Panel Video Workspace */}
      {selectedVideo && !isComposerOpen && (
        <div className={styles.workspace} data-testid="video-workspace">
          {/* Mobile Segmented Bar: [ 🎬 Video | 💬 Research ] */}
          <div className={styles.mobileSegmentedBar}>
            <div className={styles.segmentedControl}>
              <button
                type="button"
                className={`${styles.segmentBtn} ${mobileTab === "video" ? styles.segmentBtnActive : ""}`}
                onClick={() => setMobileTab("video")}
                data-testid="mobile-tab-video"
              >
                🎬 Video Stage
              </button>
              <button
                type="button"
                className={`${styles.segmentBtn} ${mobileTab === "research" ? styles.segmentBtnActive : ""}`}
                onClick={() => setMobileTab("research")}
                data-testid="mobile-tab-research"
              >
                💬 Research {thread.length > 0 ? `(${thread.length})` : ""}
              </button>
            </div>
          </div>

          {/* 38% / 62% Dual-Panel Stage */}
          <div className={styles.dualPanelSplit}>
            {/* Left Stage: 38% Video Player Stage */}
            <div
              className={`${styles.videoStageWrap} ${
                mobileTab === "video" ? styles.mobilePanelActive : styles.mobilePanelHidden
              }`}
            >
              <VideoPlayer
                ref={playerRef}
                video={selectedVideo}
                reprocessVideo={reprocessVideo}
                onSwitchToResearch={() => setMobileTab("research")}
              />
            </div>

            {/* Right Stage: 62% AI Research Studio */}
            <div
              className={`${styles.researchStudioWrap} ${
                mobileTab === "research" ? styles.mobilePanelActive : styles.mobilePanelHidden
              }`}
            >
              {/* Case 3: Conversation Selection View for this video */}
              {selectionVideoId && selectionVideoId === selectedVideo.video_id ? (
                <ConversationSelectionView
                  video={selectedVideo}
                  conversations={videoConversations}
                  activeConversationId={activeConversationId}
                  onSelectConversation={handleSelectFromPicker}
                  onNewConversation={handleNewConversationForVideo}
                />
              ) : (
                <>
                  {/* Studio Header Bar */}
                  <div className={styles.studioHeader}>
                    <div className={styles.studioHeaderTitle}>
                      <span>AI Research Studio</span>
                    </div>

                    <div className={styles.studioHeaderActions}>
                      {/* Section 3 Case 3 / Switch conversation action */}
                      {videoConversations.length > 1 && (
                        <button
                          type="button"
                          className={styles.studioHeaderBtn}
                          onClick={() => openConversationSelection(selectedVideo.video_id)}
                          title="View all conversations for this video"
                          data-testid="view-all-video-chats-button"
                        >
                          <MessageSquare size={12} />
                          <span>All Chats ({videoConversations.length})</span>
                        </button>
                      )}

                      {/* Section 4: New Conversation within current video */}
                      <button
                        type="button"
                        className={`${styles.studioHeaderBtn} ${styles.studioHeaderBtnPrimary}`}
                        onClick={handleNewConversationForVideo}
                        title="Start a new conversation for this video"
                        data-testid="new-conversation-for-video-button"
                      >
                        <span>+ New Chat</span>
                      </button>
                    </div>
                  </div>

                  {/* Message Thread */}
                  <div className={styles.threadWrap}>
                    {isProcessing && (
                      <div className={styles.centerState}>
                        <Spinner size={24} />
                        <p>
                          Processing this video… it&apos;ll be ready to chat with shortly.
                        </p>
                      </div>
                    )}

                    {isFailed && (
                      <div className={styles.centerState}>
                        <p className={styles.errorText}>
                          This video failed to process.
                        </p>
                        <button
                          type="button"
                          className={styles.retryLink}
                          style={{ marginTop: "8px", cursor: "pointer" }}
                          data-testid="retry-processing-button"
                          onClick={() =>
                            reprocessVideo(
                              selectedVideo.video_id,
                              selectedVideo.url || `https://www.youtube.com/watch?v=${selectedVideo.video_id}`
                            )
                          }
                        >
                          Retry processing video
                        </button>
                      </div>
                    )}

                    {isReady && thread.length === 0 && (
                      <div className={styles.emptyThread} data-testid="empty-thread">
                        <p className={styles.emptyThreadTitle}>
                          Ready to answer questions
                        </p>
                        <p className={styles.emptyThreadBody}>
                          Ask anything about{" "}
                          <strong>{selectedVideo.title || "this video"}</strong> below.
                        </p>
                      </div>
                    )}

                    {thread.map((message) => (
                      <MessageBubble
                        key={message.id}
                        message={message}
                        onSeek={handleSeek}
                      />
                    ))}
                    <div ref={threadEndRef} />
                  </div>

                  {/* Docked Question Composer */}
                  {isReady && (
                    <QAComposer
                      videoId={selectedVideo.video_id}
                      hasMessages={thread.length > 0}
                    />
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
