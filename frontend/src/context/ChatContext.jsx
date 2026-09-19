import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { askQuestion } from '../api/questions';
import { ApiError } from '../api/client';
import { useConversations } from './ConversationContext';

const ChatContext = createContext(null);

let messageIdCounter = 0;

/**
 * Heuristic for "no relevant information found" responses so we can show a
 * dedicated, friendly empty state instead of treating it as a normal answer
 * or an error. Backends sometimes signal this via empty sources, sometimes
 * via a null/empty answer — we check both without assuming a specific shape.
 */
function isNoInformationFound(response) {
  const answer = (response?.answer || '').trim().toLowerCase();
  if (!answer) return true;
  const negativePatterns = [
    "don't have enough information",
    'do not have enough information',
    "couldn't find",
    'could not find',
    'no relevant information',
    'not mentioned in the video',
    "doesn't appear to be covered",
  ];
  return negativePatterns.some((p) => answer.includes(p));
}

/**
 * Converts backend Message records ({ id, role, content, created_at }) into
 * the display shape used by QAThread/MessageBubble.
 *
 * Backend messages are stored as separate user/assistant rows. We pair each
 * user message with the following assistant message into a single display
 * entry. Sources are NOT persisted by the backend, so reloaded conversations
 * show answers without source chips (a backend limitation).
 */
export function convertBackendMessages(messages) {
  const result = [];
  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    if (msg.role !== 'user') continue;
    const next = messages[i + 1];
    if (next && next.role === 'assistant') {
      result.push({
        id: msg.id,
        question: msg.content,
        status: 'done',
        answer: next.content,
        sources: Array.isArray(next?.sources) ? next.sources : [],
        notFound: false,
        errorMessage: null,
      });
      i++; // skip the paired assistant message
    } else {
      result.push({
        id: msg.id,
        question: msg.content,
        status: 'done',
        answer: null,
        sources: [],
        notFound: false,
        errorMessage: null,
      });
    }
  }
  return result;
}

export function ChatProvider({ children }) {
  const {
    activeConversationId,
    messages: persistedMessages,
    messagesStatus,
    registerConversation,
  } = useConversations();

  // { [key]: Array<Message> }
  // Keys:
  // - `conv_${conversationId}` for conversations
  // - `draft_${videoId}` for drafts / new chat sessions
  const [threads, setThreads] = useState({});

  // Sync persisted messages into the thread when the active conversation's
  // messages finish loading.
  useEffect(() => {
    if (!activeConversationId || messagesStatus !== 'ready') return;
    const key = `conv_${activeConversationId}`;
    const converted = convertBackendMessages(persistedMessages);
    setThreads((prev) => ({ ...prev, [key]: converted }));
  }, [activeConversationId, persistedMessages, messagesStatus]);

  const askAboutVideo = useCallback(
    async (videoId, question) => {
      const messageId = ++messageIdCounter;
      const currentConvId = activeConversationId;
      const key = currentConvId ? `conv_${currentConvId}` : `draft_${videoId}`;

      const pendingMessage = {
        id: messageId,
        question,
        status: 'loading',
        answer: null,
        sources: [],
        notFound: false,
        errorMessage: null,
      };

      setThreads((prev) => ({
        ...prev,
        [key]: [...(prev[key] || []), pendingMessage],
      }));

      try {
        const response = await askQuestion({
          video_id: videoId,
          question,
          conversation_id: currentConvId,
        });

        const notFound = isNoInformationFound(response);
        const resolvedMessage = {
          id: messageId,
          question,
          status: 'done',
          answer: response?.answer || '',
          sources: Array.isArray(response?.sources) ? response.sources : [],
          notFound,
          errorMessage: null,
        };

        if (response?.conversation_id && !currentConvId) {
          const newConvId = response.conversation_id;
          setThreads((prev) => {
            const draftList = prev[`draft_${videoId}`] || [];
            const updated = draftList.map((m) => (m.id === messageId ? resolvedMessage : m));
            const next = { ...prev };
            delete next[`draft_${videoId}`];
            next[`conv_${newConvId}`] = updated.length > 0 ? updated : [resolvedMessage];
            return next;
          });
          const initialTitle = question.length > 40 ? `${question.slice(0, 40)}…` : question;
          registerConversation(newConvId, videoId, initialTitle);
        } else {
          const targetKey = currentConvId ? `conv_${currentConvId}` : key;
          setThreads((prev) => ({
            ...prev,
            [targetKey]: (prev[targetKey] || []).map((m) =>
              m.id === messageId ? resolvedMessage : m
            ),
          }));
        }
      } catch (err) {
        const message = err instanceof ApiError ? err.message : 'Something went wrong answering that question.';
        setThreads((prev) => ({
          ...prev,
          [key]: (prev[key] || []).map((m) =>
            m.id === messageId ? { ...m, status: 'error', errorMessage: message } : m
          ),
        }));
      }
    },
    [activeConversationId, registerConversation]
  );

  const retryMessage = useCallback(
    async (videoId, messageId, question) => {
      const currentConvId = activeConversationId;
      const key = currentConvId ? `conv_${currentConvId}` : `draft_${videoId}`;

      setThreads((prev) => ({
        ...prev,
        [key]: (prev[key] || []).map((m) =>
          m.id === messageId ? { ...m, status: 'loading', errorMessage: null } : m
        ),
      }));

      try {
        const response = await askQuestion({
          video_id: videoId,
          question,
          conversation_id: currentConvId,
        });

        const notFound = isNoInformationFound(response);
        const resolvedMessage = {
          id: messageId,
          question,
          status: 'done',
          answer: response?.answer || '',
          sources: Array.isArray(response?.sources) ? response.sources : [],
          notFound,
          errorMessage: null,
        };

        if (response?.conversation_id && !currentConvId) {
          const newConvId = response.conversation_id;
          setThreads((prev) => {
            const draftList = prev[`draft_${videoId}`] || [];
            const updated = draftList.map((m) => (m.id === messageId ? resolvedMessage : m));
            const next = { ...prev };
            delete next[`draft_${videoId}`];
            next[`conv_${newConvId}`] = updated.length > 0 ? updated : [resolvedMessage];
            return next;
          });
          const initialTitle = question.length > 40 ? `${question.slice(0, 40)}…` : question;
          registerConversation(newConvId, videoId, initialTitle);
        } else {
          const targetKey = currentConvId ? `conv_${currentConvId}` : key;
          setThreads((prev) => ({
            ...prev,
            [targetKey]: (prev[targetKey] || []).map((m) =>
              m.id === messageId ? resolvedMessage : m
            ),
          }));
        }
      } catch (err) {
        const message = err instanceof ApiError ? err.message : 'Something went wrong answering that question.';
        setThreads((prev) => ({
          ...prev,
          [key]: (prev[key] || []).map((m) =>
            m.id === messageId ? { ...m, status: 'error', errorMessage: message } : m
          ),
        }));
      }
    },
    [activeConversationId, registerConversation]
  );

  const getThread = useCallback((key) => threads[key] || [], [threads]);

  const clearThread = useCallback((key) => {
    setThreads((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }, []);

  const value = { askAboutVideo, retryMessage, getThread, clearThread };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChat must be used within a ChatProvider');
  return ctx;
}