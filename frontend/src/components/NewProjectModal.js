import React, { useState } from 'react';

export default function NewProjectModal({ onCancel, onCreate }) {
  const [name, setName] = useState('');
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (trimmed.length < 3 || trimmed.length > 50) {
      setError('Project name must be between 3 and 50 characters.');
      return;
    }
    if (!file || !/\.xml$/i.test(file.name)) {
      setError('Please choose a TimeXtender .xml project file.');
      return;
    }
    setError('');
    setSubmitting(true);
    try {
      await onCreate(trimmed, file);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h3>New project</h3>
        <form className="modal-form" onSubmit={handleSubmit}>
          <label>
            Project name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Analytics Project"
              maxLength={50}
              autoFocus
            />
          </label>
          <label>
            TimeXtender XML
            <div className="file-picker">
              <span className="file-picker-btn">Choose XML…</span>
              <span className="file-picker-name">{file ? file.name : 'No file selected'}</span>
              <input type="file" accept=".xml,.XML" onChange={(e) => setFile(e.target.files[0] || null)} />
            </div>
          </label>
          {error && <div className="modal-error">{error}</div>}
          <div className="modal-actions">
            <button className="secondary-btn" type="button" onClick={onCancel}>
              Cancel
            </button>
            <button className="primary-btn" type="submit" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
