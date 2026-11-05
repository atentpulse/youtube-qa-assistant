import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { useToast } from '../../../context/ToastContext';
import { useVideoLibrary } from '../../../context/VideoLibraryContext';
import { useConversations } from '../../../context/ConversationContext';
import { exportConversations, clearAllConversations } from '../../../api/conversations';
import { deleteAccount } from '../../../api/auth';
import Modal from '../../../components/common/Modal';
import { Download, Trash2, AlertTriangle, ShieldCheck, Film, MessageSquare } from 'lucide-react';
import common from './CategoryCommon.module.css';

export default function DataPrivacyCategory() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const { videos, removeVideo } = useVideoLibrary();
  const { conversations, loadConversations } = useConversations();

  const [isExporting, setIsExporting] = useState(false);

  // Modals state
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);
  const [isClearing, setIsClearing] = useState(false);

  const [videoToRemove, setVideoToRemove] = useState(null);
  const [isRemovingVideo, setIsRemovingVideo] = useState(false);

  const [isDeleteAccountModalOpen, setIsDeleteAccountModalOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);

  // Export conversations to JSON file
  const handleExport = async () => {
    setIsExporting(true);
    try {
      const data = await exportConversations();
      const jsonStr = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `ytgenius-conversations-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success('Conversation export downloaded successfully.');
    } catch (err) {
      toast.error(err?.message || 'Failed to export conversation history.');
    } finally {
      setIsExporting(false);
    }
  };

  // Clear all conversations
  const handleConfirmClear = async () => {
    setIsClearing(true);
    try {
      await clearAllConversations();
      await loadConversations();
      toast.success('All conversations cleared successfully.');
      setIsClearModalOpen(false);
    } catch (err) {
      toast.error(err?.message || 'Failed to clear conversations.');
    } finally {
      setIsClearing(false);
    }
  };

  // Remove video with reference-counted cleanup
  const handleConfirmRemoveVideo = async () => {
    if (!videoToRemove) return;
    setIsRemovingVideo(true);
    try {
      await removeVideo(videoToRemove.video_id);
      toast.success(`Removed "${videoToRemove.title || videoToRemove.video_id}" from library.`);
      setVideoToRemove(null);
    } catch (err) {
      toast.error(err?.message || 'Failed to remove video.');
    } finally {
      setIsRemovingVideo(false);
    }
  };

  // Delete entire user account
  const handleConfirmDeleteAccount = async () => {
    if (deleteConfirmText.trim() !== 'DELETE') {
      toast.error('Please type DELETE to confirm.');
      return;
    }
    setIsDeletingAccount(true);
    try {
      await deleteAccount();
      toast.success('Account and associated data deleted successfully.');
      logout();
      navigate('/', { replace: true });
    } catch (err) {
      toast.error(err?.message || 'Failed to delete account.');
      setIsDeletingAccount(false);
    }
  };

  return (
    <div className={common.container}>
      <div className={common.header}>
        <h2 className={common.title}>Data &amp; Privacy</h2>
        <p className={common.description}>
          Manage your personal data, export conversations, and review reference-counted library storage.
        </p>
      </div>

      {/* Storage Architecture Overview */}
      <div className={common.noticeBox}>
        <ShieldCheck size={18} className={common.noticeIcon} />
        <div>
          <strong style={{ color: '#ffffff', display: 'block', marginBottom: '2px' }}>
            Multi-User Canonical Video Architecture
          </strong>
          <span>
            Videos are canonical resources: removing a video from your library unlinks your personal view. If no other users reference the video, its Qdrant vectors and caches are safely destroyed. If other users reference it, their access is preserved.
          </span>
        </div>
      </div>

      {/* Usage Statistics */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Application Data Summary</h3>
          <p className={common.sectionSubtitle}>
            Current volume of stored research activity and video records for {user?.email}.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', paddingTop: '6px' }}>
          <div
            style={{
              background: 'var(--bg-canvas, #0f0f0f)',
              border: '1px solid var(--border-default, #303030)',
              borderRadius: '6px',
              padding: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
            }}
          >
            <Film size={22} style={{ color: 'var(--accent-red, #ff0033)' }} />
            <div>
              <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)' }}>
                {videos.length}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Saved Videos in Library
              </div>
            </div>
          </div>

          <div
            style={{
              background: 'var(--bg-canvas, #0f0f0f)',
              border: '1px solid var(--border-default, #303030)',
              borderRadius: '6px',
              padding: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
            }}
          >
            <MessageSquare size={22} style={{ color: 'var(--accent-blue, #3ea6ff)' }} />
            <div>
              <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)' }}>
                {conversations.length}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Active Research Chats
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Export & Clear Conversations */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Conversation History Management</h3>
          <p className={common.sectionSubtitle}>
            Export your research notes or purge old inquiry logs.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Export Research History</span>
            <span className={common.rowDescription}>
              Download all conversations, questions, and transcript citation metadata in JSON format.
            </span>
          </div>
          <button
            type="button"
            className={common.btnSecondary}
            onClick={handleExport}
            disabled={isExporting}
            data-testid="settings-export-conversations-btn"
          >
            <Download size={14} />
            {isExporting ? 'Preparing Export…' : 'Export JSON'}
          </button>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Clear All Conversations</span>
            <span className={common.rowDescription}>
              Permanently delete all research threads. Saved videos will remain in your library.
            </span>
          </div>
          <button
            type="button"
            className={common.btnDanger}
            onClick={() => setIsClearModalOpen(true)}
            disabled={conversations.length === 0}
            data-testid="settings-clear-conversations-btn"
          >
            <Trash2 size={14} /> Clear All Chats
          </button>
        </div>
      </div>

      {/* Library Video Management */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Video Library Management</h3>
          <p className={common.sectionSubtitle}>
            Unlink individual videos from your account. Reference-counted deletion is executed safely.
          </p>
        </div>

        {videos.length === 0 ? (
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '8px 0 0' }}>
            No videos in your library yet.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
            {videos.map((vid) => (
              <div
                key={vid.video_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                  padding: '10px 12px',
                  background: 'var(--bg-canvas, #0f0f0f)',
                  border: '1px solid var(--border-default, #303030)',
                  borderRadius: '6px',
                }}
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-primary)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                    {vid.title || vid.video_id}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                    ID: {vid.video_id} • Status: {vid.status}
                  </div>
                </div>
                <button
                  type="button"
                  className={common.btnDanger}
                  style={{ padding: '5px 10px', fontSize: '12px' }}
                  onClick={() => setVideoToRemove(vid)}
                  data-testid={`settings-remove-video-${vid.video_id}`}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Dangerous Account Deletion Zone */}
      <div className={common.section} style={{ borderColor: 'rgba(239, 68, 68, 0.4)' }}>
        <div>
          <h3 className={common.sectionTitle} style={{ color: '#ef4444' }}>
            Danger Zone
          </h3>
          <p className={common.sectionSubtitle}>
            Irreversible actions that permanently delete your personal account and associated data.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Delete Account</span>
            <span className={common.rowDescription}>
              Permanently delete your user profile, purge all conversation history, and unlink library videos.
            </span>
          </div>
          <button
            type="button"
            className={common.btnDangerSolid}
            onClick={() => {
              setDeleteConfirmText('');
              setIsDeleteAccountModalOpen(true);
            }}
            data-testid="settings-delete-account-btn"
          >
            Delete Account
          </button>
        </div>
      </div>

      {/* Clear Conversations Confirmation Modal */}
      <Modal
        isOpen={isClearModalOpen}
        onClose={() => setIsClearModalOpen(false)}
        title="Clear All Conversations?"
        confirmLabel="Clear Conversations"
        cancelLabel="Cancel"
        isDestructive
        isLoading={isClearing}
        onConfirm={handleConfirmClear}
      >
        <p>
          Are you sure you want to permanently delete all {conversations.length} conversation threads?
          Your video library will remain untouched, but all previous questions and responses will be erased.
        </p>
      </Modal>

      {/* Remove Video Confirmation Modal */}
      <Modal
        isOpen={!!videoToRemove}
        onClose={() => setVideoToRemove(null)}
        title="Remove Video from Library?"
        confirmLabel="Remove Video"
        cancelLabel="Cancel"
        isDestructive
        isLoading={isRemovingVideo}
        onConfirm={handleConfirmRemoveVideo}
      >
        <p>
          Are you sure you want to remove <strong>{videoToRemove?.title || videoToRemove?.video_id}</strong>?
        </p>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          If other users reference this video, their access is preserved and vector embeddings remain intact.
          If you are the only user with this video, its transcript index will be safely erased.
        </p>
      </Modal>

      {/* Delete Account Modal */}
      <Modal
        isOpen={isDeleteAccountModalOpen}
        onClose={() => setIsDeleteAccountModalOpen(false)}
        title="Delete Your Account Permanently"
        confirmLabel="Permanently Delete Account"
        cancelLabel="Cancel"
        isDestructive
        isLoading={isDeletingAccount}
        onConfirm={handleConfirmDeleteAccount}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className={common.warningBox}>
            <AlertTriangle size={18} className={common.warningIcon} />
            <span>
              This action cannot be undone. All conversations, profile records, and personal associations will be immediately deleted.
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '13px' }}>
            To confirm, please type <strong>DELETE</strong> below:
          </p>
          <input
            type="text"
            className={common.input}
            style={{ width: '100%', maxWidth: '100%' }}
            placeholder="Type DELETE to confirm"
            value={deleteConfirmText}
            onChange={(e) => setDeleteConfirmText(e.target.value)}
            data-testid="settings-delete-confirm-input"
          />
        </div>
      </Modal>
    </div>
  );
}
