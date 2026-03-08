import { Pencil } from 'lucide-react';

/**
 * SlidePreview Component
 * 
 * Displays a preview card for a single slide.
 */
function SlidePreview({ slide, onEdit, onSelectVersion, isUpdating = false, isSwitchingVersion = false }) {
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
          <div className="slide-card-version-switch" role="tablist" aria-label={`Slide ${slide.slide_number} versions`}>
            {slide.versions.map((_, idx) => {
              const isActive = idx === slide.current_version;
              return (
                <button
                  key={`slide-${slide.slide_number}-version-${idx}`}
                  type="button"
                  role="tab"
                  className={`slide-card-version-tab ${isActive ? 'active' : ''}`}
                  aria-selected={isActive}
                  onClick={() => onSelectVersion?.(idx)}
                  disabled={isUpdating || isSwitchingVersion || isActive}
                  title={`Switch to version ${idx + 1}`}
                >
                  {idx + 1}
                </button>
              );
            })}
          </div>
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
          {isUpdating ? 'Updating...' : 'Edit Slide'}
        </button>
        {isUpdating && <span className="slide-update-pill">Applying changes...</span>}
      </div>
    </div>
  );
}

export default SlidePreview;
