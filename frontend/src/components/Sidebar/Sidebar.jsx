import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import VideoLibraryItem from './VideoLibraryItem';
import ConversationItem from './ConversationItem';
import Modal from '../common/Modal';
import Tooltip from '../common/Tooltip';
import Skeleton from '../common/Skeleton';
import UserProfileDropdown from './UserProfileDropdown';
import { MessageSquare, Film, ChevronRight } from 'lucide-react';
import { useVideoLibrary } from '../../context/VideoLibraryContext';
import { useConversations } from '../../context/ConversationContext';
import { useChat } from '../../context/ChatContext';
import { useUI } from '../../context/UIContext';
import { useAuth } from '../../context/AuthContext';
import { VIDEO_STATUS } from '../../utils/constants';
import styles from './Sidebar.module.css';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: VIDEO_STATUS.PROCESSED, label: 'Ready' },
  { key: VIDEO_STATUS.PROCESSING, label: 'Processing' },
  { key: VIDEO_STATUS.FAILED, label: 'Failed' },
];

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none">
      <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export default function Sidebar() {
  const navigate = useNavigate();
  const { videos, libraryStatus, libraryError, fetchVideos, selectedVideoId, selectVideo } = useVideoLibrary();
  const {
    conversations,
    conversationsStatus,
    conversationsError,
    loadConversations,
    activeConversationId,
    selectConversation,
    clearActiveConversation,
  } = useConversations();
  const { clearThread } = useChat();
  const {
    openComposer,
    closeComposer,
    openConversationSelection,
    closeConversationSelection,
    isMobileSidebarOpen,
    closeMobileSidebar,
    isSidebarCollapsed,
    toggleSidebarCollapse,
  } = useUI();
  const { logout } = useAuth();

  // Search & filter state
  const [convQuery, setConvQuery] = useState('');
  const [videoQuery, setVideoQuery] = useState('');
  const [filter, setFilter] = useState('all');

  // Conversations is collapsed by default per specification (independent state, persisted in localStorage)
  const [isConversationsExpanded, setIsConversationsExpanded] = useState(() => {
    try {
      const saved = localStorage.getItem('ytgenius_sidebar_convs_expanded');
      return saved === 'true'; // false by default
    } catch {
      return false;
    }
  });

  // Video Library is expanded by default per specification (independent state, persisted in localStorage)
  const [isLibraryExpanded, setIsLibraryExpanded] = useState(() => {
    try {
      const saved = localStorage.getItem('ytgenius_sidebar_library_expanded');
      return saved !== 'false'; // true by default
    } catch {
      return true;
    }
  });

  const toggleConversations = () => {
    setIsConversationsExpanded((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('ytgenius_sidebar_convs_expanded', String(next));
      } catch (_err) {
        // Ignore storage errors in restricted contexts
      }
      return next;
    });
  };

  const toggleLibrary = () => {
    setIsLibraryExpanded((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('ytgenius_sidebar_library_expanded', String(next));
      } catch (_err) {
        // Ignore storage errors in restricted contexts
      }
      return next;
    });
  };

  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);

  // Fast lookup for video title by video_id
  const videoMap = useMemo(() => {
    return new Map(videos.map((v) => [v.video_id, v.title]));
  }, [videos]);

  // Fast lookup for conversation count by video_id
  const convCountMap = useMemo(() => {
    const map = {};
    conversations.forEach((c) => {
      if (c.video_id) {
        map[c.video_id] = (map[c.video_id] || 0) + 1;
      }
    });
    return map;
  }, [conversations]);

  // Flat list of conversations filtered by search query
  const filteredConversations = useMemo(() => {
    if (!convQuery.trim()) return conversations;
    const q = convQuery.toLowerCase().trim();
    return conversations.filter((c) => {
      const title = (c.title || '').toLowerCase();
      const videoTitle = (c.video_title || videoMap.get(c.video_id) || '').toLowerCase();
      const videoId = (c.video_id || '').toLowerCase();
      return title.includes(q) || videoTitle.includes(q) || videoId.includes(q);
    });
  }, [conversations, convQuery, videoMap]);

  // Video library list filtered by query and status
  const filteredVideos = useMemo(() => {
    return videos.filter((v) => {
      const matchesQuery =
        !videoQuery.trim() || (v.title || '').toLowerCase().includes(videoQuery.trim().toLowerCase());
      const matchesFilter =
        filter === 'all' ||
        v.status === filter ||
        (filter === VIDEO_STATUS.PROCESSED && v.status === VIDEO_STATUS.ALREADY_PROCESSED);
      return matchesQuery && matchesFilter;
    });
  }, [videos, videoQuery, filter]);

  // Global New Chat button action (Section 5)
  const handleNewChat = () => {
    openComposer('new_chat');
    closeConversationSelection();
    closeMobileSidebar();
  };

  // Add video action inside Video Library (Section 6)
  const handleNewVideo = (e) => {
    e?.stopPropagation();
    openComposer('add_video');
    closeConversationSelection();
    closeMobileSidebar();
  };

  // Selecting a conversation from the flat recent list (Section 2.A)
  const handleSelectConversation = (conversationId) => {
    selectConversation(conversationId);
    closeConversationSelection();
    closeComposer();
    closeMobileSidebar();
  };

  // Clicking a video in Video Library: Case 1, Case 2, Case 3 (Section 3)
  const handleSelectVideo = (video) => {
    const videoConvs = conversations.filter((c) => c.video_id === video.video_id);
    selectVideo(video.video_id);
    closeComposer();
    closeMobileSidebar();

    if (videoConvs.length === 0) {
      // Case 1: No existing conversations -> fresh empty conversation state
      clearActiveConversation();
      closeConversationSelection();
    } else if (videoConvs.length === 1) {
      // Case 2: Exactly one existing conversation -> open directly
      selectConversation(videoConvs[0].id);
      closeConversationSelection();
    } else {
      // Case 3: Multiple existing conversations -> open conversation-selection view
      clearActiveConversation();
      openConversationSelection(video.video_id);
    }
  };

  const handleConfirmLogout = () => {
    setIsLogoutModalOpen(false);
    clearActiveConversation();
    if (selectedVideoId) {
      clearThread(`draft_${selectedVideoId}`);
    }
    logout();
    navigate('/', { replace: true });
  };

  return (
    <>
      {isMobileSidebarOpen && (
        <div className={styles.backdrop} onClick={closeMobileSidebar} aria-hidden="true" />
      )}

      <aside
        className={`${styles.sidebar} ${isSidebarCollapsed ? styles.sidebarCollapsed : ''} ${
          isMobileSidebarOpen ? styles.sidebarOpen : ''
        }`}
        role="navigation"
        aria-label="Workspace sidebar"
      >
        {/* ---- Brand & Collapse Row ---- */}
        <div className={styles.brandRow}>
          {isSidebarCollapsed ? (
            <Tooltip content="Expand sidebar">
              <button
                type="button"
                className={styles.brandIconBtnCollapsed}
                onClick={toggleSidebarCollapse}
                aria-label="Expand sidebar"
                title="Expand sidebar"
              >
                ▶
              </button>
            </Tooltip>
          ) : (
            <>
              <div className={styles.brandGroup}>
                <div className={styles.brandIcon} aria-hidden="true">
                  ▶
                </div>
                <div className={styles.brandText}>
                  <span className={styles.brandName}>
                    <span className={styles.brandYt}>Yt</span><span className={styles.brandGenius}>Genius</span>
                  </span>
                </div>
              </div>

              <Tooltip content="Collapse sidebar">
                <button
                  type="button"
                  className={styles.collapseButton}
                  onClick={toggleSidebarCollapse}
                  aria-label="Collapse sidebar"
                  title="Collapse sidebar"
                >
                  ◀
                </button>
              </Tooltip>
            </>
          )}

          <button
            type="button"
            className={styles.mobileCloseButton}
            onClick={closeMobileSidebar}
            aria-label="Close sidebar"
          >
            ×
          </button>
        </div>

        {/* ---- Pinned Top Action: New Chat (Section 5) ---- */}
        <div className={styles.pinnedActionWrap}>
          {isSidebarCollapsed ? (
            <Tooltip content="New Chat">
              <button
                type="button"
                className={styles.newChatButtonCollapsed}
                onClick={handleNewChat}
                aria-label="Start a new chat"
                data-testid="new-chat-button"
              >
                <PlusIcon />
              </button>
            </Tooltip>
          ) : (
            <button
              type="button"
              className={styles.newChatButton}
              onClick={handleNewChat}
              aria-label="Start a new chat"
              data-testid="new-chat-button"
            >
              <PlusIcon />
              <span>New Chat</span>
            </button>
          )}
        </div>

        {/* ---- Scrollable Container ---- */}
        <div className={styles.scrollableBody}>
          {isSidebarCollapsed ? (
            <div className={styles.collapsedNavRail}>
              <Tooltip content="Conversations">
                <button
                  type="button"
                  className={styles.collapsedNavBtn}
                  onClick={toggleSidebarCollapse}
                  aria-label="Conversations"
                >
                  <MessageSquare size={16} />
                </button>
              </Tooltip>
              <Tooltip content="Video Library">
                <button
                  type="button"
                  className={styles.collapsedNavBtn}
                  onClick={toggleSidebarCollapse}
                  aria-label="Video Library"
                >
                  <Film size={16} />
                </button>
              </Tooltip>
              {selectedVideoId && (
                <Tooltip
                  content={`Active: ${
                    videos.find((v) => v.video_id === selectedVideoId)?.title || selectedVideoId
                  }`}
                >
                  <button
                    type="button"
                    className={styles.collapsedActiveVideoBtn}
                    onClick={toggleSidebarCollapse}
                    aria-label="Active video"
                  >
                    {videos.find((v) => v.video_id === selectedVideoId)?.thumbnail_url ? (
                      <img
                        src={videos.find((v) => v.video_id === selectedVideoId)?.thumbnail_url}
                        alt=""
                        className={styles.collapsedVideoThumb}
                      />
                    ) : (
                      <Film size={14} />
                    )}
                  </button>
                </Tooltip>
              )}
              <div className={styles.collapsedRailDivider} />
            </div>
          ) : (
            <>
              {/* ---- A. Conversations Section (Collapsible, Collapsed by Default) ---- */}
              <div className={styles.sectionHeader}>
                <button
                  type="button"
                  className={styles.sectionToggleBtn}
                  onClick={toggleConversations}
                  aria-expanded={isConversationsExpanded}
                  aria-label="Toggle Conversations section"
                  data-testid="toggle-conversations-button"
                >
                  <span
                    className={`${styles.sectionChevron} ${
                      isConversationsExpanded ? styles.sectionChevronExpanded : ''
                    }`}
                  >
                    <ChevronRight size={14} />
                  </span>
                  <span className={styles.sectionTitle}>Conversations</span>
                  {conversations.length > 0 && (
                    <span className={styles.itemCount}>({conversations.length})</span>
                  )}
                </button>
              </div>

              {isConversationsExpanded && (
                <div className={styles.conversationsExpandedContent} data-testid="conversations-content">
                  {conversations.length > 3 && (
                    <div className={styles.conversationSearchRow}>
                      <input
                        type="search"
                        placeholder="Search conversations…"
                        value={convQuery}
                        onChange={(e) => setConvQuery(e.target.value)}
                        className={styles.searchInput}
                        aria-label="Search conversations"
                        data-testid="conversation-search-input"
                      />
                    </div>
                  )}

                  <div className={styles.conversationListWrap}>
                    {conversationsStatus === 'loading' && (
                      <div className={styles.skeletonList}>
                        <Skeleton height={38} borderRadius={6} style={{ marginBottom: 6 }} />
                        <Skeleton height={38} borderRadius={6} style={{ marginBottom: 6 }} />
                        <Skeleton height={38} borderRadius={6} style={{ marginBottom: 6 }} />
                      </div>
                    )}

                    {conversationsStatus === 'error' && (
                      <div className={styles.stateBlock}>
                        <p className={styles.stateError}>{conversationsError}</p>
                        <button
                          type="button"
                          className={styles.retryButton}
                          onClick={loadConversations}
                        >
                          Try again
                        </button>
                      </div>
                    )}

                    {conversationsStatus === 'ready' && conversations.length === 0 && (
                      <div className={styles.stateBlock}>
                        <p className={styles.emptyBody}>
                          No conversations yet. Start a new chat to get started.
                        </p>
                      </div>
                    )}

                    {conversations.length > 0 && filteredConversations.length === 0 && (
                      <div className={styles.stateBlock}>
                        <p className={styles.emptyBody}>No conversations match search.</p>
                      </div>
                    )}

                    {filteredConversations.length > 0 && (
                      <ul className={styles.list} data-testid="conversations-flat-list">
                        {filteredConversations.map((conv) => (
                          <ConversationItem
                            key={conv.id}
                            conversation={conv}
                            videoTitle={conv.video_title || videoMap.get(conv.video_id)}
                            isActive={conv.id === activeConversationId}
                            onSelect={() => handleSelectConversation(conv.id)}
                            isCollapsed={false}
                          />
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}

              <div className={styles.sectionDivider} />

              {/* ---- B. Video Library Section (Collapsible, Expanded by Default) ---- */}
              <div className={styles.sectionHeader}>
                <button
                  type="button"
                  className={styles.libraryToggleBtn}
                  onClick={toggleLibrary}
                  aria-expanded={isLibraryExpanded}
                  aria-label="Toggle Video Library section"
                  data-testid="toggle-video-library-button"
                >
                  <span
                    className={`${styles.libraryChevron} ${
                      isLibraryExpanded ? styles.libraryChevronExpanded : ''
                    }`}
                  >
                    <ChevronRight size={14} />
                  </span>
                  <span className={styles.sectionTitle}>Video Library</span>
                  {videos.length > 0 && (
                    <span className={styles.itemCount}>({videos.length})</span>
                  )}
                </button>

                <button
                  type="button"
                  className={styles.addVideoButton}
                  onClick={handleNewVideo}
                  aria-label="Add a YouTube video to library"
                  title="Add video to library"
                  data-testid="add-video-button"
                >
                  <PlusIcon />
                  Add
                </button>
              </div>

              {/* Content visible only when expanded */}
              {isLibraryExpanded && (
                <div className={styles.libraryExpandedContent} data-testid="video-library-content">
                  {videos.length > 0 && (
                    <>
                      <div className={styles.searchRow}>
                        <input
                          type="search"
                          placeholder="Search your library…"
                          value={videoQuery}
                          onChange={(e) => setVideoQuery(e.target.value)}
                          className={styles.searchInput}
                          aria-label="Search video library"
                          data-testid="library-search-input"
                        />
                      </div>
                      <div className={styles.filterRow} role="tablist" aria-label="Filter by status">
                        {FILTERS.map((f) => (
                          <button
                            key={f.key}
                            type="button"
                            role="tab"
                            aria-selected={filter === f.key}
                            className={`${styles.filterChip} ${
                              filter === f.key ? styles.filterChipActive : ''
                            }`}
                            onClick={() => setFilter(f.key)}
                          >
                            {f.label}
                          </button>
                        ))}
                      </div>
                    </>
                  )}

                  <div className={styles.listWrap}>
                    {libraryStatus === 'loading' && (
                      <div className={styles.skeletonList}>
                        <Skeleton height={36} borderRadius={6} style={{ marginBottom: 6 }} />
                        <Skeleton height={36} borderRadius={6} style={{ marginBottom: 6 }} />
                      </div>
                    )}

                    {libraryStatus === 'error' && (
                      <div className={styles.stateBlock}>
                        <p className={styles.stateError}>{libraryError}</p>
                        <button type="button" className={styles.retryButton} onClick={fetchVideos}>
                          Try again
                        </button>
                      </div>
                    )}

                    {libraryStatus === 'ready' && videos.length === 0 && (
                      <div className={styles.stateBlock}>
                        <p className={styles.emptyTitle}>No videos yet</p>
                        <p className={styles.emptyBody}>Add a YouTube video to start building your library.</p>
                      </div>
                    )}

                    {libraryStatus === 'ready' &&
                      videos.length > 0 &&
                      filteredVideos.length === 0 && (
                        <div className={styles.stateBlock}>
                          <p className={styles.emptyBody}>No videos match search.</p>
                        </div>
                      )}

                    {filteredVideos.length > 0 && (
                      <ul className={styles.list}>
                        {filteredVideos.map((video) => (
                          <VideoLibraryItem
                            key={video.video_id}
                            video={video}
                            isSelected={video.video_id === selectedVideoId}
                            isCollapsed={false}
                            conversationCount={convCountMap[video.video_id] || 0}
                            onSelectVideo={handleSelectVideo}
                          />
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* ---- Pinned Bottom Footer: User Profile Menu ---- */}
        <div className={styles.accountFooter}>
          <UserProfileDropdown
            isCollapsed={isSidebarCollapsed}
            onTriggerLogout={() => setIsLogoutModalOpen(true)}
          />
        </div>
      </aside>

      <Modal
        isOpen={isLogoutModalOpen}
        onClose={() => setIsLogoutModalOpen(false)}
        title="Log out?"
        confirmLabel="Log out"
        cancelLabel="Cancel"
        isDestructive
        onConfirm={handleConfirmLogout}
      >
        <p>Are you sure you want to log out?</p>
      </Modal>
    </>
  );
}
