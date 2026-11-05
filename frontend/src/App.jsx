import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ToastProvider } from './context/ToastContext';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { PreferencesProvider } from './context/PreferencesContext';
import { VideoLibraryProvider } from './context/VideoLibraryContext';
import { ConversationProvider } from './context/ConversationContext';
import ProtectedRoute from './routes/ProtectedRoute';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import OAuthCallbackPage from './pages/OAuthCallbackPage';
import AppPage from './pages/AppPage';
import SettingsPage from './pages/Settings/SettingsPage';

export default function App() {
  return (
    <ToastProvider>
      <ThemeProvider>
        <AuthProvider>
          <PreferencesProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<LoginPage initialMode="register" />} />
                <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
                <Route
                  path="/app"
                  element={
                    <ProtectedRoute>
                      <AppPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/settings"
                  element={
                    <ProtectedRoute>
                      <VideoLibraryProvider>
                        <ConversationProvider>
                          <SettingsPage />
                        </ConversationProvider>
                      </VideoLibraryProvider>
                    </ProtectedRoute>
                  }
                />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </BrowserRouter>
          </PreferencesProvider>
        </AuthProvider>
      </ThemeProvider>
    </ToastProvider>
  );
}
