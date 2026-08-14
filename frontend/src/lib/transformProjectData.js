// Converts the raw nested JSON produced by the backend's
// xml_to_nested_json.build_structure() (project -> data warehouses ->
// tables/views -> fields, plus semantic models) into the
// { layers, sources, semanticModels } shape the UI components render.
//
// Table/field relationships (lineage edges, transformation logic) aren't in
// this JSON yet - that lands once Step3-5 are adjusted to the new contract -
// so this only ever produces layers/sources/semanticModels, never edges.

import { colorForLayer } from './projectTree';

const EMPTY = { layers: [], sources: [], semanticModels: [] };

function fieldsFromRaw(rawFields) {
  return Object.entries(rawFields || {}).map(([fieldName, fieldObj]) => ({
    name: fieldName,
    type: String(fieldObj.SqlDataType || fieldObj.DataType || 'UNKNOWN').toUpperCase(),
    source: fieldObj.Name || fieldName,
  }));
}

function tablesFromRaw(rawTables) {
  return Object.entries(rawTables || {}).map(([tableName, tableObj]) => {
    const fields = fieldsFromRaw(tableObj.Fields);
    return {
      id: tableObj.DataTableId || tableName,
      name: tableName,
      fieldCount: fields.length,
      fields,
    };
  });
}

function buildLayers(warehouses) {
  return Object.entries(warehouses || {}).map(([warehouseName, warehouseObj], index) => {
    const groups = [];
    const tables = tablesFromRaw(warehouseObj.Tables);
    const views = tablesFromRaw(warehouseObj.Views);
    if (tables.length) groups.push({ type: 'TABLES', items: tables });
    if (views.length) groups.push({ type: 'VIEWS', items: views });
    return {
      key: warehouseObj.DataWarehouseId || warehouseName,
      label: warehouseName,
      color: colorForLayer(warehouseName, index),
      groups,
    };
  });
}

function buildSources(sourcesObj) {
  const dataSources = (sourcesObj && sourcesObj.DataSources) || {};
  return Object.entries(dataSources).map(([sourceName, sourceObj], index) => ({
    id: sourceObj.DataSourceId || `source_${index}`,
    name: sourceName,
    // Table-to-source linkage isn't available until the lineage steps are wired up.
    tables: [],
  }));
}

function buildSemanticModels(modelsObj) {
  return Object.entries(modelsObj || {}).map(([modelName, modelObj]) => {
    const slTables = modelObj.SemanticLayerTables || {};
    const tableNames = Object.values(slTables)
      .map((table) => table.TableName || table.Name)
      .filter(Boolean);
    return {
      id: modelObj.SemanticLayerModelId || modelName,
      name: modelName,
      description: tableNames.length ? `Tables: ${tableNames.join(', ')}` : 'No tables mapped yet',
      tables: tableNames,
    };
  });
}

export function transformProjectData(raw) {
  if (!raw || !raw.Projects) return EMPTY;

  const projectEntry = Object.values(raw.Projects)[0];
  if (!projectEntry) return EMPTY;

  return {
    layers: buildLayers(projectEntry.DataWarehouses),
    sources: buildSources(projectEntry.Sources),
    semanticModels: buildSemanticModels(projectEntry.SemanticLayerModels),
  };
}
