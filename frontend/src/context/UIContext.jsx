import React, { createContext, useCallback, useContext, useState } from 'react';

const UIContext = createContext(null);

export function UIProvider({ children }) {
  const [isComposerOpen, setIsComposerOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const openComposer = useCallback(() => setIsComposerOpen(true), []);
  const closeComposer = useCallback(() => setIsComposerOpen(false), []);
  const toggleComposer = useCallback(() => setIsComposerOpen((v) => !v), []);

  const toggleSidebar = useCallback(() => setIsSidebarOpen((v) => !v), []);
  const closeSidebar = useCallback(() => setIsSidebarOpen(false), []);

  // Mobile-named aliases for the same sidebar state — Sidebar.jsx and
  // MainPanel.jsx consume these names (open/close on small screens).
  const openMobileSidebar = useCallback(() => setIsSidebarOpen(true), []);
  const closeMobileSidebar = useCallback(() => setIsSidebarOpen(false), []);

  return (
    <UIContext.Provider
      value={{
        isComposerOpen,
        openComposer,
        closeComposer,
        toggleComposer,
        isSidebarOpen,
        toggleSidebar,
        closeSidebar,
        isMobileSidebarOpen: isSidebarOpen,
        openMobileSidebar,
        closeMobileSidebar,
      }}
    >
      {children}
    </UIContext.Provider>
  );
}

export function useUI() {
  const ctx = useContext(UIContext);
  if (!ctx) {
    throw new Error('useUI must be used within UIProvider');
  }
  return ctx;
}
