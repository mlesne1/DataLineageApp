import React, { useMemo, useState } from 'react';
import { PBIP_PAGES, REPORT_FILTERS, PAGE_FILTERS } from '../mockData';
import { UploadIcon, ChevronIcon, EyeIcon, GridIcon } from '../icons';

function FilterRow({ filter }) {
  return (
    <div className="filter-row">
      <span className="filter-type">{filter.type}</span>
      <div className="filter-body">
        <div className="filter-field">{filter.field}</div>
        <div className="filter-values">= {filter.values.join(', ')}</div>
      </div>
      <span className="filter-dot" />
    </div>
  );
}

function FilterSection({ title, filters }) {
  const [open, setOpen] = useState(true);
  if (!filters.length) return null;
  return (
    <div className="filter-section">
      <button className="filter-section-header" onClick={() => setOpen((v) => !v)}>
        <ChevronIcon open={open} />
        <span>{title}</span>
        <span className="layer-count">{filters.length}</span>
      </button>
      {open && <div className="filter-section-body">{filters.map((f, i) => <FilterRow key={i} filter={f} />)}</div>}
    </div>
  );
}

function VisualBox({ visual, active, onClick }) {
  return (
    <button
      className={`visual-box${active ? ' active' : ''}`}
      style={{ borderColor: `${visual.color}88`, background: `${visual.color}14`, color: visual.color }}
      onClick={onClick}
    >
      <span className="visual-box-icon" style={{ background: visual.color }} />
      <span className="visual-box-label">{visual.label}</span>
      {visual.hidden && <span className="visual-box-hidden"><EyeIcon off /></span>}
    </button>
  );
}

function GraphExploration({ visual, selectedFields, onToggleField }) {
  return (
    <div className="graph-exploration">
      <div className="graph-exploration-header">
        <GridIcon />
        <span>{visual.label}</span>
        <span className="kind-pill" style={{ borderColor: `${visual.color}88`, color: visual.color }}>
          {visual.kind.toUpperCase()}
        </span>
      </div>

      <div className="graph-section-title">Fields</div>
      <div className="graph-field-list">
        {visual.fields.map((f) => {
          const key = `${f.table}::${f.name}`;
          const checked = selectedFields.has(key);
          return (
            <button
              key={f.role + f.name}
              className={`graph-field-row${checked ? ' checked' : ''}`}
              onClick={() => onToggleField(f.table, f.name)}
            >
              <span className={`checkbox${checked ? ' checked' : ''}`}>{checked ? '✓' : ''}</span>
              <span className="graph-field-role">{f.role}</span>
              <span className="graph-field-name">
                {f.name}
                <span className="graph-field-table">{f.table}{f.agg ? ` · ${f.agg}` : ''}</span>
              </span>
            </button>
          );
        })}
      </div>

      {visual.filters.length > 0 && (
        <>
          <div className="graph-section-title">Visual filters</div>
          {visual.filters.map((f, i) => <FilterRow key={i} filter={f} />)}
        </>
      )}
    </div>
  );
}

export default function PbipPanel({ selectedFields, onToggleField }) {
  const [fileName, setFileName] = useState(null);
  const [activePageId, setActivePageId] = useState(PBIP_PAGES[0].id);
  const [hideHidden, setHideHidden] = useState(false);
  const [expandedVisual, setExpandedVisual] = useState(null);

  const activePage = PBIP_PAGES.find((p) => p.id === activePageId);
  const visibleVisuals = useMemo(
    () => activePage.visuals.filter((v) => !hideHidden || !v.hidden),
    [activePage, hideHidden]
  );
  const expandedVisualData = activePage.visuals.find((v) => v.id === expandedVisual);
  const pageFilters = PAGE_FILTERS[activePageId] || [];

  const handleUpload = (e) => {
    const file = e.target.files[0];
    if (file) setFileName(file.name);
  };

  return (
    <aside className="pbip-panel">
      <div className="pbip-header">
        <div className="pbip-title">
          <span className="pbip-tag">PBIP</span>
          <span className="pbip-filename">{fileName || 'No report uploaded'}</span>
        </div>
        <label className="upload-btn">
          <UploadIcon /> Upload
          <input type="file" accept=".pbip,.zip" hidden onChange={handleUpload} />
        </label>
      </div>

      <div className="pbip-tabs">
        {PBIP_PAGES.map((page) => (
          <button
            key={page.id}
            className={`pbip-tab${page.id === activePageId ? ' active' : ''}`}
            onClick={() => setActivePageId(page.id)}
          >
            {page.hidden && <EyeIcon off />}
            {page.name}
          </button>
        ))}
      </div>

      <div className="pbip-scroll">
        <div className="visual-grid-header">
          <span>Page visuals</span>
          <label className="hide-toggle">
            <input type="checkbox" checked={hideHidden} onChange={(e) => setHideHidden(e.target.checked)} />
            Hide hidden
          </label>
        </div>
        <div className="visual-grid">
          {visibleVisuals.map((v) => (
            <VisualBox
              key={v.id}
              visual={v}
              active={expandedVisual === v.id}
              onClick={() => setExpandedVisual((cur) => (cur === v.id ? null : v.id))}
            />
          ))}
        </div>

        {expandedVisualData && (
          <GraphExploration visual={expandedVisualData} selectedFields={selectedFields} onToggleField={onToggleField} />
        )}

        <FilterSection title="Report filters" filters={REPORT_FILTERS} />
        <FilterSection title="Page filters" filters={pageFilters} />
      </div>
    </aside>
  );
}
