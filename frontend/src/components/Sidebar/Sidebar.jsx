import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import VideoLibraryItem from './VideoLibraryItem';
import ConversationItem from './ConversationItem';
import Spinner from '../common/Spinner';
import Modal from '../common/Modal';
import { Moon, Sun } from 'lucide-react';
import { useVideoLibrary } from '../../context/VideoLibraryContext';
import { useConversations } from '../../context/ConversationContext';
import { useChat } from '../../context/ChatContext';
import { useUI } from '../../context/UIContext';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
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

function LogoutIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none">
      <path
        d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
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
  const { openComposer, closeComposer, isMobileSidebarOpen, closeMobileSidebar } = useUI();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);

  const filteredVideos = useMemo(() => {
    return videos.filter((v) => {
      const matchesQuery = !query.trim() || (v.title || '').toLowerCase().includes(query.trim().toLowerCase());
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

      <aside className={`${styles.sidebar} ${isMobileSidebarOpen ? styles.sidebarOpen : ''}`}>
        <div className={styles.brand}>
          <div className={styles.brandMark} aria-hidden="true">
            <img src="/logo.svg" alt="" className={styles.brandMarkImg} />
          </div>
          <div>
            <h1 className={styles.brandName}>VidMind</h1>
            <p className={styles.brandSubtitle}>Video Q&A</p>
          </div>
          <button
            type="button"
            className={styles.mobileCloseButton}
            onClick={closeMobileSidebar}
            aria-label="Close sidebar"
          >
            ×
          </button>
        </div>

        {/* ---- + New Chat Primary Action ---- */}
        <div className={styles.newVideoRow}>
          <button
            type="button"
            className={styles.newVideoButton}
            onClick={handleNewChat}
            aria-label="Start a new chat"
            data-testid="new-chat-button"
          >
            <PlusIcon />
            + New Chat
          </button>
        </div>

        {/* ---- Conversations section ---- */}
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>Conversations</span>
          <span className={styles.itemCount}>
            {conversations.length > 0 ? `(${conversations.length})` : ''}
          </span>
        </div>

        <div className={styles.conversationListWrap}>
          {conversationsStatus === 'loading' && (
            <div className={styles.stateBlock}>
              <Spinner size={16} />
              <p>Loading conversations…</p>
            </div>
          )}

          {conversationsStatus === 'error' && (
            <div className={styles.stateBlock}>
              <p className={styles.stateError}>{conversationsError}</p>
              <button type="button" className={styles.retryButton} onClick={loadConversations}>
                Try again
              </button>
            </div>
          )}

          {conversationsStatus === 'ready' && conversations.length === 0 && (
            <div className={styles.stateBlock}>
              <p className={styles.emptyBody}>No conversations yet. Ask a question to get started.</p>
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
                />
              ))}
            </ul>
          )}
        </div>

        {/* ---- Visual separation divider ---- */}
        <div className={styles.sectionDivider} />

        {/* ---- Video library section ---- */}
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>Video Library</span>
          <button
            type="button"
            className={styles.newChatButton}
            onClick={handleNewVideo}
            aria-label="Add a YouTube video"
            title="Add video"
            data-testid="add-video-button"
          >
            <PlusIcon />
            Add video
          </button>
        </div>

        {videos.length > 0 && (
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
                  className={`${styles.filterChip} ${filter === f.key ? styles.filterChipActive : ''}`}
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
            <div className={styles.stateBlock}>
              <Spinner size={18} />
              <p>Loading your library…</p>
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
              <p className={styles.emptyBody}>Add a YouTube video to start asking questions.</p>
            </div>
          )}

          {libraryStatus === 'ready' && videos.length > 0 && filteredVideos.length === 0 && (
            <div className={styles.stateBlock}>
              <p className={styles.emptyBody}>No videos match your search.</p>
            </div>
          )}

          {filteredVideos.length > 0 && (
            <ul className={styles.list}>
              {filteredVideos.map((video) => (
                <VideoLibraryItem key={video.video_id} video={video} isSelected={video.video_id === selectedVideoId} />
              ))}
            </ul>
          )}
        </div>

        <div className={styles.accountFooter}>
          <div className={styles.accountInfo}>
            <div className={styles.accountAvatar} aria-hidden="true">
              {(user?.username || user?.email || '?').charAt(0).toUpperCase()}
            </div>
            <div className={styles.accountText}>
              <p className={styles.accountName} title={user?.username}>
                {user?.username || 'Account'}
              </p>
              <p className={styles.accountEmail} title={user?.email}>
                {user?.email}
              </p>
            </div>
          </div>
          <button
            type="button"
            className={styles.themeToggle}
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
            data-testid="theme-toggle"
          >
            {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
          </button>
          <button
            type="button"
            className={styles.logoutButton}
            onClick={() => setIsLogoutModalOpen(true)}
            aria-label="Log out"
            title="Sign out"
            data-testid="logout-button"
          >
            <LogoutIcon />
          </button>
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