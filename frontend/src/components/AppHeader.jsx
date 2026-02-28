import { Download, History, Info } from 'lucide-react'

function AppHeader({
  user,
  slidesLength,
  profileWrapRef,
  showProfileMenu,
  setShowProfileMenu,
  handleOpenHistory,
  handleLogout,
  setAuthMode,
  setShowAuthModal,
  handleDownload,
  handleNewPresentation,
}) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="brand">
          <div className="brand-logo" aria-hidden="true">
            <img src="/icon.png" alt="neko.ai logo" className="app-logo" />
          </div>
          <div className="brand-text">
            <h1>neko.ai</h1>
          </div>
        </div>
      </div>
      <div className="header-actions">
        <a
          className="btn btn-secondary header-link-btn"
          href="https://github.com/chethans2005"
          target="_blank"
          rel="noreferrer"
          title="About Me"
        >
          <Info size={14} aria-hidden="true" />
          <span>About Me</span>
        </a>
        <button className="btn btn-secondary history-header-btn" onClick={handleOpenHistory} title="Open history">
          <History size={14} aria-hidden="true" />
          <span>History</span>
        </button>
        <div className="profile-wrap" ref={profileWrapRef}>
          {user ? (
            <>
              <button className="btn btn-secondary profile-btn" onClick={() => setShowProfileMenu((v) => !v)} title="Open profile menu">
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt={user.name} className="profile-avatar-image" />
                ) : (
                  <span className="profile-avatar">{(user.name || 'U').slice(0, 1).toUpperCase()}</span>
                )}
                <span>{user.name}</span>
              </button>
              {showProfileMenu && (
                <div className="profile-menu panel">
                  <div className="profile-line"><strong>{user.name}</strong></div>
                  <div className="profile-line">{user.email}</div>
                  <div className="profile-line">Slides generated: {user.requests_generated || 0}</div>
                  <button className="btn btn-sm btn-danger" onClick={handleLogout} title="Logout">Logout</button>
                </div>
              )}
            </>
          ) : (
            <button className="btn btn-secondary" onClick={() => { setAuthMode('login'); setShowAuthModal(true) }} title="Login or sign up">
              Login / Sign Up
            </button>
          )}
        </div>
        {slidesLength > 0 && (
          <>
            <button className="btn btn-success" onClick={handleDownload} title="Download presentation">
              <Download size={15} aria-hidden="true" />
              Download PPT
            </button>
            <button className="btn btn-secondary" onClick={handleNewPresentation} title="Start new presentation">
              New Presentation
            </button>
          </>
        )}
      </div>
    </header>
  )
}

export default AppHeader
