/**
 * TemplateSelector Component
 * 
 * Allows users to select a presentation template.
 */
import { Briefcase, GraduationCap, Rocket, Sparkles } from 'lucide-react';

const TEMPLATES = [
  { id: 'professional', name: 'Professional', icon: Briefcase, description: 'Clean corporate design' },
  { id: 'startup', name: 'Startup', icon: Rocket, description: 'Bold and modern' },
  { id: 'academic', name: 'Academic', icon: GraduationCap, description: 'Scholarly and formal' },
  { id: 'minimal', name: 'Minimal', icon: Sparkles, description: 'Simple and elegant' },
];

function TemplateSelector({ selected, onSelect, disabled = false }) {
  return (
    <div className="form-group">
      <label className="form-label">Template</label>
      <div className="template-grid">
        {TEMPLATES.map((template) => {
          const Icon = template.icon;
          return (
          <div
            key={template.id}
            className={`template-option ${selected === template.id ? 'selected' : ''} ${disabled ? 'disabled' : ''}`}
            onClick={() => !disabled && onSelect(template.id)}
            style={{ cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.6 : 1 }}
          >
            <div className="template-icon" aria-hidden="true">
              <Icon size={22} />
            </div>
            <div className="template-name">{template.name}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
              {template.description}
            </div>
          </div>
          );
        })}
      </div>
    </div>
  );
}

export default TemplateSelector;
