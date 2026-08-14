import React, { useEffect, useMemo, useRef, useState } from 'react';
import { findTableMeta, getFields, describeTransform } from '../lib/projectTree';
import { ClearIcon } from '../icons';

const NODE_WIDTH = 220;
const FALLBACK_COLS = 3;
const FALLBACK_BASE_X = 80;
const FALLBACK_BASE_Y = 460;
const FALLBACK_GAP_X = 260;
const FALLBACK_GAP_Y = 140;

function fallbackPosition(index) {
  const col = index % FALLBACK_COLS;
  const row = Math.floor(index / FALLBACK_COLS);
  return { x: FALLBACK_BASE_X + col * FALLBACK_GAP_X, y: FALLBACK_BASE_Y + row * FALLBACK_GAP_Y };
}

// edges are always {from: upstream, to: downstream} (the true data-flow
// direction) no matter which direction was walked to find them - see
// edgeAnchor below, which always anchors an edge's right side to `from`
// and its left side to `to`. That only draws a clean connector (instead
// of one looping behind both boxes) when upstream nodes actually sit to
// the left of the downstream nodes they feed, so new nodes are ranked by
// longest hop count from a root along from->to edges: upstream/root
// nodes get column 0, and every hop downstream moves a column to the
// right - regardless of whether the user clicked the upstream or the
// downstream end first.
function computeColumns(nodeIds, edges) {
  const nodeIdSet = new Set(nodeIds);
  const incoming = {};
  nodeIds.forEach((id) => { incoming[id] = []; });
  edges.forEach(({ from, to }) => {
    if (nodeIdSet.has(from) && nodeIdSet.has(to)) incoming[to].push(from);
  });

  const column = {};
  const resolving = new Set();
  const columnOf = (id) => {
    if (column[id] !== undefined) return column[id];
    if (resolving.has(id)) return 0; // cycle guard
    resolving.add(id);
    const preds = incoming[id] || [];
    column[id] = preds.length ? Math.max(...preds.map(columnOf)) + 1 : 0;
    resolving.delete(id);
    return column[id];
  };
  nodeIds.forEach(columnOf);
  return column;
}

function edgeAnchor(pos, side) {
  const y = pos.y + 34;
  return side === 'right' ? { x: pos.x + NODE_WIDTH, y } : { x: pos.x, y };
}

function EdgePath({ from, to }) {
  const start = edgeAnchor(from, 'right');
  const end = edgeAnchor(to, 'left');
  const dx = Math.max(60, (end.x - start.x) / 2);
  const d = `M ${start.x} ${start.y} C ${start.x + dx} ${start.y}, ${end.x - dx} ${end.y}, ${end.x} ${end.y}`;
  return <path d={d} className="edge-path" />;
}

function TableNode({ tableId, meta, pos, viewMode, selectedFields, onDragStart, onFieldClick }) {
  const fields = viewMode === 'field'
    ? getFields(meta).filter((f) => selectedFields.has(`${tableId}::${f.name}`))
    : [];

  return (
    <div
      className="board-node"
      style={{ left: pos.x, top: pos.y, borderColor: `${meta.color}66`, background: `${meta.color}0d` }}
      onMouseDown={(e) => onDragStart(e, tableId)}
    >
      <div className="board-node-title" style={{ color: meta.color }}>{meta.name}</div>
      <div className="board-node-meta">{meta.fieldCount} fields</div>
      {viewMode === 'field' && fields.length > 0 && (
        <div className="board-node-fields">
          {fields.map((field) => (
            <button
              key={field.name}
              className="board-node-field"
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => onFieldClick(e, tableId, field)}
            >
              <span className="field-name" style={{ color: meta.color }}>{field.name}</span>
              <span className="field-type">{field.type}</span>
              <span className="field-source">{field.source}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Whiteboard({
  layers,
  edges,
  defaultPositions,
  viewMode,
  setViewMode,
  lineageDirection,
  onDirectionChange,
  selectedTables,
  selectedFields,
  onClear,
}) {
  const containerRef = useRef(null);
  const dragRef = useRef(null);
  const panRef = useRef(null);
  // Nodes the user has manually dragged - the column layout below skips
  // these on every recompute so it never fights a manual placement.
  const draggedIdsRef = useRef(new Set());
  const [positions, setPositions] = useState(defaultPositions);
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [inspect, setInspect] = useState(null);

  const nodeIds = useMemo(() => {
    if (viewMode === 'table') return Array.from(selectedTables);
    const ids = new Set();
    selectedFields.forEach((key) => ids.add(key.split('::')[0]));
    return Array.from(ids);
  }, [viewMode, selectedTables, selectedFields]);

  // Recomputed (not just filled in) on every change: a node revealed early
  // - e.g. the clicked seed - can end up several hops closer to column 0
  // than it truly belongs once a deeper upstream/downstream chain past it
  // is discovered, so its column has to be free to shift, not just get
  // set once. Row is a stable position-within-column, ordered the same
  // way as nodeIds (append-only), so already-placed nodes don't jitter.
  useEffect(() => {
    setPositions((prev) => {
      const columns = computeColumns(nodeIds, edges);
      const rowByColumn = {};
      const next = { ...prev };
      let changed = false;
      nodeIds.forEach((id) => {
        if (draggedIdsRef.current.has(id)) return;
        const col = columns[id];
        const row = rowByColumn[col] || 0;
        rowByColumn[col] = row + 1;
        const x = FALLBACK_BASE_X + col * FALLBACK_GAP_X;
        const y = FALLBACK_BASE_Y + row * FALLBACK_GAP_Y;
        if (!prev[id] || prev[id].x !== x || prev[id].y !== y) {
          next[id] = { x, y };
          changed = true;
        }
      });
      return changed ? next : prev;
    });
  }, [nodeIds, edges]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    const onWheel = (e) => {
      e.preventDefault();
      const delta = -e.deltaY * 0.0012;
      setTransform((t) => ({ ...t, scale: Math.min(2, Math.max(0.5, +(t.scale + delta).toFixed(3))) }));
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  const handleNodeDragStart = (e, tableId) => {
    e.preventDefault();
    draggedIdsRef.current.add(tableId);
    dragRef.current = {
      tableId,
      startX: e.clientX,
      startY: e.clientY,
      origin: positions[tableId] || fallbackPosition(0),
    };
    setInspect(null);
    window.addEventListener('mousemove', handleNodeDragMove);
    window.addEventListener('mouseup', handleNodeDragEnd);
  };

  const handleNodeDragMove = (e) => {
    const drag = dragRef.current;
    if (!drag) return;
    const dx = (e.clientX - drag.startX) / transform.scale;
    const dy = (e.clientY - drag.startY) / transform.scale;
    setPositions((prev) => ({
      ...prev,
      [drag.tableId]: { x: drag.origin.x + dx, y: drag.origin.y + dy },
    }));
  };

  const handleNodeDragEnd = () => {
    dragRef.current = null;
    window.removeEventListener('mousemove', handleNodeDragMove);
    window.removeEventListener('mouseup', handleNodeDragEnd);
  };

  const handlePanStart = (e) => {
    if (e.target.closest('.board-node, .view-toggle, .clear-whiteboard, .field-inspect')) return;
    setInspect(null);
    panRef.current = { startX: e.clientX, startY: e.clientY, origin: { x: transform.x, y: transform.y } };
    window.addEventListener('mousemove', handlePanMove);
    window.addEventListener('mouseup', handlePanEnd);
  };

  const handlePanMove = (e) => {
    const pan = panRef.current;
    if (!pan) return;
    setTransform((t) => ({
      ...t,
      x: pan.origin.x + (e.clientX - pan.startX),
      y: pan.origin.y + (e.clientY - pan.startY),
    }));
  };

  const handlePanEnd = () => {
    panRef.current = null;
    window.removeEventListener('mousemove', handlePanMove);
    window.removeEventListener('mouseup', handlePanEnd);
  };

  const handleFieldClick = (e, tableId, field) => {
    e.stopPropagation();
    setInspect({ tableId, field, kind: describeTransform(tableId, field) });
  };

  const visibleEdges = edges.filter(
    (edge) => nodeIds.includes(edge.from) && nodeIds.includes(edge.to) && positions[edge.from] && positions[edge.to]
  );

  return (
    <section className="whiteboard" ref={containerRef} onMouseDown={handlePanStart}>
      <div className="whiteboard-grid" />

      <div className="whiteboard-toolbar">
        <div className="view-toggle">
          <button className={viewMode === 'table' ? 'active' : ''} onClick={() => setViewMode('table')}>TABLE</button>
          <button className={viewMode === 'field' ? 'active' : ''} onClick={() => setViewMode('field')}>FIELD</button>
        </div>
        <div className="view-toggle">
          <button
            className={lineageDirection === 'downstream' ? 'active' : ''}
            onClick={() => onDirectionChange('downstream')}
          >
            DOWNSTREAM
          </button>
          <button
            className={lineageDirection === 'upstream' ? 'active' : ''}
            onClick={() => onDirectionChange('upstream')}
          >
            UPSTREAM
          </button>
        </div>
      </div>

      <div className="whiteboard-canvas" style={{ transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})` }}>
        <svg className="edge-layer">
          {visibleEdges.map((edge) => (
            <EdgePath key={`${edge.from}-${edge.to}`} from={positions[edge.from]} to={positions[edge.to]} />
          ))}
        </svg>

        {nodeIds.map((tableId) => {
          const meta = findTableMeta(layers, tableId);
          const pos = positions[tableId];
          if (!meta || !pos) return null;
          return (
            <TableNode
              key={tableId}
              tableId={tableId}
              meta={meta}
              pos={pos}
              viewMode={viewMode}
              selectedFields={selectedFields}
              onDragStart={handleNodeDragStart}
              onFieldClick={handleFieldClick}
            />
          );
        })}
      </div>

      {nodeIds.length === 0 && (
        <div className="whiteboard-empty">
          Select {viewMode === 'table' ? 'tables' : 'fields'} from the left panel to populate the whiteboard.
        </div>
      )}

      {inspect && (
        <div className="field-inspect" onMouseDown={(e) => e.stopPropagation()}>
          <div className="field-inspect-header">
            <span>{inspect.tableId}.{inspect.field.name}</span>
            <button onClick={() => setInspect(null)}>×</button>
          </div>
          <div className="field-inspect-row">
            <span className="label">Type</span>
            <span>{inspect.field.type}</span>
          </div>
          <div className="field-inspect-row">
            <span className="label">Transformation</span>
            <span>{inspect.kind}</span>
          </div>
          <div className="field-inspect-row">
            <span className="label">Source</span>
            <span>{inspect.field.source}</span>
          </div>
        </div>
      )}

      <button className="clear-whiteboard" onClick={() => { draggedIdsRef.current.clear(); onClear(); }}>
        <ClearIcon />
        Clear whiteboard
      </button>
    </section>
  );
}
