import React, { useEffect, useMemo, useState } from 'react';
import TopBar from './components/TopBar';
import LeftPanel from './components/LeftPanel';
import Whiteboard from './components/Whiteboard';
import PbipPanel from './components/PbipPanel';
import NewProjectModal from './components/NewProjectModal';
import { transformProjectData } from './lib/transformProjectData';
import { colorForLayer } from './lib/projectTree';

const API_BASE = 'http://127.0.0.1:8000';

// Lineage edges and saved node layouts aren't in the project JSON yet -
// that lands once Step3-5 are adjusted to the new contract.
const NO_EDGES = [];
const NO_DEFAULT_POSITIONS = {};

function App() {
  const [existingProjects, setExistingProjects] = useState([]);
  const [createdProject, setCreatedProject] = useState(null);
  const [projectData, setProjectData] = useState(null);
  const [newProjectModalOpen, setNewProjectModalOpen] = useState(false);
  const [message, setMessage] = useState('');

  const [viewMode, setViewMode] = useState('table');
  const [selectedTables, setSelectedTables] = useState(new Set());
  const [selectedFields, setSelectedFields] = useState(new Set());
  const [selectedModel, setSelectedModel] = useState(null);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [warnings] = useState([]);

  const { layers, sources, semanticModels } = useMemo(() => transformProjectData(projectData), [projectData]);

  const displayLayers = useMemo(() => {
    if (!selectedModel || !selectedModel.tables.length) return layers;
    return [
      ...layers,
      {
        key: `semantic-model-${selectedModel.id}`,
        label: `Semantic Layer — ${selectedModel.name}`,
        color: colorForLayer('Semantic Layer', layers.length),
        groups: [{ type: 'TABLES', items: selectedModel.tables }],
      },
    ];
  }, [layers, selectedModel]);

  useEffect(() => {
    (async () => {
      try {
        const response = await fetch(`${API_BASE}/projects`);
        if (!response.ok) return;
        setExistingProjects(await response.json());
      } catch (err) {
        // backend not reachable yet - leave the list empty
      }
    })();
  }, []);

  const resetWhiteboard = () => {
    setSelectedTables(new Set());
    setSelectedFields(new Set());
    setSelectedModel(null);
  };

  const loadProjectData = async (projectName) => {
    try {
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectName)}/data`);
      if (!response.ok) {
        setProjectData(null);
        return;
      }
      setProjectData(await response.json());
    } catch (err) {
      setProjectData(null);
    }
  };

  const handleToggleTable = (tableId) => {
    setSelectedTables((prev) => {
      const next = new Set(prev);
      if (next.has(tableId)) next.delete(tableId);
      else next.add(tableId);
      return next;
    });
  };

  const handleToggleField = (tableId, fieldName) => {
    setViewMode('field');
    setSelectedFields((prev) => {
      const next = new Set(prev);
      const key = `${tableId}::${fieldName}`;
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleClearWhiteboard = () => {
    setSelectedTables(new Set());
    setSelectedFields(new Set());
  };

  const handleCreateProject = async (name, xmlFile) => {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('xml_file', xmlFile);

    try {
      const response = await fetch(`${API_BASE}/projects`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setExistingProjects((prev) => (prev.includes(data.project) ? prev : [...prev, data.project]));
      setCreatedProject(data.project);
      resetWhiteboard();
      setNewProjectModalOpen(false);

      if (data.warning) {
        setMessage(`Project created, but analysis failed: ${data.warning}`);
        setProjectData(null);
      } else {
        setMessage('Project created successfully.');
        await loadProjectData(data.project);
      }
    } catch (err) {
      setMessage('Could not reach the backend to create the project.');
    }
  };

  const handleSelectProject = (project) => {
    setCreatedProject(project);
    setProjectData(null);
    resetWhiteboard();
    setMessage(`Selected project: ${project}`);
    loadProjectData(project);
  };

  const handleDeleteProject = (project) => {
    setExistingProjects((prev) => prev.filter((p) => p !== project));
    if (createdProject === project) {
      setCreatedProject(null);
      setProjectData(null);
      resetWhiteboard();
      setRightPanelOpen(false);
    }
    setMessage(`Deleted project: ${project}`);
  };

  return (
    <div className="app-shell">
      <TopBar
        existingProjects={existingProjects}
        createdProject={createdProject}
        onSelectProject={handleSelectProject}
        onDeleteProject={handleDeleteProject}
        onNewProject={() => setNewProjectModalOpen(true)}
        semanticModels={semanticModels}
        selectedModel={selectedModel}
        onSelectModel={setSelectedModel}
        rightPanelOpen={rightPanelOpen}
        onToggleRightPanel={() => setRightPanelOpen((v) => !v)}
        warnings={warnings}
      />

      <main className={`workspace${rightPanelOpen ? ' with-right-panel' : ''}`}>
        <LeftPanel
          hasProject={Boolean(createdProject)}
          layers={displayLayers}
          sources={sources}
          viewMode={viewMode}
          selectedTables={selectedTables}
          selectedFields={selectedFields}
          onToggleTable={handleToggleTable}
          onToggleField={handleToggleField}
        />

        <Whiteboard
          layers={displayLayers}
          edges={NO_EDGES}
          defaultPositions={NO_DEFAULT_POSITIONS}
          viewMode={viewMode}
          setViewMode={setViewMode}
          selectedTables={selectedTables}
          selectedFields={selectedFields}
          onClear={handleClearWhiteboard}
        />

        {rightPanelOpen && createdProject && (
          <PbipPanel key={createdProject} selectedFields={selectedFields} onToggleField={handleToggleField} />
        )}
      </main>

      {newProjectModalOpen && (
        <NewProjectModal onCancel={() => setNewProjectModalOpen(false)} onCreate={handleCreateProject} />
      )}

      {message && <div className="toast-bar" onAnimationEnd={() => setMessage('')}>{message}</div>}
    </div>
  );
}

export default App;
