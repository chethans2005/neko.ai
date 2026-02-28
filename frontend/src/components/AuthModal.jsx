function AuthModal({
  show,
  onClose,
  authMode,
  setAuthMode,
  authForm,
  setAuthForm,
  isAuthLoading,
  onAuthSubmit,
  onGoogleAuth,
}) {
  if (!show) return null

  return (
    <div className="auth-overlay" onClick={onClose}>
      <main className="auth-shell" onClick={(e) => e.stopPropagation()}>
        <div className="auth-card panel">
          <div className="panel-header">
            <h2>{authMode === 'signup' ? 'Create account' : 'Welcome back'}</h2>
          </div>
          <div className="panel-content auth-content">
            {authMode === 'signup' && (
              <div className="form-group">
                <label className="form-label">Name</label>
                <input
                  className="form-input"
                  value={authForm.name}
                  onChange={(e) => setAuthForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="Your name"
                  disabled={isAuthLoading}
                />
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Email</label>
              <input
                className="form-input"
                type="email"
                value={authForm.email}
                onChange={(e) => setAuthForm((prev) => ({ ...prev, email: e.target.value }))}
                placeholder="you@example.com"
                disabled={isAuthLoading}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                className="form-input"
                type="password"
                value={authForm.password}
                onChange={(e) => setAuthForm((prev) => ({ ...prev, password: e.target.value }))}
                placeholder="••••••••"
                disabled={isAuthLoading}
              />
            </div>

            <button
              className="btn btn-primary btn-lg"
              onClick={onAuthSubmit}
              disabled={isAuthLoading}
              title={authMode === 'signup' ? 'Sign up' : 'Login'}
            >
              {isAuthLoading ? 'Please wait...' : authMode === 'signup' ? 'Sign Up' : 'Login'}
            </button>

            <button className="btn btn-secondary google-btn" onClick={onGoogleAuth} disabled={isAuthLoading} title="Continue with Google">
              <svg viewBox="0 0 24 24" width="16" height="16" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M21.35 12.23c0-.79-.07-1.55-.21-2.27H12v4.3h5.23a4.47 4.47 0 0 1-1.94 2.94v2.44h3.14c1.84-1.7 2.92-4.2 2.92-7.41z" fill="#4285F4"/>
                <path d="M12 21.7c2.62 0 4.82-.87 6.42-2.36l-3.14-2.44c-.87.58-1.98.92-3.28.92-2.52 0-4.65-1.7-5.4-3.98H3.37v2.51A9.7 9.7 0 0 0 12 21.7z" fill="#34A853"/>
                <path d="M6.6 13.84a5.83 5.83 0 0 1 0-3.68V7.65H3.37a9.7 9.7 0 0 0 0 8.7l3.23-2.51z" fill="#FBBC05"/>
                <path d="M12 6.18c1.43 0 2.71.49 3.72 1.45l2.79-2.79A9.35 9.35 0 0 0 12 2.3a9.7 9.7 0 0 0-8.63 5.35l3.23 2.51c.75-2.28 2.88-3.98 5.4-3.98z" fill="#EA4335"/>
              </svg>
              <span>Continue with Google</span>
            </button>

            <button
              className="btn btn-sm btn-secondary"
              onClick={() => setAuthMode((prev) => (prev === 'signup' ? 'login' : 'signup'))}
              disabled={isAuthLoading}
              title={authMode === 'signup' ? 'Switch to login' : 'Switch to sign up'}
            >
              {authMode === 'signup' ? 'Already have an account? Login' : "Don't have an account? Sign Up"}
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}

export default AuthModal
