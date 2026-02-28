import { useState } from 'react';
import { PencilLine } from 'lucide-react';

/**
 * SlideEditor Component
 * 
 * Modal/panel for editing a specific slide using natural language.
 */
function SlideEditor({ slideNumber, slide, onSubmit, onCancel, isLoading = false }) {
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

  return (
    <div className="chat-input-container" style={{ borderTop: '2px solid var(--primary)' }}>
      <div style={{ marginBottom: 'var(--space-md)' }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: 'var(--space-sm)'
        }}>
          <h4 style={{ margin: 0, color: 'var(--primary)' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <PencilLine size={14} aria-hidden="true" />
              <span>Editing Slide {slideNumber}: {currentVersion?.title}</span>
            </span>
          </h4>
          <button 
            className="btn btn-secondary btn-sm"
            onClick={onCancel}
            disabled={isLoading}
            title="Cancel editing"
          >
            Cancel
          </button>
        </div>
        
        <p style={{ 
          fontSize: '0.875rem', 
          color: 'var(--text-secondary)',
          margin: 0 
        }}>
          Describe how you want to change this slide using natural language.
        </p>
      </div>

      {/* Quick Suggestions */}
      <div style={{ 
        display: 'flex', 
        flexWrap: 'wrap', 
        gap: 'var(--space-xs)',
        marginBottom: 'var(--space-md)' 
      }}>
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            className="btn btn-secondary btn-sm"
            onClick={() => setInstruction(suggestion)}
            disabled={isLoading}
            style={{ fontSize: '0.7rem' }}
            title={`Use suggestion: ${suggestion}`}
          >
            {suggestion}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <form className="chat-input-wrapper" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input"
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
    </div>
  );
}

export default SlideEditor;
