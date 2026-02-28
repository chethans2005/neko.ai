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
  signup,
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

  // Auth + profile state
  const [user, setUser] = useState(null);
  const [historyItems, setHistoryItems] = useState([]);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '' });
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showHistorySidebar, setShowHistorySidebar] = useState(false);
  const [pendingDeleteHistoryId, setPendingDeleteHistoryId] = useState(null);
  const [modelTagText, setModelTagText] = useState('Model: Groq → Gemini fallback');
  const profileWrapRef = useRef(null);

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
    const restore = async () => {
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
  }, [loadHistory]);

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
    if (!authForm.email.trim() || !authForm.password.trim()) {
      showMessage('error', 'Email and password are required');
      return;
    }
    if (authMode === 'signup' && !authForm.name.trim()) {
      showMessage('error', 'Name is required for signup');
      return;
    }

    setIsAuthLoading(true);
    try {
      const response = authMode === 'signup'
        ? await signup(authForm.name.trim(), authForm.email.trim(), authForm.password)
        : await login(authForm.email.trim(), authForm.password);
      await finishAuth(response);
      showMessage('success', authMode === 'signup' ? 'Account created successfully' : 'Login successful');
    } catch (err) {
      showMessage('error', err.response?.data?.detail || err.message || 'Authentication failed');
    } finally {
      setIsAuthLoading(false);
    }
  };

  const handleGoogleAuth = async () => {
    try {
      const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
      if (!googleClientId) {
        showMessage('error', 'Google login is not configured. Set VITE_GOOGLE_CLIENT_ID.');
        return;
      }
      if (!window.google?.accounts?.id) {
        showMessage('error', 'Google Identity SDK is not available.');
        return;
      }

      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (resp) => {
          try {
            const authResponse = await loginWithGoogle(resp.credential);
            await finishAuth(authResponse);
            showMessage('success', 'Google login successful');
          } catch (err) {
            showMessage('error', err.response?.data?.detail || err.message || 'Google login failed');
          }
        },
      });

      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed?.() || notification.isSkippedMoment?.()) {
          showMessage('error', 'Google prompt was blocked or unavailable. Please allow popups/third-party cookies and try again.');
        }
      });
    } catch (err) {
      showMessage('error', err.message || 'Unable to start Google login');
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
    setEditingSlide(null);

    try {
      const response = await updateSlide(sessionId, slideNumber, instruction);
      
      // Update local slides state
      setSlides(prevSlides => 
        prevSlides.map(slide => 
          slide.slide_number === slideNumber ? response.updated_slide : slide
        )
      );

      showMessage('success', `Slide ${slideNumber} updated successfully!`);

    } catch (err) {
      showMessage('error', err.message || 'Failed to update slide');
    } finally {
      setIsUpdatingSlide(false);
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
        onClose={() => setShowAuthModal(false)}
        authMode={authMode}
        setAuthMode={setAuthMode}
        authForm={authForm}
        setAuthForm={setAuthForm}
        isAuthLoading={isAuthLoading}
        onAuthSubmit={handleAuthSubmit}
        onGoogleAuth={handleGoogleAuth}
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
                    isUpdating={isUpdatingSlide}
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
              onCancel={() => setEditingSlide(null)}
              isLoading={isUpdatingSlide}
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
