import { useState } from 'react';
import { PencilLine, Sparkles, X } from 'lucide-react';

/**
 * SlideEditor Component
 * 
 * Modal/panel for editing a specific slide using natural language.
 */
function SlideEditor({ slideNumber, slide, onSubmit, onSelectVersion, onCancel, isLoading = false }) {
  const [instruction, setInstruction] = useState('');

  const currentVersion = slide?.versions[slide.current_version];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (instruction.trim() && !isLoading) {
      onSubmit(instruction.trim());
    }
  };

  // Suggestion buttons for common edits
  const suggestions = [
    'Make it more concise',
    'Add more technical details',
    'Make it more engaging',
    'Simplify the language',
    'Add an example',
    'Focus on benefits',
  ];

  const handleVersionSelect = (versionIndex) => {
    if (isLoading) return;
    if (versionIndex === slide?.current_version) return;
    if (typeof onSelectVersion === 'function') {
      onSelectVersion(versionIndex);
    }
  };

  const totalVersions = slide?.versions?.length || 0;

  return (
    <section className="slide-edit-shell" aria-live="polite">
      <div className="slide-edit-header">
        <div>
          <p className="slide-edit-kicker">Slide Workshop</p>
          <h4 className="slide-edit-title">
            <span className="slide-edit-title-icon" aria-hidden="true">
              <PencilLine size={14} />
            </span>
            <span>Editing Slide {slideNumber}: {currentVersion?.title}</span>
          </h4>
        </div>
        <div className="slide-edit-controls">
          {totalVersions > 0 && (
            <div className="slide-version-tabs" role="tablist" aria-label={`Slide ${slideNumber} versions`}>
              {slide.versions.map((_, idx) => {
                const isActive = idx === slide.current_version;
                return (
                  <button
                    key={`${slideNumber}-v-${idx}`}
                    type="button"
                    role="tab"
                    className={`slide-version-tab ${isActive ? 'active' : ''}`}
                    aria-selected={isActive}
                    onClick={() => handleVersionSelect(idx)}
                    disabled={isLoading}
                    title={`Switch to version ${idx + 1}`}
                  >
                    {idx + 1}
                  </button>
                );
              })}
            </div>
          )}

          <button
            className="btn btn-danger btn-icon"
            onClick={onCancel}
            disabled={isLoading}
            title="Cancel editing"
            aria-label="Cancel editing"
          >
            <X size={14} aria-hidden="true" />
          </button>
        </div>
      </div>

      <p className="slide-edit-subtext">
        Describe exactly what to change on this slide. Active version: {slide?.current_version + 1 || 1} of {Math.max(1, totalVersions)}.
      </p>

      {/* Quick Suggestions */}
      <div className="slide-edit-suggestions">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            className="slide-suggestion"
            onClick={() => setInstruction(suggestion)}
            disabled={isLoading}
            title={`Use suggestion: ${suggestion}`}
          >
            <Sparkles size={12} aria-hidden="true" />
            {suggestion}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <form className="slide-edit-form" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input slide-edit-input"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="E.g., 'Add more statistics' or 'Make the title more catchy'"
          disabled={isLoading}
          autoFocus
        />
        <button
          type="submit"
          className="btn btn-primary"
          disabled={isLoading || !instruction.trim()}
          title="Update slide"
        >
          {isLoading ? (
            <>
              <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }}></span>
              Updating...
            </>
          ) : (
            'Update Slide'
          )}
        </button>
      </form>
    </section>
  );
}

export default SlideEditor;
