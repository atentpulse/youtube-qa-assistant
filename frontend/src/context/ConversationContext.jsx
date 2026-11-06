import React, { createContext, useCallback, useContext, useEffect, useReducer, useRef } from 'react';
import {
  createConversation as apiCreateConversation,
  deleteConversation as apiDeleteConversation,
  getConversationMessages,
  getConversations,
  renameConversation as apiRenameConversation,
} from '../api/conversations';
import { ApiError } from '../api/client';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';
import { VideoLibraryContext } from './VideoLibraryContext';

const ConversationContext = createContext(null);

const initialState = {
  conversations: [],
  conversationsStatus: 'idle', // idle | loading | ready | error
  conversationsError: null,
  activeConversationId: null,
  activeConversation: null,
  messages: [],
  messagesStatus: 'idle', // idle | loading | ready | error
  messagesError: null,
  nextCursor: null,
  hasMore: false,
};

function reducer(state, action) {
  switch (action.type) {
    case 'FETCH_CONVERSATIONS_START':
      return { ...state, conversationsStatus: 'loading', conversationsError: null };
    case 'FETCH_CONVERSATIONS_SUCCESS': {
      const activeConv = state.activeConversationId
        ? action.conversations.find((c) => c.id === state.activeConversationId) || state.activeConversation
        : null;
      return {
        ...state,
        conversationsStatus: 'ready',
        conversations: action.conversations,
        activeConversation: activeConv,
      };
    }
    case 'FETCH_CONVERSATIONS_ERROR':
      return { ...state, conversationsStatus: 'error', conversationsError: action.error };
    case 'SELECT_CONVERSATION':
      return {
        ...state,
        activeConversationId: action.conversationId,
        activeConversation: state.conversations.find((c) => c.id === action.conversationId) || null,
        messages: [],
        messagesStatus: 'idle',
        messagesError: null,
        nextCursor: null,
        hasMore: false,
      };
    case 'FETCH_MESSAGES_START':
      return { ...state, messagesStatus: 'loading', messagesError: null };
    case 'FETCH_MESSAGES_SUCCESS':
      return {
        ...state,
        messagesStatus: 'ready',
        messages: action.messages,
        nextCursor: action.nextCursor,
        hasMore: action.nextCursor !== null,
      };
    case 'FETCH_OLDER_MESSAGES_START':
      return { ...state, messagesStatus: 'loading', messagesError: null };
    case 'FETCH_OLDER_MESSAGES_SUCCESS': {
      // Merge older messages with existing, avoiding duplicates by id.
      const existingIds = new Set(state.messages.map((m) => m.id));
      const older = action.messages.filter((m) => !existingIds.has(m.id));
      return {
        ...state,
        messagesStatus: 'ready',
        messages: [...older, ...state.messages],
        nextCursor: action.nextCursor,
        hasMore: action.nextCursor !== null,
      };
    }
    case 'FETCH_MESSAGES_ERROR':
      return { ...state, messagesStatus: 'error', messagesError: action.error };
    case 'CONVERSATION_CREATED': {
      const conversation = action.conversation;
      const exists = state.conversations.some((c) => c.id === conversation.id);
      const conversations = exists
        ? state.conversations.map((c) =>
            c.id === conversation.id
              ? {
                  ...c,
                  ...conversation,
                  title: conversation.title || c.title,
                  video_id: conversation.video_id || c.video_id,
                }
              : c
          )
        : [conversation, ...state.conversations];
      return {
        ...state,
        conversationsStatus: 'ready',
        conversations,
        activeConversationId: conversation.id,
        activeConversation: exists
          ? {
              ...state.activeConversation,
              ...conversation,
              title: conversation.title || state.activeConversation?.title,
              video_id: conversation.video_id || state.activeConversation?.video_id,
            }
          : conversation,
      };
    }
    case 'CONVERSATION_UPDATED': {
      const conversation = action.conversation;
      return {
        ...state,
        conversations: state.conversations.map((c) => (c.id === conversation.id ? conversation : c)),
        activeConversation:
          state.activeConversationId === conversation.id ? conversation : state.activeConversation,
      };
    }
    case 'CONVERSATION_DELETED': {
      const conversations = state.conversations.filter((c) => c.id !== action.conversationId);
      const isActive = state.activeConversationId === action.conversationId;
      return {
        ...state,
        conversations,
        ...(isActive
          ? {
              activeConversationId: null,
              activeConversation: null,
              messages: [],
              messagesStatus: 'idle',
              messagesError: null,
              nextCursor: null,
              hasMore: false,
            }
          : {}),
      };
    }
    case 'CLEAR_ACTIVE':
      return {
        ...state,
        activeConversationId: null,
        activeConversation: null,
        messages: [],
        messagesStatus: 'idle',
        messagesError: null,
        nextCursor: null,
        hasMore: false,
      };
    case 'RESET':
      return { ...initialState };
    default:
      return state;
  }
}

export function ConversationProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { isAuthenticated, loading: authLoading } = useAuth();
  const videoLib = useContext(VideoLibraryContext);
  const selectedVideoId = videoLib?.selectedVideoId;
  const selectVideo = videoLib?.selectVideo;
  const toast = useToast();
  const messageRequestSeq = useRef(0);
  const previousVideoIdRef = useRef(selectedVideoId);

  const loadConversations = useCallback(async () => {
    dispatch({ type: 'FETCH_CONVERSATIONS_START' });
    try {
      const conversations = await getConversations();
      dispatch({ type: 'FETCH_CONVERSATIONS_SUCCESS', conversations });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Could not load conversations.';
      dispatch({ type: 'FETCH_CONVERSATIONS_ERROR', error: message });
    }
  }, []);

  const loadConversationMessages = useCallback(async (conversationId) => {
    const seq = ++messageRequestSeq.current;
    dispatch({ type: 'FETCH_MESSAGES_START' });
    try {
      const response = await getConversationMessages(conversationId);
      if (seq !== messageRequestSeq.current) return; // stale response
      dispatch({
        type: 'FETCH_MESSAGES_SUCCESS',
        messages: response.messages || [],
        nextCursor: response.next_cursor ?? null,
      });
    } catch (err) {
      if (seq !== messageRequestSeq.current) return;
      const message = err instanceof ApiError ? err.message : 'Could not load messages.';
      dispatch({ type: 'FETCH_MESSAGES_ERROR', error: message });
    }
  }, []);

  // One-tap conversation access (Bug 5 & Bug 6):
  // Selecting a conversation immediately sets activeConversation AND restores its bound video
  const selectConversation = useCallback(
    (conversationId) => {
      const conv = state.conversations.find((c) => c.id === conversationId);
      dispatch({ type: 'SELECT_CONVERSATION', conversationId });
      loadConversationMessages(conversationId);

      if (conv?.video_id && selectVideo && conv.video_id !== selectedVideoId) {
        selectVideo(conv.video_id);
      }
    },
    [state.conversations, loadConversationMessages, selectVideo, selectedVideoId]
  );

  // Maintain video and conversation context alignment (Bug 6 & Redesign):
  // When the selected video changes, ensure any mismatched active conversation is cleared.
  useEffect(() => {
    if (selectedVideoId !== previousVideoIdRef.current) {
      previousVideoIdRef.current = selectedVideoId;

      if (!selectedVideoId) {
        dispatch({ type: 'CLEAR_ACTIVE' });
        return;
      }

      // If active conversation already matches newly selected video, keep it
      if (state.activeConversation?.video_id === selectedVideoId) {
        return;
      }

      // Otherwise, clear active conversation to prevent cross-video state mismatch
      dispatch({ type: 'CLEAR_ACTIVE' });
    }
  }, [
    selectedVideoId,
    state.activeConversation?.video_id,
  ]);

  const loadOlderMessages = useCallback(async () => {
    if (!state.activeConversationId || !state.nextCursor) return;
    dispatch({ type: 'FETCH_OLDER_MESSAGES_START' });
    try {
      const response = await getConversationMessages(state.activeConversationId, {
        beforeId: state.nextCursor,
      });
      dispatch({
        type: 'FETCH_OLDER_MESSAGES_SUCCESS',
        messages: response.messages || [],
        nextCursor: response.next_cursor ?? null,
      });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Could not load older messages.';
      dispatch({ type: 'FETCH_MESSAGES_ERROR', error: message });
    }
  }, [state.activeConversationId, state.nextCursor]);

  const createConversation = useCallback(
    async (title = null, videoId = null) => {
      try {
        const targetVideoId = videoId || selectedVideoId;
        const conversation = await apiCreateConversation({
          title: title || 'New Chat',
          video_id: targetVideoId,
        });
        dispatch({
          type: 'CONVERSATION_CREATED',
          conversation,
        });
        return conversation;
      } catch (err) {
        const message = err instanceof ApiError ? err.message : 'Could not create conversation.';
        toast.error(message);
        throw err;
      }
    },
    [selectedVideoId, toast]
  );

  const renameConversation = useCallback(
    async (conversationId, title) => {
      try {
        const conversation = await apiRenameConversation(conversationId, title);
        dispatch({ type: 'CONVERSATION_UPDATED', conversation });
        return conversation;
      } catch (err) {
        const message = err instanceof ApiError ? err.message : 'Could not rename conversation.';
        toast.error(message);
        throw err;
      }
    },
    [toast]
  );

  const deleteConversation = useCallback(
    async (conversationId) => {
      try {
        await apiDeleteConversation(conversationId);
        dispatch({ type: 'CONVERSATION_DELETED', conversationId });
        return true;
      } catch (err) {
        const message = err instanceof ApiError ? err.message : 'Could not delete conversation.';
        toast.error(message);
        throw err;
      }
    },
    [toast]
  );

  const clearActiveConversation = useCallback(() => {
    dispatch({ type: 'CLEAR_ACTIVE' });
  }, []);

  const setActiveConversationId = useCallback((conversationId) => {
    dispatch({ type: 'SELECT_CONVERSATION', conversationId });
  }, []);

  const registerConversation = useCallback(
    (conversationId, videoId, initialTitle = null) => {
      const now = new Date().toISOString();
      dispatch({
        type: 'CONVERSATION_CREATED',
        conversation: {
          id: conversationId,
          title: initialTitle,
          video_id: videoId,
          created_at: now,
          updated_at: now,
        },
      });
      loadConversations();
    },
    [loadConversations]
  );

  // Load conversations when authenticated; reset on logout.
  useEffect(() => {
    if (authLoading) return;
    if (isAuthenticated) {
      loadConversations();
    } else {
      messageRequestSeq.current += 1; // invalidate in-flight message loads
      dispatch({ type: 'RESET' });
    }
  }, [isAuthenticated, authLoading, loadConversations]);

  const value = {
    ...state,
    loadConversations,
    selectConversation,
    loadConversationMessages,
    loadOlderMessages,
    createConversation,
    renameConversation,
    deleteConversation,
    clearActiveConversation,
    setActiveConversationId,
    registerConversation,
  };

  return <ConversationContext.Provider value={value}>{children}</ConversationContext.Provider>;
}

export function useConversations() {
  const ctx = useContext(ConversationContext);
  if (!ctx) throw new Error('useConversations must be used within a ConversationProvider');
  return ctx;
}
