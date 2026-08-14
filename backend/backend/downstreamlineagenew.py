"""Fresh column-level lineage traversal for get_lineage(structure, table_id, direction, column)."""

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class _FieldNode:
    kind: str  # "physical" (Table/View field), "semantic" (SemanticLayerField), or "external" (untracked source)
    table_id: str
    table_name: str
    column: str
    field_id: str | None = None


def _iter_physical_tables(structure: dict):
    for project_name, project in structure.get("Projects", {}).items():
        for warehouse_name, warehouse in project.get("DataWarehouses", {}).items():
            for container in ("Tables", "Views"):
                for table_name, table in warehouse.get(container, {}).items():
                    yield project_name, warehouse_name, container, table_name, table


def _iter_semantic_tables(structure: dict):
    for project_name, project in structure.get("Projects", {}).items():
        for model_name, model in project.get("SemanticLayerModels", {}).items():
            for sl_table_name, sl_table in model.get("SemanticLayerTables", {}).items():
                yield project_name, model_name, sl_table_name, sl_table


def _physical_node(entry: tuple, field_name: str) -> _FieldNode:
    _, _, _, table_name, table = entry
    field = table.get("Fields", {}).get(field_name, {})
    table_id = table.get("DataTableId") or table_name
    return _FieldNode("physical", table_id, table_name, field_name, field.get("DataFieldId"))


def _semantic_node(entry: tuple, field_name: str, sl_field: dict) -> _FieldNode:
    _, _, sl_table_name, sl_table = entry
    table_id = sl_table.get("SemanticLayerTableId") or sl_table_name
    # FieldId (not SemanticLayerFieldId) is what ties this back to the physical field.
    return _FieldNode("semantic", table_id, sl_table_name, field_name, sl_field.get("FieldId"))


def _external_node(ref: str) -> _FieldNode:
    ref = ref.strip()
    suffix = " (unresolved)"
    if ref.endswith(suffix):
        ref = ref[: -len(suffix)]
    table_part, _, column = ref.rpartition(".")
    return _FieldNode("external", table_part or ref, table_part or ref, column)


class _Index:
    """Lookup tables built once per get_lineage() call so a 'sources' string or a semantic
    field's FieldId can be resolved without rescanning the whole structure per node visited."""

    def __init__(self, structure: dict):
        self.by_table_id: dict[str, tuple] = {}
        self.by_table_name: dict[str, list[tuple]] = {}
        self.by_warehouse_table: dict[tuple[str, str], tuple] = {}
        self.by_schema_table: dict[tuple[str, str], tuple] = {}
        self.field_location: dict[str, tuple[tuple, str]] = {}
        self.semantic_by_table_id: dict[str, tuple] = {}
        self.semantic_fields_by_field_id: dict[str, list[tuple[tuple, str, dict]]] = {}
        # (producer table_id, producer column) -> [(consumer entry, consumer column), ...]
        self.reverse_lineage: dict[tuple[str, str], list[tuple[tuple, str]]] = {}

        for entry in _iter_physical_tables(structure):
            _, warehouse_name, _, table_name, table = entry
            table_id = table.get("DataTableId") or table_name
            self.by_table_id[table_id] = entry
            self.by_table_name.setdefault(table_name, []).append(entry)
            self.by_warehouse_table[(warehouse_name, table_name)] = entry
            schema_name = table.get("SchemaName")
            if schema_name:
                self.by_schema_table[(schema_name.lower(), table_name)] = entry
            for field_name, field in table.get("Fields", {}).items():
                field_id = field.get("DataFieldId")
                if field_id:
                    self.field_location[field_id] = (entry, field_name)

        for entry in _iter_semantic_tables(structure):
            _, _, sl_table_name, sl_table = entry
            sl_table_id = sl_table.get("SemanticLayerTableId") or sl_table_name
            self.semantic_by_table_id[sl_table_id] = entry
            for sl_field_name, sl_field in sl_table.get("SemanticLayerFields", {}).items():
                field_id = sl_field.get("FieldId")
                if field_id:
                    self.semantic_fields_by_field_id.setdefault(field_id, []).append(
                        (entry, sl_field_name, sl_field)
                    )

        # Second pass: sources can only be resolved once by_table_name/by_warehouse_table/by_schema_table exist.
        for entry in _iter_physical_tables(structure):
            table = entry[4]
            for field_name, lineage_entry in table.get("ColumnLineage", {}).items():
                for ref in lineage_entry.get("sources", []):
                    resolved = self.resolve_source_ref(ref)
                    if resolved is None:
                        continue
                    producer_entry, producer_field = resolved
                    producer_table_id = producer_entry[4].get("DataTableId") or producer_entry[3]
                    self.reverse_lineage.setdefault((producer_table_id, producer_field), []).append(
                        (entry, field_name)
                    )

    def resolve_source_ref(self, ref: str):
        """'sources' strings mix conventions from different pipeline stages: schema.table.column
        (SQL-parsed view lineage), warehouse.table.column (table_lineage.py's own bookkeeping), or a
        bare table.column. Try each in turn; None means it points outside the structure entirely
        (e.g. a raw, untracked source table), not a bug.
        """
        ref = ref.strip()
        suffix = " (unresolved)"
        if ref.endswith(suffix):
            ref = ref[: -len(suffix)]

        parts = ref.split(".")

        if len(parts) >= 3:
            qualifier, table_name, column = parts[-3], parts[-2], parts[-1]
            entry = self.by_warehouse_table.get((qualifier, table_name))
            if entry is None:
                entry = self.by_schema_table.get((qualifier.lower(), table_name))
            if entry is not None and column in entry[4].get("Fields", {}):
                return entry, column

        if len(parts) >= 2:
            table_name, column = parts[-2], parts[-1]
            for entry in self.by_table_name.get(table_name, []):
                if column in entry[4].get("Fields", {}):
                    return entry, column

        return None


def _downstream_neighbors(node: _FieldNode, index: _Index) -> list[_FieldNode]:
    if node.kind != "physical":
        return []

    neighbors = [
        _physical_node(entry, field_name)
        for entry, field_name in index.reverse_lineage.get((node.table_id, node.column), [])
    ]
    neighbors.extend(
        _semantic_node(entry, field_name, sl_field)
        for entry, field_name, sl_field in index.semantic_fields_by_field_id.get(node.field_id, [])
    )
    return neighbors


def _upstream_neighbors(node: _FieldNode, index: _Index) -> list[_FieldNode]:
    if node.kind == "semantic":
        location = index.field_location.get(node.field_id)
        if location is None:
            return []
        entry, field_name = location
        return [_physical_node(entry, field_name)]

    if node.kind != "physical":
        return []

    table = index.by_table_id[node.table_id][4]
    lineage_entry = table.get("ColumnLineage", {}).get(node.column)
    if not lineage_entry:
        return []

    neighbors = []
    for ref in lineage_entry.get("sources", []):
        resolved = index.resolve_source_ref(ref)
        neighbors.append(_physical_node(*resolved) if resolved else _external_node(ref))
    return neighbors


def _traverse(seeds: list[_FieldNode], direction: str, index: _Index):
    get_neighbors = _downstream_neighbors if direction == "downstream" else _upstream_neighbors

    visited_order = list(seeds)
    visited_set = set(seeds)
    queue = deque(seeds)
    edges: list[tuple[str, str]] = []
    seen_edges = set()

    while queue:
        node = queue.popleft()
        for neighbor in get_neighbors(node, index):
            edge = (
                (node.table_id, neighbor.table_id)
                if direction == "downstream"
                else (neighbor.table_id, node.table_id)
            )
            # Same-table edges (e.g. a hash field sourced from a sibling field) are real lineage but a
            # degenerate, zero-length arrow on a table-level whiteboard, so they're dropped here.
            if edge[0] != edge[1] and edge not in seen_edges:
                seen_edges.add(edge)
                edges.append(edge)

            if neighbor not in visited_set:
                visited_set.add(neighbor)
                visited_order.append(neighbor)
                # Semantic fields (downstream's stopping point) and external sources have nothing further to expand.
                if neighbor.kind == "physical":
                    queue.append(neighbor)

    return visited_order, edges


def get_lineage(structure: dict, table_id: str, direction: str, column: str | None = None) -> dict:
    if direction not in ("upstream", "downstream"):
        return {"error": f"Unknown direction: {direction!r}", "tables": [], "fields": [], "edges": []}

    index = _Index(structure)

    if table_id in index.by_table_id:
        entry = index.by_table_id[table_id]
        fields = entry[4].get("Fields", {})
        names = [column] if column is not None else list(fields)
        seeds = [_physical_node(entry, name) for name in names if name in fields]
    elif table_id in index.semantic_by_table_id:
        entry = index.semantic_by_table_id[table_id]
        sl_fields = entry[3].get("SemanticLayerFields", {})
        names = [column] if column is not None else list(sl_fields)
        seeds = [_semantic_node(entry, name, sl_fields[name]) for name in names if name in sl_fields]
    else:
        return {"error": f"Unknown table_id: {table_id!r}", "tables": [], "fields": [], "edges": []}

    if not seeds:
        return {"tables": [table_id], "fields": [], "edges": []}

    visited, edge_pairs = _traverse(seeds, direction, index)

    tables: list[str] = []
    seen_tables = set()
    for node in visited:
        if node.table_id not in seen_tables:
            seen_tables.add(node.table_id)
            tables.append(node.table_id)

    fields = [{"table_id": node.table_id, "column": node.column} for node in visited]
    edges = [{"from": a, "to": b} for a, b in edge_pairs]

    return {"tables": tables, "fields": fields, "edges": edges}
