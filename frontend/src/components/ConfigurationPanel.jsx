import TemplateSelector from './TemplateSelector'
import { THEME_OPTIONS, TONE_OPTIONS } from '../constants/presentationOptions'

function ConfigurationPanel({
  topic,
  setTopic,
  description,
  setDescription,
  numSlides,
  setNumSlides,
  tone,
  setTone,
  theme,
  setTheme,
  template,
  setTemplate,
  isGenerating,
  slidesLength,
  handleGenerate,
  progress,
  progressMessage,
  modelTagText,
}) {
  return (
    <aside className="sidebar hover-scroll">
      <div className="panel config-panel">
        <div className="panel-header">
          <h2>Configuration</h2>
        </div>
        <div className="panel-content hover-scroll">
          <div className="form-group">
            <label className="form-label">Presentation Topic</label>
            <input
              type="text"
              className="form-input topic-input"
              placeholder="Enter presentation topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              disabled={isGenerating}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description <span style={{ color: 'var(--text-secondary)', fontWeight: 'normal' }}>(optional)</span></label>
            <textarea
              className="form-textarea"
              placeholder="Add details like key points to cover, target audience, specific requirements, etc."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isGenerating}
              rows={3}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Number of Slides</label>
            <input
              type="number"
              max={15}
              step={1}
              className="form-input form-number"
              value={numSlides}
              onChange={(e) => setNumSlides(e.target.value)}
              disabled={isGenerating}
            />
            <small className="input-hint"> Maximum 15</small>
          </div>

          <div className="form-group">
            <label className="form-label">Tone</label>
            <select
              className="form-select"
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              disabled={isGenerating || slidesLength > 0}
            >
              {TONE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Theme</label>
            <select
              className="form-select"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              disabled={isGenerating || slidesLength > 0}
            >
              {THEME_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>

          <TemplateSelector
            selected={template}
            onSelect={setTemplate}
            disabled={isGenerating || slidesLength > 0}
          />

          <button
            className="btn btn-primary btn-lg"
            style={{ width: '100%', marginTop: 'var(--space-md)' }}
            onClick={handleGenerate}
            disabled={isGenerating || !topic.trim()}
            title="Generate presentation"
          >
            {isGenerating ? 'Generating...' : 'Generate Presentation'}
          </button>

          <span className="model-tag">{modelTagText}</span>

          {isGenerating && (
            <div style={{ marginTop: 'var(--space-md)' }}>
              <div style={{
                fontSize: '0.875rem',
                color: 'var(--text-secondary)',
                marginBottom: 'var(--space-xs)',
              }}>
                {progressMessage}
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}

export default ConfigurationPanel
