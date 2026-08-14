import React, { useState } from 'react';
import { CaretIcon, WarningIcon, PanelIcon, CloseIcon } from '../icons';

export default function TopBar({
  existingProjects,
  createdProject,
  onSelectProject,
  onDeleteProject,
  onNewProject,
  semanticModels,
  selectedModel,
  onSelectModel,
  rightPanelOpen,
  onToggleRightPanel,
  warnings,
}) {
  const [activeMenu, setActiveMenu] = useState(null);
  const toggleMenu = (menu) => setActiveMenu((cur) => (cur === menu ? null : menu));
  const closeMenu = () => setActiveMenu(null);

  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">DL</div>
        <span className="brand-name">DATA LINEAGE</span>
      </div>

      <div className="topbar-selectors">
        <div className="selector">
          <button className="selector-btn" onClick={() => toggleMenu('project')}>
            <span className="selector-label">PROJECT</span>
            <span className="selector-value">{createdProject || 'Select project'}</span>
            <CaretIcon />
          </button>
          {activeMenu === 'project' && (
            <>
              <div className="menu-backdrop" onClick={closeMenu} />
              <div className="dropdown-panel">
                <div className="dropdown-panel-header">
                  <span>Projects</span>
                  <button className="new-btn" onClick={() => { onNewProject(); closeMenu(); }}>+ New</button>
                </div>
                {existingProjects.length === 0 && <div className="dropdown-empty">No projects yet</div>}
                {existingProjects.map((project) => (
                  <div
                    key={project}
                    className={`dropdown-row${project === createdProject ? ' selected' : ''}`}
                    onClick={() => { onSelectProject(project); closeMenu(); }}
                  >
                    <span>{project}</span>
                    <button
                      className="row-delete"
                      onClick={(e) => { e.stopPropagation(); onDeleteProject(project); }}
                      aria-label={`Delete ${project}`}
                    >
                      <CloseIcon />
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="selector">
          <button className="selector-btn" disabled={!createdProject} onClick={() => toggleMenu('model')}>
            <span className="selector-label">MODEL</span>
            <span className="selector-value">{selectedModel ? selectedModel.name : 'Select model'}</span>
            <CaretIcon />
          </button>
          {activeMenu === 'model' && (
            <>
              <div className="menu-backdrop" onClick={closeMenu} />
              <div className="dropdown-panel wide">
                <div className="dropdown-panel-header">
                  <span>Semantic models</span>
                </div>
                {semanticModels.length === 0 && <div className="dropdown-empty">No semantic models found</div>}
                {semanticModels.map((model) => (
                  <div
                    key={model.id}
                    className={`model-row${selectedModel?.id === model.id ? ' selected' : ''}`}
                    onClick={() => { onSelectModel(model); closeMenu(); }}
                  >
                    <span className="model-dot" />
                    <div>
                      <div className="model-name">{model.name}</div>
                      <div className="model-description">{model.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="topbar-actions">
        <div className="selector">
          <button className="icon-btn" onClick={() => toggleMenu('warnings')} aria-label="Session warnings">
            <WarningIcon />
          </button>
          {activeMenu === 'warnings' && (
            <>
              <div className="menu-backdrop" onClick={closeMenu} />
              <div className="dropdown-panel warnings-panel">
                <div className="dropdown-panel-header">
                  <span><WarningIcon /> Session Warnings</span>
                  <span className="warnings-count">{warnings.length} total</span>
                  <button className="row-delete" onClick={closeMenu}><CloseIcon /></button>
                </div>
                {warnings.length === 0 ? (
                  <div className="dropdown-empty">No warnings this session</div>
                ) : (
                  warnings.map((w, i) => <div key={i} className="warning-row">{w}</div>)
                )}
              </div>
            </>
          )}
        </div>

        <button
          className={`panel-toggle-btn${rightPanelOpen ? ' active' : ''}`}
          disabled={!createdProject}
          onClick={onToggleRightPanel}
        >
          <PanelIcon /> PBIP
        </button>
      </div>
    </header>
  );
}
