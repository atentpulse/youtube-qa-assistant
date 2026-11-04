import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

const UIContext = createContext(null);
const SIDEBAR_COLLAPSED_KEY = 'ytgenius_sidebar_collapsed';

export function UIProvider({ children }) {
  const [isComposerOpen, setIsComposerOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Desktop sidebar collapsed state (240px expanded vs 64px icon bar)
  const [isSidebarCollapsed, setIsSidebarCollapsedState] = useState(() => {
    if (typeof window === 'undefined') return false;
    try {
      const stored = window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) || window.localStorage.getItem('vidmind_sidebar_collapsed');
      if (stored !== null) {
        return stored === 'true';
      }
      // Default to collapsed on narrower laptop screens (<= 1024px) to protect dual-panel stage
      return window.innerWidth <= 1024;
    } catch {
      return false;
    }
  });

  const openComposer = useCallback(() => setIsComposerOpen(true), []);
  const closeComposer = useCallback(() => setIsComposerOpen(false), []);
  const toggleComposer = useCallback(() => setIsComposerOpen((v) => !v), []);

  const toggleSidebar = useCallback(() => setIsSidebarOpen((v) => !v), []);
  const closeSidebar = useCallback(() => setIsSidebarOpen(false), []);

  // Mobile-named aliases for off-canvas drawer on small screens
  const openMobileSidebar = useCallback(() => setIsSidebarOpen(true), []);
  const closeMobileSidebar = useCallback(() => setIsSidebarOpen(false), []);

  // Desktop collapsible sidebar methods (persisting manual user preference)
  const setSidebarCollapsed = useCallback((collapsed) => {
    setIsSidebarCollapsedState(collapsed);
    try {
      window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed));
    } catch {
      // Ignore storage write failures (e.g. private browsing quota)
    }
  }, []);

  const toggleSidebarCollapse = useCallback(() => {
    setIsSidebarCollapsedState((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next));
      } catch {
        // Ignore storage write failures
      }
      return next;
    });
  }, []);

  // Handle responsive resize: auto-collapse on narrow screens ONLY if user hasn't explicitly set a preference
  useEffect(() => {
    const handleResize = () => {
      try {
        const stored = window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
        if (stored === null && window.innerWidth <= 1024) {
          setIsSidebarCollapsedState(true);
        }
      } catch {
        // Ignore storage read failures
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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
        isSidebarCollapsed,
        setSidebarCollapsed,
        toggleSidebarCollapse,
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
