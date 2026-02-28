import { useState } from 'react';

/**
 * ChatInput Component
 * 
 * Provides a chat-like input for entering prompts or instructions.
 */
function ChatInput({ 
  onSubmit, 
  placeholder = "Enter your message...", 
  disabled = false,
  buttonText = "Send"
}) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSubmit(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form className="chat-input-wrapper" onSubmit={handleSubmit}>
      <input
        type="text"
        className="chat-input"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
      />
      <button
        type="submit"
        className="btn btn-primary"
        disabled={disabled || !input.trim()}
        title={buttonText}
      >
        {buttonText}
      </button>
    </form>
  );
}

export default ChatInput;
