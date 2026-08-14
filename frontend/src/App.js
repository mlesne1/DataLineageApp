import React, { useEffect, useMemo, useState } from 'react';
import TopBar from './components/TopBar';
import LeftPanel from './components/LeftPanel';
import Whiteboard from './components/Whiteboard';
import PbipPanel from './components/PbipPanel';
import NewProjectModal from './components/NewProjectModal';
import { transformProjectData } from './lib/transformProjectData';
import { colorForLayer } from './lib/projectTree';

const API_BASE = 'http://127.0.0.1:8000';

// Saved node layouts aren't in the project JSON yet.
const NO_DEFAULT_POSITIONS = {};

function App() {
  const [existingProjects, setExistingProjects] = useState([]);
  const [createdProject, setCreatedProject] = useState(null);
  const [projectData, setProjectData] = useState(null);
  const [newProjectModalOpen, setNewProjectModalOpen] = useState(false);
  const [message, setMessage] = useState('');

  const [viewMode, setViewMode] = useState('table');
  const [lineageDirection, setLineageDirection] = useState('downstream');
  const [selectedTables, setSelectedTables] = useState(new Set());
  const [selectedFields, setSelectedFields] = useState(new Set());
  const [selectedModel, setSelectedModel] = useState(null);
  const [edges, setEdges] = useState([]);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [warnings] = useState([]);

  const { layers, sources, semanticModels } = useMemo(() => transformProjectData(projectData), [projectData]);

  const displayLayers = useMemo(() => {
    if (!selectedModel || !selectedModel.tables.length) return layers;
    return [
      ...layers,
      {
        key: `semantic-model-${selectedModel.id}`,
        label: 'Semantic Layer',
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
    setEdges([]);
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

  const mergeEdges = (prev, incoming) => {
    const seen = new Set(prev.map((e) => `${e.from}::${e.to}`));
    const merged = [...prev];
    incoming.forEach((edge) => {
      const key = `${edge.from}::${edge.to}`;
      if (!seen.has(key)) {
        seen.add(key);
        merged.push(edge);
      }
    });
    return merged;
  };

  const applyLineage = (data) => {
    if (data.tables && data.tables.length) {
      setSelectedTables((prev) => {
        const next = new Set(prev);
        data.tables.forEach((id) => next.add(id));
        return next;
      });
    }

    if (data.edges && data.edges.length) {
      setEdges((prev) => mergeEdges(prev, data.edges));
    }

    if (data.fields && data.fields.length) {
      setSelectedFields((prev) => {
        const next = new Set(prev);
        data.fields.forEach((f) => next.add(`${f.table_id}::${f.column}`));
        return next;
      });
    }
  };

  const fetchLineage = async (tableId, column) => {
    if (!createdProject) return;
    try {
      const params = new URLSearchParams({ direction: lineageDirection });
      if (column) params.set('column', column);
      const response = await fetch(
        `${API_BASE}/projects/${encodeURIComponent(createdProject)}/lineage/${encodeURIComponent(tableId)}?${params}`
      );
      if (!response.ok) return;
      applyLineage(await response.json());
    } catch (err) {
      // backend not reachable - the click still registers, just without the drilldown
    }
  };

  const handleToggleTable = (tableId) => {
    const isSelecting = !selectedTables.has(tableId);
    setSelectedTables((prev) => {
      const next = new Set(prev);
      if (next.has(tableId)) next.delete(tableId);
      else next.add(tableId);
      return next;
    });
    if (isSelecting) fetchLineage(tableId);
  };

  const handleToggleField = (tableId, fieldName, sourceColumn) => {
    setViewMode('field');
    const key = `${tableId}::${fieldName}`;
    const isSelecting = !selectedFields.has(key);
    setSelectedFields((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
    if (isSelecting) fetchLineage(tableId, sourceColumn || fieldName);
  };

  const handleClearWhiteboard = () => {
    setSelectedTables(new Set());
    setSelectedFields(new Set());
    setEdges([]);
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
          edges={edges}
          defaultPositions={NO_DEFAULT_POSITIONS}
          viewMode={viewMode}
          setViewMode={setViewMode}
          lineageDirection={lineageDirection}
          setLineageDirection={setLineageDirection}
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
