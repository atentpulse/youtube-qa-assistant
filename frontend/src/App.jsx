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
import PrivacyPage from './pages/Legal/PrivacyPage';
import TermsPage from './pages/Legal/TermsPage';
import DisclaimerPage from './pages/Legal/DisclaimerPage';
import ContactPage from './pages/Legal/ContactPage';
import DocsPage from './pages/Legal/DocsPage';
import VerifyEmailPage from './pages/Auth/VerifyEmailPage';
import ResetPasswordPage from './pages/Auth/ResetPasswordPage';

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
                <Route path="/verify-email" element={<VerifyEmailPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
                <Route path="/privacy" element={<PrivacyPage />} />
                <Route path="/terms" element={<TermsPage />} />
                <Route path="/disclaimer" element={<DisclaimerPage />} />
                <Route path="/contact" element={<ContactPage />} />
                <Route path="/docs" element={<DocsPage />} />
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
