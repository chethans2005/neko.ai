import { Download, Trash2, X } from 'lucide-react'

function HistoryDrawer({
  open,
  onClose,
  historyItems,
  formatHistoryDate,
  handleHistoryDownload,
  handleAskDeleteHistory,
}) {
  return (
    <>
      <div className={`history-drawer-backdrop ${open ? 'open' : ''}`} onClick={onClose} />
      <aside className={`history-drawer panel ${open ? 'open' : ''}`}>
        <div className="panel-header">
          <h2>History</h2>
          <button className="btn btn-secondary btn-sm" onClick={onClose} title="Close history">
            <X size={14} aria-hidden="true" />
            <span>Close</span>
          </button>
        </div>
        <div className="panel-content hover-scroll">
          {historyItems.length === 0 ? (
            <div className="history-empty">No presentations yet.</div>
          ) : (
            <div className="history-list">
              {historyItems.map((item) => (
                <div className="history-item" key={item.history_id}>
                  <div>
                    <div className="history-title">{item.topic || item.filename}</div>
                    <div className="history-meta">{item.slide_count} slides • {formatHistoryDate(item.created_at)}</div>
                  </div>
                  <div className="history-actions">
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => handleHistoryDownload(item.history_id, item.filename)}
                      aria-label="Download history item"
                      title="Download"
                    >
                      <Download size={14} aria-hidden="true" />
                    </button>
                    <button
                      className="btn btn-sm btn-secondary history-delete-btn"
                      onClick={() => handleAskDeleteHistory(item.history_id)}
                      aria-label="Delete history item"
                      title="Delete"
                    >
                      <Trash2 size={14} aria-hidden="true" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>
    </>
  )
}

export default HistoryDrawer
