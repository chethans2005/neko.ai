import { History, Pencil } from 'lucide-react';

/**
 * SlidePreview Component
 * 
 * Displays a preview card for a single slide.
 */
function SlidePreview({ slide, onEdit, isUpdating = false }) {
  // Get the current version of the slide
  const currentVersion = slide.versions[slide.current_version];
  const hasMultipleVersions = slide.versions.length > 1;

  return (
    <div className="slide-card">
      <div className="slide-card-header">
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div className="slide-number">{slide.slide_number}</div>
          <h3 className="slide-title">{currentVersion.title}</h3>
        </div>
        {hasMultipleVersions && (
          <span style={{ 
            fontSize: '0.75rem', 
            color: 'var(--text-secondary)',
            background: 'var(--bg-tertiary)',
            padding: '2px 8px',
            borderRadius: 'var(--radius-sm)'
          }}>
            v{slide.current_version + 1} of {slide.versions.length}
          </span>
        )}
      </div>

      <div className="slide-content">
        <ul>
          {currentVersion.content.map((bullet, idx) => (
            <li key={idx}>{bullet}</li>
          ))}
        </ul>

        {currentVersion.speaker_notes && (
          <div style={{ 
            marginTop: 'var(--space-md)',
            padding: 'var(--space-sm) var(--space-md)',
            background: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.8rem',
            color: 'var(--text-secondary)'
          }}>
            <strong>Notes:</strong> {currentVersion.speaker_notes}
          </div>
        )}
      </div>

      <div className="slide-actions">
        <button
          className="btn btn-secondary btn-sm"
          onClick={onEdit}
          disabled={isUpdating}
          title="Edit slide"
        >
          <Pencil size={14} aria-hidden="true" />
          Edit Slide
        </button>
        {hasMultipleVersions && (
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => {/* TODO: Show version history modal */}}
            disabled={isUpdating}
            title="Open slide history"
          >
            <History size={14} aria-hidden="true" />
            History
          </button>
        )}
      </div>
    </div>
  );
}

export default SlidePreview;
