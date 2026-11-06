import React from 'react';
import { MessageSquare, Plus, ArrowRight, Film } from 'lucide-react';
import styles from './ConversationSelectionView.module.css';

function formatRelativeTime(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diffSecs = Math.floor((now - date) / 1000);
  if (diffSecs < 60) return 'Just now';
  const diffMins = Math.floor(diffSecs / 60);
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function ConversationSelectionView({
  video,
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onNewConversation,
}) {
  return (
    <div className={styles.container} data-testid="conversation-selection-view">
      {/* Header Context Card */}
      <div className={styles.headerCard}>
        <div className={styles.headerInfo}>
          <div className={styles.badgeRow}>
            <span className={styles.videoBadge}>
              <Film size={11} aria-hidden="true" />
              Video Conversations
            </span>
          </div>
          <h2 className={styles.title} title={video?.title}>
            {video?.title || 'Selected Video'}
          </h2>
          <p className={styles.subtitle}>
            This video has {conversations.length} existing conversations. Choose one to continue or start a new conversation.
          </p>
        </div>

        <button
          type="button"
          className={styles.newConvBtn}
          onClick={onNewConversation}
          data-testid="selection-new-conversation-button"
        >
          <Plus size={15} />
          New Conversation
        </button>
      </div>

      {/* List of Conversations */}
      <div className={styles.listHeader}>
        <span className={styles.listTitle}>All Conversations</span>
        <span className={styles.listCount}>
          {conversations.length} {conversations.length === 1 ? 'thread' : 'threads'}
        </span>
      </div>

      <div className={styles.conversationGrid} role="list">
        {conversations.map((conv) => {
          const isActive = conv.id === activeConversationId;
          const relativeTime = formatRelativeTime(conv.updated_at || conv.created_at);

          return (
            <div
              key={conv.id}
              role="listitem"
              tabIndex={0}
              className={`${styles.convCard} ${isActive ? styles.convCardActive : ''}`}
              onClick={() => onSelectConversation(conv.id)}
              onKeyDown={(e) => e.key === 'Enter' && onSelectConversation(conv.id)}
              data-testid={`select-conv-${conv.id}`}
            >
              <div className={styles.convCardLeft}>
                <div className={styles.convIconWrap}>
                  <MessageSquare size={16} />
                </div>
                <div className={styles.convInfo}>
                  <p className={styles.convTitle} title={conv.title}>
                    {conv.title || 'Untitled Conversation'}
                  </p>
                  <div className={styles.convMetaRow}>
                    {relativeTime && <span>Last active {relativeTime}</span>}
                    {conv.message_count !== undefined && (
                      <>
                        <span>•</span>
                        <span>{conv.message_count} {conv.message_count === 1 ? 'message' : 'messages'}</span>
                      </>
                    )}
                    {isActive && <span className={styles.activeTag}>Current</span>}
                  </div>
                </div>
              </div>

              <div className={styles.arrowIcon}>
                <ArrowRight size={16} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
