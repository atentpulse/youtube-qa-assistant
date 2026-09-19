import React, { useEffect, useRef, useState } from "react";
import { MessageSquare } from "lucide-react";
import { useConversations } from "../../context/ConversationContext";
import Modal from "../common/Modal";
import styles from "./Sidebar.module.css";

export default function ConversationItem({ conversation, isActive, onSelect }) {
  const { renameConversation, deleteConversation } = useConversations();
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [editTitle, setEditTitle] = useState(
    conversation.title || "Conversation",
  );
  const inputRef = useRef(null);
  const menuRef = useRef(null);
  const toggleRef = useRef(null);

  // Position a fixed-position menu next to the ⋮ button so it is never
  // clipped by the scrollable conversation list, never adds a scrollbar,
  // and flips upward when near the bottom of the viewport.
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
    document.addEventListener("mousedown", handleClickOutside);
    window.addEventListener("scroll", closeOnMove, true);
    window.addEventListener("resize", closeOnMove);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("scroll", closeOnMove, true);
      window.removeEventListener("resize", closeOnMove);
    };
  }, [menuOpen]);

  const handleStartEdit = (e) => {
    e.stopPropagation();
    setMenuOpen(false);
    setIsEditing(true);
    setEditTitle(conversation.title || "");
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const handleCommitEdit = async () => {
    const trimmed = editTitle.trim();
    if (trimmed && trimmed !== conversation.title) {
      await renameConversation(conversation.id, trimmed);
    }
    setIsEditing(false);
  };

  const handleEditKeyDown = (e) => {
    if (e.key === "Enter") handleCommitEdit();
    if (e.key === "Escape") setIsEditing(false);
  };

  const handleOpenDeleteModal = (e) => {
    e.stopPropagation();
    setMenuOpen(false);
    setIsDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    try {
      setIsDeleting(true);
      await deleteConversation(conversation.id);
    } finally {
      setIsDeleting(false);
      setIsDeleteModalOpen(false);
    }
  };

  return (
    <>
      <li
        className={`${styles.conversationItem} ${isActive ? styles.conversationItemActive : ""}`}
        onClick={!isEditing ? onSelect : undefined}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => !isEditing && e.key === "Enter" && onSelect()}
        aria-pressed={isActive}
      >
        <span className={styles.conversationIcon} aria-hidden="true">
          <MessageSquare size={14} />
        </span>

        {isEditing ? (
          <input
            ref={inputRef}
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onBlur={handleCommitEdit}
            onKeyDown={handleEditKeyDown}
            className={styles.renameInput}
            aria-label="Rename conversation"
            onClick={(e) => e.stopPropagation()}
            autoFocus
          />
        ) : (
          <span className={styles.conversationTitle} title={conversation.title}>
            {conversation.title || "Conversation"}
          </span>
        )}

        <div className={styles.itemActions} onClick={(e) => e.stopPropagation()}>
          <button
            ref={toggleRef}
            type="button"
            className={styles.menuToggle}
            onClick={() => (menuOpen ? setMenuOpen(false) : openMenu())}
            aria-label="Conversation options"
            aria-expanded={menuOpen}
            data-testid="conversation-menu-toggle"
          >
            ⋮
          </button>
          {menuOpen && (
            <div
              ref={menuRef}
              className={`${styles.dropdownMenu} ${styles.dropdownMenuFixed}`}
              style={{ top: menuPos.top, left: menuPos.left }}
              data-testid="conversation-menu"
            >
              <button
                type="button"
                className={styles.dropdownItem}
                onClick={handleStartEdit}
                data-testid="conversation-rename-button"
              >
                Rename
              </button>
              <button
                type="button"
                className={`${styles.dropdownItem} ${styles.dropdownItemDanger}`}
                onClick={handleOpenDeleteModal}
                data-testid="conversation-delete-button"
              >
                Delete
              </button>
            </div>
          )}
        </div>
      </li>

      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => !isDeleting && setIsDeleteModalOpen(false)}
        title="Delete conversation?"
        confirmLabel="Delete"
        cancelLabel="Cancel"
        isDestructive
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
      >
        <p>
          Are you sure you want to delete &ldquo;{conversation.title || "this conversation"}&rdquo;?
          This action cannot be undone.
        </p>
      </Modal>
    </>
  );
}
