import React, { useEffect, useRef, useState } from 'react';
import { Film, MessageSquare } from 'lucide-react';
import { useVideoLibrary } from '../../context/VideoLibraryContext';
import { useUI } from '../../context/UIContext';
import { VIDEO_STATUS } from '../../utils/constants';
import { sanitizeErrorMessage, formatProcessingStartedAt } from '../../utils/formatters';
import Modal from '../common/Modal';
import Tooltip from '../common/Tooltip';
import styles from './Sidebar.module.css';

function StatusDot({ status }) {
  const colors = {
    [VIDEO_STATUS.PROCESSED]: 'var(--success-500, #22c55e)',
    [VIDEO_STATUS.ALREADY_PROCESSED]: 'var(--success-500, #22c55e)',
    [VIDEO_STATUS.PROCESSING]: 'var(--warning-500, #f59e0b)',
    [VIDEO_STATUS.FAILED]: 'var(--danger-500, #ef4444)',
  };
  return (
    <span
      style={{
        width: 7,
        height: 7,
        borderRadius: '50%',
        background: colors[status] || 'var(--text-muted, #717171)',
        flexShrink: 0,
        display: 'inline-block',
      }}
      aria-hidden="true"
    />
  );
}

export default function VideoLibraryItem({
  video,
  isSelected,
  isCollapsed,
  conversationCount = 0,
  onSelectVideo,
}) {
  const { selectVideo, removeVideo, reprocessVideo } = useVideoLibrary();
  const { closeComposer } = useUI();
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const menuRef = useRef(null);
  const toggleRef = useRef(null);

  const openMenu = () => {
    const rect = toggleRef.current?.getBoundingClientRect();
    if (rect) {
      const MENU_W = 140;
      const MENU_H = 92;
      let top = rect.bottom + 4;
      if (top + MENU_H > window.innerHeight - 8) {
        top = rect.top - MENU_H - 4;
      }
      let left = rect.right - MENU_W;
      if (left < 8) left = 8;
      setMenuPos({ top, left });
    }
    setMenuOpen(true);
  };

  useEffect(() => {
    if (!menuOpen) return undefined;
    const handleClickOutside = (e) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(e.target) &&
        toggleRef.current &&
        !toggleRef.current.contains(e.target)
      ) {
        setMenuOpen(false);
      }
    };
    const closeOnMove = () => setMenuOpen(false);
    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('scroll', closeOnMove, true);
    window.addEventListener('resize', closeOnMove);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('scroll', closeOnMove, true);
      window.removeEventListener('resize', closeOnMove);
    };
  }, [menuOpen]);

  const handleSelect = () => {
    if (onSelectVideo) {
      onSelectVideo(video);
    } else {
      selectVideo(video.video_id);
      closeComposer();
    }
    setMenuOpen(false);
  };

  const handleOpenDeleteModal = (e) => {
    e.stopPropagation();
    setMenuOpen(false);
    setIsDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    try {
      await removeVideo(video.video_id);
    } finally {
      setIsDeleting(false);
      setIsDeleteModalOpen(false);
    }
  };

  const handleReprocess = async (e) => {
    e.stopPropagation();
    setMenuOpen(false);
    await reprocessVideo(
      video.video_id,
      video.url || `https://www.youtube.com/watch?v=${video.video_id}`
    );
  };

  const statusLabels = {
    [VIDEO_STATUS.PROCESSED]: 'Ready',
    [VIDEO_STATUS.ALREADY_PROCESSED]: 'Ready',
    [VIDEO_STATUS.PROCESSING]: 'Processing…',
    [VIDEO_STATUS.FAILED]: 'Failed',
  };

  if (isCollapsed) {
    const statusHint =
      video.status === VIDEO_STATUS.FAILED && video.error_message
        ? ` - ${sanitizeErrorMessage(video.error_message)}`
        : video.status === VIDEO_STATUS.PROCESSING && video.processing_started_at
          ? ` (${formatProcessingStartedAt(video.processing_started_at)})`
          : '';
    const tooltipText = `${video.title || 'Video'} (${statusLabels[video.status] || video.status}${statusHint} • ${conversationCount} ${conversationCount === 1 ? 'chat' : 'chats'})`;
    return (
      <li
        className={`${styles.itemCollapsed} ${isSelected ? styles.itemSelected : ''}`}
        onClick={handleSelect}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && handleSelect()}
        aria-pressed={isSelected}
        aria-label={`Video: ${video.title || 'Untitled'} (${statusLabels[video.status] || video.status})`}
      >
        <Tooltip content={tooltipText}>
          <div className={styles.itemThumbCollapsed}>
            {video.thumbnail_url ? (
              <img src={video.thumbnail_url} alt="" className={styles.itemThumbImg} />
            ) : (
              <Film size={14} />
            )}
            <span className={styles.collapsedStatusDot}>
              <StatusDot status={video.status} />
            </span>
          </div>
        </Tooltip>
      </li>
    );
  }

  return (
    <>
      <li
        className={`${styles.item} ${isSelected ? styles.itemSelected : ''} ${isDeleting ? styles.itemDeleting : ''}`}
        onClick={handleSelect}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && handleSelect()}
        aria-pressed={isSelected}
        data-testid="video-library-item"
      >
        {video.thumbnail_url ? (
          <img
            src={video.thumbnail_url}
            alt=""
            className={styles.itemThumb}
            data-testid="sidebar-video-thumbnail"
          />
        ) : (
          <div className={styles.itemThumbFallback} aria-hidden="true">
            <Film size={14} />
          </div>
        )}
        <div className={styles.itemBody}>
          <p className={styles.itemTitle} title={video.title}>
            {video.title || 'Untitled'}
          </p>
          <div className={styles.itemMeta}>
            <StatusDot status={video.status} />
            <span
              className={styles.itemStatus}
              title={
                video.status === VIDEO_STATUS.FAILED && video.error_message
                  ? sanitizeErrorMessage(video.error_message)
                  : video.status === VIDEO_STATUS.PROCESSING && video.processing_started_at
                    ? formatProcessingStartedAt(video.processing_started_at)
                    : undefined
              }
            >
              {statusLabels[video.status] || video.status}
            </span>
            <span className={styles.itemMetaDivider}>•</span>
            <span className={styles.itemChatCount}>
              <MessageSquare size={10} style={{ marginRight: 3, verticalAlign: 'middle' }} />
              {conversationCount} {conversationCount === 1 ? 'chat' : 'chats'}
            </span>
          </div>
        </div>

        <div className={styles.itemActions} onClick={(e) => e.stopPropagation()}>
          <button
            ref={toggleRef}
            type="button"
            className={styles.menuToggle}
            onClick={() => (menuOpen ? setMenuOpen(false) : openMenu())}
            aria-label="Video options"
            aria-expanded={menuOpen}
            data-testid="video-menu-toggle"
          >
            ⋮
          </button>
          {menuOpen && (
            <div
              ref={menuRef}
              className={`${styles.dropdownMenu} ${styles.dropdownMenuFixed}`}
              style={{ top: menuPos.top, left: menuPos.left }}
            >
              {video.status === VIDEO_STATUS.FAILED && (
                <button
                  type="button"
                  className={styles.dropdownItem}
                  onClick={handleReprocess}
                >
                  Reprocess
                </button>
              )}
              <button
                type="button"
                className={`${styles.dropdownItem} ${styles.dropdownItemDanger}`}
                onClick={handleOpenDeleteModal}
              >
                Delete
              </button>
            </div>
          )}
        </div>
      </li>

      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Delete video?"
        confirmLabel={isDeleting ? 'Deleting…' : 'Delete'}
        cancelLabel="Cancel"
        isDestructive
        onConfirm={handleConfirmDelete}
      >
        <p>
          Are you sure you want to delete &ldquo;{video.title || 'this video'}&rdquo;?
          This will remove it and its associated question history from your library.
        </p>
      </Modal>
    </>
  );
}
