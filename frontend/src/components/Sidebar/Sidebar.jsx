import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import VideoLibraryItem from './VideoLibraryItem';
import ConversationItem from './ConversationItem';
import Modal from '../common/Modal';
import Tooltip from '../common/Tooltip';
import Skeleton from '../common/Skeleton';
import UserProfileDropdown from './UserProfileDropdown';
import { MessageSquare, Film } from 'lucide-react';
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
  const { videos, libraryStatus, libraryError, fetchVideos, selectedVideoId } = useVideoLibrary();
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
    isMobileSidebarOpen,
    closeMobileSidebar,
    isSidebarCollapsed,
    toggleSidebarCollapse,
  } = useUI();
  const { logout } = useAuth();
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);

  const filteredVideos = useMemo(() => {
    return videos.filter((v) => {
      const matchesQuery =
        !query.trim() || (v.title || '').toLowerCase().includes(query.trim().toLowerCase());
      const matchesFilter =
        filter === 'all' ||
        v.status === filter ||
        (filter === VIDEO_STATUS.PROCESSED && v.status === VIDEO_STATUS.ALREADY_PROCESSED);
      return matchesQuery && matchesFilter;
    });
  }, [videos, query, filter]);

  const handleNewVideo = () => {
    openComposer();
    closeMobileSidebar();
  };

  const handleNewChat = () => {
    clearActiveConversation();
    if (selectedVideoId) {
      clearThread(`draft_${selectedVideoId}`);
    }
    closeComposer();
    closeMobileSidebar();
  };

  const handleSelectConversation = (conversationId) => {
    selectConversation(conversationId);
    closeComposer();
    closeMobileSidebar();
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
                  <span className={styles.brandSubtitle}>AI Video Research</span>
                </div>
              </div>

              <button
                type="button"
                className={styles.collapseButton}
                onClick={toggleSidebarCollapse}
                aria-label="Collapse sidebar"
                title="Collapse sidebar"
              >
                ◀
              </button>
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

        {/* ---- Pinned Top Action: New Chat ---- */}
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

        {/* ---- Independently Scrollable Lists Container ---- */}
        <div className={styles.scrollableBody}>
          {isSidebarCollapsed && (
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
              <Tooltip content="Add YouTube Video">
                <button
                  type="button"
                  className={styles.collapsedNavBtn}
                  onClick={handleNewVideo}
                  aria-label="Add YouTube Video"
                >
                  <PlusIcon />
                </button>
              </Tooltip>
              <div className={styles.collapsedRailDivider} />
            </div>
          )}

          {/* ---- Conversations Section ---- */}
          {!isSidebarCollapsed && (
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>Conversations</span>
              <span className={styles.itemCount}>
                {conversations.length > 0 ? `(${conversations.length})` : ''}
              </span>
            </div>
          )}

          <div className={styles.conversationListWrap}>
            {conversationsStatus === 'loading' && (
              <div className={styles.skeletonList}>
                <Skeleton height={30} borderRadius={6} style={{ marginBottom: 6 }} />
                <Skeleton height={30} borderRadius={6} style={{ marginBottom: 6 }} />
              </div>
            )}

            {conversationsStatus === 'error' && (
              <div className={styles.stateBlock}>
                {!isSidebarCollapsed && (
                  <>
                    <p className={styles.stateError}>{conversationsError}</p>
                    <button
                      type="button"
                      className={styles.retryButton}
                      onClick={loadConversations}
                    >
                      Try again
                    </button>
                  </>
                )}
              </div>
            )}

            {conversationsStatus === 'ready' && conversations.length === 0 && !isSidebarCollapsed && (
              <div className={styles.stateBlock}>
                <p className={styles.emptyBody}>
                  No conversations yet. Ask a question to get started.
                </p>
              </div>
            )}

            {conversations.length > 0 && (
              <ul className={styles.conversationList}>
                {conversations.map((conversation) => (
                  <ConversationItem
                    key={conversation.id}
                    conversation={conversation}
                    isActive={conversation.id === activeConversationId}
                    onSelect={() => handleSelectConversation(conversation.id)}
                    isCollapsed={isSidebarCollapsed}
                  />
                ))}
              </ul>
            )}
          </div>

          <div className={styles.sectionDivider} />

          {/* ---- Video Library Section ---- */}
          {!isSidebarCollapsed && (
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>Video Library</span>
              <button
                type="button"
                className={styles.addVideoButton}
                onClick={handleNewVideo}
                aria-label="Add a YouTube video"
                title="Add video"
                data-testid="add-video-button"
              >
                <PlusIcon />
                Add
              </button>
            </div>
          )}

          {videos.length > 0 && !isSidebarCollapsed && (
            <>
              <div className={styles.searchRow}>
                <input
                  type="search"
                  placeholder="Search your library…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
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
                {!isSidebarCollapsed && (
                  <>
                    <p className={styles.stateError}>{libraryError}</p>
                    <button type="button" className={styles.retryButton} onClick={fetchVideos}>
                      Try again
                    </button>
                  </>
                )}
              </div>
            )}

            {libraryStatus === 'ready' && videos.length === 0 && !isSidebarCollapsed && (
              <div className={styles.stateBlock}>
                <p className={styles.emptyTitle}>No videos yet</p>
                <p className={styles.emptyBody}>Add a YouTube video to start asking questions.</p>
              </div>
            )}

            {libraryStatus === 'ready' &&
              videos.length > 0 &&
              filteredVideos.length === 0 &&
              !isSidebarCollapsed && (
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
                    isCollapsed={isSidebarCollapsed}
                  />
                ))}
              </ul>
            )}
          </div>
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
