import { useState, useCallback, useEffect, useRef } from 'react';
import { FileText, Github, Linkedin, Mail } from 'lucide-react';
import SlidePreview from './components/SlidePreview';
import SlideEditor from './components/SlideEditor';
import AuthModal from './components/AuthModal';
import AppHeader from './components/AppHeader';
import ConfigurationPanel from './components/ConfigurationPanel';
import HistoryDrawer from './components/HistoryDrawer';
import DeleteConfirmModal from './components/DeleteConfirmModal';
import AlertToasts from './components/AlertToasts';
import {
  startSession,
  generatePresentation,
  pollJobStatus,
  getPreview,
  updateSlide,
  rollbackSlide,
  signupStart,
  signupVerify,
  login,
  loginWithGoogle,
  getMe,
  getAIStatus,
  getHistory,
  deleteHistoryItem,
  setAuthToken,
  downloadSessionPpt,
  downloadHistoryPpt,
} from './api';

function App() {
  const configuredGoogleLoginUri = import.meta.env.VITE_GOOGLE_LOGIN_URI?.trim();
  const apiBaseForGoogle = import.meta.env.VITE_API_BASE_URL?.trim();
  const derivedGoogleLoginUri = apiBaseForGoogle?.startsWith('http')
    ? `${apiBaseForGoogle.replace(/\/+$/, '')}/auth/google/callback`
    : null;
  const googleLoginUri = configuredGoogleLoginUri || derivedGoogleLoginUri;
  const googleAuthEnabled =
    import.meta.env.VITE_ENABLE_GOOGLE_AUTH?.toLowerCase() !== 'false' &&
    Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim()) &&
    Boolean(googleLoginUri)

  // Session state
  const [sessionId, setSessionId] = useState(null);
  const [topic, setTopic] = useState('');
  const [description, setDescription] = useState('');
  const [numSlides, setNumSlides] = useState('2');
  const [template, setTemplate] = useState('professional');
  const [theme, setTheme] = useState('professional');
  const [tone, setTone] = useState('professional');
  
  // Presentation state
  const [slides, setSlides] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  
  // UI state
  const [alerts, setAlerts] = useState([]);
  const [editingSlide, setEditingSlide] = useState(null);
  const [isUpdatingSlide, setIsUpdatingSlide] = useState(false);
  const [updatingSlideNumber, setUpdatingSlideNumber] = useState(null);
  const [isSwitchingVersion, setIsSwitchingVersion] = useState(false);

  // Auth + profile state
  const [user, setUser] = useState(null);
  const [historyItems, setHistoryItems] = useState([]);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [signupStep, setSignupStep] = useState('form');
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '', otp: '', signupToken: '' });
  const [authError, setAuthError] = useState('');
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showHistorySidebar, setShowHistorySidebar] = useState(false);
  const [pendingDeleteHistoryId, setPendingDeleteHistoryId] = useState(null);
  const [modelTagText, setModelTagText] = useState('Model: Groq → Gemini fallback');
  const profileWrapRef = useRef(null);

  const buildGoogleReturnUrl = useCallback(() => {
    return `${window.location.origin}${window.location.pathname}`;
  }, []);

  const buildGoogleRedirectState = useCallback(() => {
    const payload = {
      return_to: buildGoogleReturnUrl(),
      ts: Date.now(),
    };
    return btoa(JSON.stringify(payload));
  }, [buildGoogleReturnUrl]);

  // Clear messages after timeout
  const showMessage = useCallback((type, message) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setAlerts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setAlerts((prev) => prev.filter((alert) => alert.id !== id));
    }, 5000);
  }, []);

  const parseFilename = (headers, fallback) => {
    const disposition = headers?.['content-disposition'] || headers?.['Content-Disposition'];
    if (!disposition) return fallback;
    const match = disposition.match(/filename\*?=(?:UTF-8''|")?([^";\n]+)/i);
    if (!match?.[1]) return fallback;
    return decodeURIComponent(match[1].replace(/"/g, ''));
  };

  const saveBlobResponse = (response, fallbackName) => {
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    });
    const filename = parseFilename(response.headers, fallbackName);
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  };

  const loadHistory = useCallback(async () => {
    try {
      const data = await getHistory();
      setHistoryItems(data.items || []);
    } catch {
      setHistoryItems([]);
    }
  }, []);

  const finishAuth = useCallback(async (authResponse) => {
    setAuthToken(authResponse.access_token);
    setUser(authResponse.user);
    setShowAuthModal(false);
    setSessionId(null);
    setSlides([]);
    await loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    const completeGoogleRedirectAuth = async () => {
      const params = new URLSearchParams(window.location.search);
      const redirectSource = params.get('source');
      const tokenFromRedirect = params.get('auth_token');
      const authErrorFromRedirect = params.get('error');

      if (redirectSource !== 'google') {
        return false;
      }

      if (authErrorFromRedirect) {
        showMessage('error', authErrorFromRedirect);
        window.history.replaceState({}, '', '/');
        return true;
      }

      if (!tokenFromRedirect) {
        showMessage('error', 'Google redirect login did not return an auth token.');
        window.history.replaceState({}, '', '/');
        return true;
      }

      try {
        setAuthToken(tokenFromRedirect);
        const me = await getMe();
        setUser(me);
        await loadHistory();
        showMessage('success', 'Google login successful');
      } catch {
        setAuthToken(null);
        setUser(null);
        showMessage('error', 'Google login failed while finalizing your session.');
      } finally {
        window.history.replaceState({}, '', '/');
      }

      return true;
    };

    const restore = async () => {
      const handledGoogleRedirect = await completeGoogleRedirectAuth();
      if (handledGoogleRedirect) {
        return;
      }

      const storedToken = localStorage.getItem('auth_token');
      if (!storedToken) {
        setUser(null);
        return;
      }

      try {
        const me = await getMe();
        setUser(me);
        await loadHistory();
      } catch {
        setAuthToken(null);
        setUser(null);
      }
    };

    restore();
  }, [loadHistory, showMessage]);

  useEffect(() => {
    const loadProviderStatus = async () => {
      try {
        const status = await getAIStatus();
        const groq = status?.Groq;
        const gemini = status?.Gemini;

        if (groq && gemini) {
          const groqModel = groq.model || 'Groq';
          const geminiModel = gemini.model || 'Gemini';
          setModelTagText(`Model: ${groqModel} || ${geminiModel}: fallback`);
          return;
        }

        if (groq) {
          setModelTagText(`Model: ${groq.model || 'Groq'}`);
          return;
        }

        if (gemini) {
          setModelTagText(`Model: ${gemini.model || 'Gemini'}`);
          return;
        }

        setModelTagText('Model: AI provider unavailable');
      } catch {
        setModelTagText('Model: Groq → Gemini fallback');
      }
    };

    loadProviderStatus();
  }, []);

  useEffect(() => {
    const handleDocumentClick = (event) => {
      if (!showProfileMenu) return;
      if (profileWrapRef.current?.contains(event.target)) return;
      setShowProfileMenu(false);
    };

    document.addEventListener('mousedown', handleDocumentClick);
    return () => document.removeEventListener('mousedown', handleDocumentClick);
  }, [showProfileMenu]);

  const handleAuthSubmit = async () => {
    setAuthError('');

    if (!authForm.email.trim() || !authForm.password.trim()) {
      const message = 'Email and password are required';
      setAuthError(message);
      showMessage('error', message);
      return;
    }
    if (authMode === 'signup' && signupStep === 'form' && !authForm.name.trim()) {
      const message = 'Name is required for signup';
      setAuthError(message);
      showMessage('error', message);
      return;
    }
    if (authMode === 'signup' && signupStep === 'otp' && !authForm.otp.trim()) {
      const message = 'Please enter the OTP code sent to your email';
      setAuthError(message);
      showMessage('error', message);
      return;
    }

    setIsAuthLoading(true);
    try {
      if (authMode === 'signup' && signupStep === 'form') {
        const response = await signupStart(authForm.name.trim(), authForm.email.trim(), authForm.password);
        setAuthForm((prev) => ({
          ...prev,
          email: authForm.email.trim(),
          name: authForm.name.trim(),
          otp: '',
          signupToken: response.signup_token,
        }));
        setSignupStep('otp');
        setAuthError('');
        showMessage('success', 'OTP sent to your email. Please verify to complete signup.');
        return;
      }

      if (authMode === 'signup' && signupStep === 'otp') {
        const response = await signupVerify(authForm.email.trim(), authForm.otp.trim(), authForm.signupToken);
        await finishAuth(response);
        setSignupStep('form');
        setAuthForm({ name: '', email: '', password: '', otp: '', signupToken: '' });
        setAuthError('');
        showMessage('success', 'Account created successfully');
        return;
      }

      const response = await login(authForm.email.trim(), authForm.password);
      await finishAuth(response);
      setAuthError('');
      showMessage('success', 'Login successful');
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      let message = detail || err?.message || 'Authentication failed';

      if (!err?.response) {
        message = 'Unable to reach server. Please check your connection and try again.';
      } else if (status === 401) {
        message = 'Invalid email or password. Please try again.';
      } else if (status === 404) {
        message = 'Auth service endpoint not found. Backend may not be updated yet.';
      } else if (status === 429) {
        message = detail || 'Too many attempts. Please wait a moment and try again.';
      } else if (status >= 500) {
        message = detail || 'Server error while processing authentication. Please try again shortly.';
      }

      setAuthError(message);
      showMessage('error', message);
    } finally {
      setIsAuthLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setAuthError('');

    if (!authForm.name.trim() || !authForm.email.trim() || !authForm.password.trim()) {
      const message = 'Name, email and password are required to resend OTP';
      setAuthError(message);
      showMessage('error', message);
      return;
    }

    setIsAuthLoading(true);
    try {
      const response = await signupStart(authForm.name.trim(), authForm.email.trim(), authForm.password);
      setAuthForm((prev) => ({ ...prev, signupToken: response.signup_token, otp: '' }));
      setSignupStep('otp');
      setAuthError('');
      showMessage('success', 'New OTP sent to your email');
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      let message = detail || err?.message || 'Failed to resend OTP';

      if (!err?.response) {
        message = 'Unable to reach server. Please check your connection and try again.';
      } else if (status === 404) {
        message = 'OTP endpoint not found. Backend may not be updated yet.';
      } else if (status === 429) {
        message = detail || 'Please wait before requesting another OTP.';
      }

      setAuthError(message);
      showMessage('error', message);
    } finally {
      setIsAuthLoading(false);
    }
  };

  const handleToggleAuthMode = () => {
    setAuthMode((prev) => (prev === 'signup' ? 'login' : 'signup'));
    setSignupStep('form');
    setAuthForm({ name: '', email: '', password: '', otp: '', signupToken: '' });
    setAuthError('');
  };

  const handleGoogleAuth = async () => {
    const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    try {
      if (!googleAuthEnabled) {
        showMessage('error', 'Google login is disabled or not fully configured. Use email signup/login.');
        return;
      }

      if (!googleClientId || !googleLoginUri) {
        showMessage('error', 'Google login is not configured. Set VITE_GOOGLE_CLIENT_ID and VITE_GOOGLE_LOGIN_URI.');
        return;
      }
      if (!window.google?.accounts?.id) {
        showMessage('error', 'Google Identity SDK is not available.');
        return;
      }

      const authResponse = await new Promise((resolve, reject) => {
        let settled = false;
        const finish = (handler, value) => {
          if (settled) return;
          settled = true;
          handler(value);
        };

        window.google.accounts.id.initialize({
          client_id: googleClientId,
          ux_mode: 'popup',
          callback: (response) => {
            if (!response?.credential) {
              finish(reject, new Error('Google did not return a credential.'));
              return;
            }
            finish(resolve, response.credential);
          },
          error_callback: (error) => {
            const reason = error?.type || 'unknown';
            finish(reject, new Error(reason));
          },
        });

        try {
          window.google.accounts.id.prompt();
        } catch {
          finish(reject, new Error('prompt_failed'));
        }

        window.setTimeout(() => {
          finish(reject, new Error('popup_timeout'));
        }, 12000);
      });

      const response = await loginWithGoogle(authResponse);
      await finishAuth(response);
      setAuthError('');
      showMessage('success', 'Google login successful');
    } catch (err) {
      const message = err?.message || 'Unable to start Google login';
      const isPopupIssue = message === 'popup_failed_to_open' || message === 'popup_timeout' || message === 'prompt_failed';
      const isCancel = message === 'popup_closed';

      if (isCancel) {
        showMessage('error', 'Google login was canceled.');
        return;
      }

      if (isPopupIssue) {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          ux_mode: 'redirect',
          login_uri: googleLoginUri,
        });

        // Redirect fallback for strict popup blockers and embedded browsers.
        const holder = document.createElement('div');
        holder.style.position = 'fixed';
        holder.style.left = '-9999px';
        holder.style.top = '-9999px';
        document.body.appendChild(holder);

        window.google.accounts.id.renderButton(holder, {
          type: 'standard',
          size: 'large',
          theme: 'outline',
          text: 'continue_with',
          state: buildGoogleRedirectState(),
        });

        const googleButton = holder.querySelector('div[role="button"], iframe');
        if (!googleButton) {
          holder.remove();
          showMessage('error', 'Unable to start Google login.');
          return;
        }

        googleButton.click();
        window.setTimeout(() => holder.remove(), 2000);
        return;
      }

      showMessage('error', message);
    }
  };

  const handleLogout = () => {
    setAuthToken(null);
    setUser(null);
    setHistoryItems([]);
    setShowProfileMenu(false);
    handleNewPresentation();
  };

  const handleOpenHistory = () => {
    setShowProfileMenu(false);
    if (!user) {
      setAuthMode('login');
      setShowAuthModal(true);
      return;
    }
    setShowHistorySidebar((prev) => !prev);
  };

  // Generate presentation
  const handleGenerate = async () => {
    if (!user) {
      setAuthMode('login');
      setShowAuthModal(true);
      showMessage('error', 'Please login/signup to generate presentations');
      return;
    }

    if (!topic.trim()) {
      showMessage('error', 'Please enter a presentation topic');
      return;
    }

    setIsGenerating(true);
    setProgress(0);
    setProgressMessage('Starting...');
    setSlides([]);

    try {
      // Start session if needed
      let currentSessionId = sessionId;
      if (!currentSessionId) {
        const session = await startSession(theme, tone);
        currentSessionId = session.session_id;
        setSessionId(currentSessionId);
      }

      // Start generation job
      const parsedSlides = Number.parseInt(numSlides, 10);
      const requestedSlides = Number.isNaN(parsedSlides) ? 2 : Math.min(15, parsedSlides);

      const jobResponse = await generatePresentation(
        currentSessionId,
        topic,
        requestedSlides,
        description.trim() || null
      );

      // Poll for completion
      await pollJobStatus(jobResponse.job_id, (status) => {
        setProgress(status.progress || 0);
        setProgressMessage(status.message || 'Processing...');
      });

      // Get preview
      const preview = await getPreview(currentSessionId);
      setSlides(preview.slides);
      await loadHistory();
      setUser((prev) => (prev ? { ...prev, requests_generated: (prev.requests_generated || 0) + preview.slides.length } : prev));
      showMessage('success', `Generated ${preview.slides.length} slides successfully!`);

    } catch (err) {
      showMessage('error', err.response?.data?.detail || err.message || 'Failed to generate presentation');
    } finally {
      setIsGenerating(false);
      setProgress(0);
      setProgressMessage('');
    }
  };

  // Update single slide
  const handleUpdateSlide = async (slideNumber, instruction) => {
    if (!sessionId) return;

    setIsUpdatingSlide(true);
    setUpdatingSlideNumber(slideNumber);

    try {
      const response = await updateSlide(sessionId, slideNumber, instruction);
      
      // Update local slides state
      setSlides(prevSlides => 
        prevSlides.map(slide => 
          slide.slide_number === slideNumber ? response.updated_slide : slide
        )
      );

      showMessage('success', `Slide ${slideNumber} updated successfully!`);
      setEditingSlide(null);

    } catch (err) {
      showMessage('error', err.message || 'Failed to update slide');
    } finally {
      setIsUpdatingSlide(false);
      setUpdatingSlideNumber(null);
    }
  };

  const handleSelectSlideVersion = async (slideNumber, versionIndex) => {
    if (!sessionId || isSwitchingVersion) return;

    setIsSwitchingVersion(true);
    try {
      const response = await rollbackSlide(sessionId, slideNumber, versionIndex);
      setSlides((prevSlides) =>
        prevSlides.map((slide) => {
          if (slide.slide_number !== slideNumber) return slide;
          return {
            ...slide,
            current_version: response.current_version,
          };
        })
      );
      showMessage('success', `Switched to version ${versionIndex + 1} on slide ${slideNumber}`);
    } catch (err) {
      showMessage('error', err.response?.data?.detail || err.message || 'Failed to switch slide version');
    } finally {
      setIsSwitchingVersion(false);
    }
  };

  // Download presentation
  const handleDownload = () => {
    if (!sessionId) return;

    downloadSessionPpt(sessionId)
      .then((response) => saveBlobResponse(response, 'presentation.pptx'))
      .catch((err) => showMessage('error', err.response?.data?.detail || err.message || 'Download failed'));
  };

  const handleHistoryDownload = async (historyId, filename) => {
    try {
      const response = await downloadHistoryPpt(historyId);
      saveBlobResponse(response, filename || 'presentation.pptx');
    } catch (err) {
      showMessage('error', err.response?.data?.detail || err.message || 'History download failed');
    }
  };

  const handleHistoryDelete = async (historyId) => {
    try {
      await deleteHistoryItem(historyId);
      setHistoryItems((prev) => prev.filter((item) => item.history_id !== historyId));
      setPendingDeleteHistoryId(null);
      showMessage('success', 'History item deleted');
    } catch (err) {
      showMessage('error', err.response?.data?.detail || err.message || 'Failed to delete history item');
    }
  };

  // Start new presentation
  const handleNewPresentation = () => {
    setSessionId(null);
    setSlides([]);
    setTopic('');
    setDescription('');
    setNumSlides('2');
    setEditingSlide(null);
  };

  const handleAskDeleteHistory = (historyId) => {
    setPendingDeleteHistoryId(historyId);
    showMessage('info', 'Please confirm deletion in the dialog.');
  };

  const formatHistoryDate = (value) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="app">
      <div className="bg-scene" aria-hidden="true">
        <span className="bg-orb orb-1" />
        <span className="bg-orb orb-2" />
        <span className="bg-orb orb-3" />
        <span className="bg-grid" />
      </div>

      <AuthModal
        show={showAuthModal}
        onClose={() => {
          setShowAuthModal(false)
          setSignupStep('form')
          setAuthError('')
        }}
        authMode={authMode}
        signupStep={signupStep}
        authError={authError}
        authForm={authForm}
        setAuthForm={setAuthForm}
        isAuthLoading={isAuthLoading}
        onAuthSubmit={handleAuthSubmit}
        onToggleAuthMode={handleToggleAuthMode}
        onResendOtp={handleResendOtp}
        onGoogleAuth={handleGoogleAuth}
        showGoogleAuth={googleAuthEnabled}
      />

      <AppHeader
        user={user}
        slidesLength={slides.length}
        profileWrapRef={profileWrapRef}
        showProfileMenu={showProfileMenu}
        setShowProfileMenu={setShowProfileMenu}
        handleOpenHistory={handleOpenHistory}
        handleLogout={handleLogout}
        setAuthMode={setAuthMode}
        setShowAuthModal={setShowAuthModal}
        handleDownload={handleDownload}
        handleNewPresentation={handleNewPresentation}
      />

      {/* Main Content */}
      <main className="main-content">
        <ConfigurationPanel
          topic={topic}
          setTopic={setTopic}
          description={description}
          setDescription={setDescription}
          numSlides={numSlides}
          setNumSlides={setNumSlides}
          tone={tone}
          setTone={setTone}
          theme={theme}
          setTheme={setTheme}
          template={template}
          setTemplate={setTemplate}
          isGenerating={isGenerating}
          slidesLength={slides.length}
          handleGenerate={handleGenerate}
          progress={progress}
          progressMessage={progressMessage}
          modelTagText={modelTagText}
        />

        {/* Preview Area */}
        <section className="preview-area panel">
          <div className="panel-header">
            <h2>
              {slides.length > 0 
                ? `Slides Preview (${slides.length} slides)`
                : 'Slides Preview'
              }
            </h2>
            {slides.length > 0 && (
              <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Click &quot;Edit&quot; to modify individual slides
              </span>
            )}
          </div>
          
          <div className="panel-content preview-scroll hover-scroll">
            {slides.length === 0 && !isGenerating ? (
              <div className="empty-state">
                <div className="empty-state-icon" aria-hidden="true"><FileText size={30} /></div>
                <h3>No Presentation Yet</h3>
                <p>Enter a topic and click &quot;Generate Presentation&quot; to get started.</p>
              </div>
            ) : isGenerating ? (
              <div className="loading">
                <div className="spinner"></div>
                <p>{progressMessage || 'Generating your presentation...'}</p>
              </div>
            ) : (
              <>
                {slides.map((slide) => (
                  <SlidePreview
                    key={slide.slide_number}
                    slide={slide}
                    onEdit={() => setEditingSlide(slide.slide_number)}
                    onSelectVersion={(versionIndex) => handleSelectSlideVersion(slide.slide_number, versionIndex)}
                    isUpdating={isUpdatingSlide && updatingSlideNumber === slide.slide_number}
                    isSwitchingVersion={isSwitchingVersion}
                  />
                ))}
              </>
            )}
          </div>

          {/* Slide Editor */}
          {editingSlide !== null && (
            <SlideEditor
              slideNumber={editingSlide}
              slide={slides.find(s => s.slide_number === editingSlide)}
              onSubmit={(instruction) => handleUpdateSlide(editingSlide, instruction)}
              onSelectVersion={(versionIndex) => handleSelectSlideVersion(editingSlide, versionIndex)}
              onCancel={() => setEditingSlide(null)}
              isLoading={isSwitchingVersion || (isUpdatingSlide && updatingSlideNumber === editingSlide)}
            />
          )}
        </section>
      </main>

      <footer className="app-footer">
        <a className="footer-link" href="mailto:chetansoyal@gmail.com" aria-label="Email chetansoyal@gmail.com">
          <Mail size={14} aria-hidden="true" />
          <span>chetansoyal@gmail.com</span>
        </a>
        <a className="footer-link" href="https://github.com/chethans2005" target="_blank" rel="noreferrer" aria-label="GitHub chethans2005">
          <Github className="footer-icon" size={14} />
          <span>github.com/chethans2005</span>
        </a>
        <a className="footer-link" href="https://www.linkedin.com/in/chethan-s1122/" target="_blank" rel="noreferrer" aria-label="LinkedIn chethan-s1122">
          <Linkedin className="footer-icon" size={14} />
          <span>linkedin.com/in/chethan-s1122/</span>
        </a>
      </footer>

      <HistoryDrawer
        open={showHistorySidebar}
        onClose={() => setShowHistorySidebar(false)}
        historyItems={historyItems}
        formatHistoryDate={formatHistoryDate}
        handleHistoryDownload={handleHistoryDownload}
        handleAskDeleteHistory={handleAskDeleteHistory}
      />

      <DeleteConfirmModal
        open={Boolean(pendingDeleteHistoryId)}
        onCancel={() => setPendingDeleteHistoryId(null)}
        onConfirm={() => handleHistoryDelete(pendingDeleteHistoryId)}
      />

      <AlertToasts alerts={alerts} />
    </div>
  );
}

export default App;
