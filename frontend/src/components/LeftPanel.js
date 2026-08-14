import React, { useMemo, useState } from 'react';
import { getFields, findTableMeta } from '../lib/projectTree';
import { ChevronIcon, SearchIcon, CheckIcon } from '../icons';

function matches(name, term) {
  return !term || name.toLowerCase().includes(term.toLowerCase());
}

function Checkbox({ checked }) {
  return (
    <span className={`checkbox${checked ? ' checked' : ''}`} role="checkbox" aria-checked={checked}>
      {checked && <CheckIcon />}
    </span>
  );
}

function TableRow({ item, color, checked, onToggle }) {
  return (
    <button className="tree-row" onClick={onToggle}>
      <Checkbox checked={checked} />
      <span className="tree-row-name" style={{ color }}>
        <span className="tree-row-dot">›</span>
        {item.name}
      </span>
    </button>
  );
}

function FieldSubRows({ item, color, selectedFields, onToggleField }) {
  const fields = getFields(item);
  return (
    <div className="field-sub-list">
      {fields.map((field) => {
        const key = `${item.id}::${field.name}`;
        const checked = selectedFields.has(key);
        return (
          <button key={key} className="tree-row field-row" onClick={() => onToggleField(item.id, field.name)}>
            <Checkbox checked={checked} />
            <span className="tree-row-name" style={{ color }}>
              {field.name}
            </span>
            <span className="field-row-type">{field.type}</span>
          </button>
        );
      })}
    </div>
  );
}

function LayerGroup({ layer, viewMode, searchTerm, selectedTables, selectedFields, onToggleTable, onToggleField }) {
  const [open, setOpen] = useState(true);
  const [groupOpen, setGroupOpen] = useState(() => Object.fromEntries(layer.groups.map((g) => [g.type, true])));
  const [expandedTable, setExpandedTable] = useState(null);

  const filteredGroups = useMemo(() => {
    return layer.groups
      .map((group) => ({
        ...group,
        items: group.items.filter((item) => matches(item.name, searchTerm)),
      }))
      .filter((group) => group.items.length > 0);
  }, [layer.groups, searchTerm]);

  if (searchTerm && filteredGroups.length === 0) return null;

  const totalCount = layer.groups.reduce((sum, g) => sum + g.items.length, 0);

  return (
    <div className="layer-group">
      <button className="layer-header" style={{ color: layer.color }} onClick={() => setOpen((v) => !v)}>
        <ChevronIcon open={open} />
        <span className="layer-label">{layer.label}</span>
        <span className="layer-count">{totalCount}</span>
      </button>
      {open && (
        <div className="layer-body">
          {filteredGroups.map((group) => (
            <div className="sub-group" key={group.type}>
              <button
                className="sub-group-header"
                onClick={() => setGroupOpen((prev) => ({ ...prev, [group.type]: !prev[group.type] }))}
              >
                <ChevronIcon open={groupOpen[group.type]} />
                <span>{group.type}</span>
                <span className="layer-count">{group.items.length}</span>
              </button>
              {groupOpen[group.type] && (
                <div className="sub-group-body">
                  {group.items.map((item) => (
                    <div key={item.id}>
                      {viewMode === 'table' ? (
                        <TableRow
                          item={item}
                          color={layer.color}
                          checked={selectedTables.has(item.id)}
                          onToggle={() => onToggleTable(item.id)}
                        />
                      ) : (
                        <>
                          <button
                            className="tree-row expandable"
                            onClick={() => setExpandedTable((cur) => (cur === item.id ? null : item.id))}
                          >
                            <ChevronIcon open={expandedTable === item.id} />
                            <span className="tree-row-name" style={{ color: layer.color }}>
                              {item.name}
                            </span>
                            <span className="field-row-type">{item.fieldCount} fields</span>
                          </button>
                          {expandedTable === item.id && (
                            <FieldSubRows
                              item={item}
                              color={layer.color}
                              selectedFields={selectedFields}
                              onToggleField={onToggleField}
                            />
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SourceGroup({ source, layers, searchTerm }) {
  const [open, setOpen] = useState(false);
  const tables = source.tables
    .filter((t) => matches(t, searchTerm))
    .map((id) => findTableMeta(layers, id))
    .filter(Boolean);

  if (searchTerm && tables.length === 0) return null;

  return (
    <div className="source-group">
      <button className="source-header" onClick={() => setOpen((v) => !v)}>
        <ChevronIcon open={open} />
        <span>{source.name}</span>
      </button>
      {open && (
        <div className="source-body">
          {tables.map((t) => (
            <div className="tree-row source-table" key={t.id}>
              <span className="tree-row-name" style={{ color: t.color }}>
                <span className="tree-row-dot">›</span>
                {t.name}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function LeftPanel({
  hasProject,
  layers,
  sources,
  viewMode,
  selectedTables,
  selectedFields,
  onToggleTable,
  onToggleField,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const hasData = layers.length > 0 || sources.length > 0;

  return (
    <aside className="left-panel">
      <div className="search-bar">
        <SearchIcon />
        <input
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search tables & fields…"
          disabled={!hasProject}
        />
      </div>

      {!hasProject && (
        <div className="left-panel-empty">Select or create a project to see its tables and fields.</div>
      )}

      {hasProject && !hasData && (
        <div className="left-panel-empty">No analysis data available for this project yet.</div>
      )}

      {hasProject && hasData && (
        <div className="left-panel-scroll">
          {layers.map((layer) => (
            <LayerGroup
              key={layer.key}
              layer={layer}
              viewMode={viewMode}
              searchTerm={searchTerm}
              selectedTables={selectedTables}
              selectedFields={selectedFields}
              onToggleTable={onToggleTable}
              onToggleField={onToggleField}
            />
          ))}

          {sources.length > 0 && (
            <div className="sources-section">
              <div className="sources-title">Sources</div>
              {sources.map((source) => (
                <SourceGroup key={source.id} source={source} layers={layers} searchTerm={searchTerm} />
              ))}
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
