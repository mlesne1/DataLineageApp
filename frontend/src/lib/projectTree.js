// Generic helpers for working with the { layers, sources, semanticModels }
// shape produced by transformProjectData.js. Not mock-specific — these work
// on whatever real layers array is passed in.

const PALETTE = ['#f472b6', '#a78bfa', '#60a5fa', '#34d399', '#fb923c', '#22d3ee'];

const NAME_COLOR_HINTS = [
  { match: /semantic/i, color: '#f472b6' },
  { match: /mdw/i, color: '#a78bfa' },
  { match: /dsa/i, color: '#60a5fa' },
];

export function colorForLayer(name, index) {
  const hint = NAME_COLOR_HINTS.find((h) => h.match.test(name));
  if (hint) return hint.color;
  return PALETTE[index % PALETTE.length];
}

export function getFields(tableMeta) {
  if (!tableMeta) return [];
  if (tableMeta.fields) return tableMeta.fields;
  const count = tableMeta.fieldCount || 0;
  return Array.from({ length: count }, (_, i) => ({
    name: `field_${i + 1}`,
    type: 'VARCHAR',
    source: `field_${i + 1}`,
  }));
}

export function findTableMeta(layers, tableId) {
  for (const layer of layers) {
    for (const group of layer.groups) {
      const found = group.items.find((item) => item.id === tableId);
      if (found) return { ...found, layerKey: layer.key, color: layer.color };
    }
  }
  return null;
}

const TRANSFORM_KINDS = [
  'Field lookup',
  'Transformation',
  'Condition on a transformation',
  'Straight SQL',
  'Table insert',
  'Table transform',
  'Hash of multiple fields',
  'System field',
  'Regular copy of another field',
  'Measure using multiple fields',
];

// Placeholder label until the column-lineage steps (Step3-5) are adjusted to
// the nested JSON contract and can describe a field's real transformation.
export function describeTransform(tableId, field) {
  const seed = (tableId.length + field.name.length) % TRANSFORM_KINDS.length;
  return TRANSFORM_KINDS[seed];
}
