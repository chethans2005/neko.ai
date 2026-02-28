function DeleteConfirmModal({
  open,
  onCancel,
  onConfirm,
}) {
  if (!open) return null

  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-card panel" onClick={(event) => event.stopPropagation()}>
        <div className="panel-header">
          <h2>Delete History</h2>
        </div>
        <div className="panel-content confirm-content">
          <p>This presentation will be removed from your history.</p>
          <div className="confirm-actions">
            <button className="btn btn-secondary" onClick={onCancel} title="Cancel">
              Cancel
            </button>
            <button className="btn btn-danger" onClick={onConfirm} title="Confirm delete">
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DeleteConfirmModal
