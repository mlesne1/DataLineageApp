"""Given a table or field, find everything else connected to it by
ColumnLineage - either everything it feeds (downstream, "what does this feed
into") or everything that feeds it (upstream, "where did this come from") -
so the UI can auto-toggle the whole chain when a user clicks a table/field.

This extracts just the drilldown/graph-walk *mechanism* from the workspace-
root Step5_3_draw_graph_from_excel_failedlineagehandled.py: normalize a
"table.column" reference, walk edges, guard against revisiting a node.
Everything else in that script is specific to generating a static report
and isn't relevant to an interactive click-to-reveal UI action, so it's
left behind: the pyvis HTML graph rendering, the Excel-seeded PBIP
field-usage matching, the semantic-model-entry starting points, and the
"skip date tables" / "_ETL"/"_R" suffix-trimming heuristics (those read as
tuned to one specific TimeXtender project's naming conventions, not
something to carry into a general-purpose implementation).

Step5_3's drill_down() only ever walked upstream. get_lineage() below covers
both directions: upstream reads a field's own ColumnLineage.sources directly;
downstream needs those edges inverted first (build_downstream_index), since
nothing records "what consumes me" directly.

This only reads from `structure`; it doesn't mutate it and isn't run as
part of project creation - call it on demand when a table/field is clicked.

Known gap: ColumnLineage `sources` entries are plain table/column NAMES
(e.g. "stg_orders.order_id"), not the DataTableId/DataFieldId values the
frontend uses to identify whiteboard nodes - matching a name back to an ID
needs a small lookup the frontend or an API layer would still have to do.
"""

from __future__ import annotations


def _normalize(value: str) -> str:
    return value.strip().lower()


def _table_column_key(path: str) -> str | None:
    """Reduce a lineage source path to its last two "table.column" segments.

    ColumnLineage sources are inconsistently 2-part ("table.column") or
    3-part ("warehouse.table.column") depending on which lineage category
    produced them (same-table references know their own warehouse prefix;
    cross-table references only have the resolved table name) - true in
    the old pipeline too, not something introduced here. Keying off the
    last two segments sidesteps that instead of trying to normalize it away.
    """
    parts = [p for p in path.split(".") if p]
    if len(parts) < 2:
        return None
    return _normalize(f"{parts[-2]}.{parts[-1]}")


def _iter_entities(structure: dict):
    """Yield (table_path, entity_name, entity_dict) for every table and view
    across every project/warehouse."""
    for project in structure.get("Projects", {}).values():
        for warehouse_name, warehouse in project.get("DataWarehouses", {}).items():
            for kind in ("Tables", "Views"):
                for entity_name, entity in warehouse.get(kind, {}).items():
                    yield f"{warehouse_name}.{entity_name}", entity_name, entity


def build_downstream_index(structure: dict) -> dict[str, list[dict]]:
    """Maps a normalized "table.column" source key to every field that
    consumes it, by scanning every entity's ColumnLineage (populated by
    view_lineage.compute_view_lineage / table_lineage.compute_table_lineage).
    """
    index: dict[str, list[dict]] = {}

    for table_path, entity_name, entity in _iter_entities(structure):
        for column, lineage in entity.get("ColumnLineage", {}).items():
            for source in lineage.get("sources", []):
                key = _table_column_key(source)
                if not key:
                    continue
                index.setdefault(key, []).append(
                    {"table": entity_name, "table_path": table_path, "column": column}
                )

    return index


def _table_id_and_name_maps(structure: dict) -> tuple[dict[str, str], dict[str, str]]:
    """(normalized name -> DataTableId, DataTableId -> name) across every
    table/view, so downstream results can be expressed as the same
    DataTableId values the frontend already uses for whiteboard nodes.

    A name shared by more than one table (the same table name reused across
    warehouses - common in TimeXtender projects, e.g. a staging table and
    its MDW counterpart) is deliberately left out of name_to_id.
    ColumnLineage only ever records cross-table references by bare name (no
    warehouse/schema qualifier - see `_table_column_key`), so there's no way
    to tell which of the same-named tables a given reference actually meant.
    Guessing one would silently borrow lineage that may belong to a
    different table; leaving it out instead makes that reference resolve
    the same way a genuinely external/untracked table already does (`_walk`
    falls back to the raw name, which never matches a real DataTableId).
    """
    name_to_ids: dict[str, set[str]] = {}
    id_to_name: dict[str, str] = {}
    for _table_path, entity_name, entity in _iter_entities(structure):
        table_id = entity.get("DataTableId") or entity_name
        name_to_ids.setdefault(_normalize(entity_name), set()).add(table_id)
        id_to_name[table_id] = entity_name

    name_to_id = {name: next(iter(ids)) for name, ids in name_to_ids.items() if len(ids) == 1}
    return name_to_id, id_to_name


def build_upstream_index(structure: dict) -> dict[str, dict]:
    """Maps a normalized "table.column" key to that field's own lineage dict
    (with its "sources"), by scanning every entity's ColumnLineage. Unlike
    `build_downstream_index`, this isn't inverted - a field's sources are
    already sitting right there on the field itself, so no separate
    consumer-lookup is needed to walk upstream.
    """
    index: dict[str, dict] = {}
    for _table_path, entity_name, entity in _iter_entities(structure):
        for column, lineage in entity.get("ColumnLineage", {}).items():
            index[_normalize(f"{entity_name}.{column}")] = lineage
    return index


def _upstream_neighbors(index: dict[str, dict], key: str) -> list[dict]:
    """The `sources` of the field at `key`, as the same {"table", "column"}
    shape `build_downstream_index` produces, so upstream and downstream
    walks can share one BFS in `_walk`."""
    lineage = index.get(key)
    if not lineage:
        return []
    neighbors = []
    for source in lineage.get("sources", []):
        source_key = _table_column_key(source)
        if not source_key:
            continue
        source_table, _, source_column = source_key.rpartition(".")
        neighbors.append({"table": source_table, "column": source_column})
    return neighbors


def _walk(
    get_neighbors,
    name_to_id: dict[str, str],
    seed_keys: set[str],
    exclude_table_id: str | None,
    direction: str,
) -> dict[str, list]:
    """Breadth-first walk from `seed_keys`, collapsing the field-level
    ColumnLineage graph into table-level nodes/edges (plus the raw field
    list) resolved to DataTableId values. `get_neighbors(key)` returns the
    next hop's [{"table", "column"}, ...] - consumers for a downstream walk,
    sources for an upstream one.

    Edges are always recorded as {"from": <feeds>, "to": <consumes>} - the
    true data-flow direction - regardless of which direction was walked, so
    lineage reads the same way on the whiteboard either way.

    Table-level edges are derived by collapsing the field-level walk:
    whenever a field in one table is connected to a field in a different
    table, that's an edge between the two tables. Two fields in the same
    table feeding each other (e.g. a hash field over sibling columns) isn't
    a table edge, but the walk still continues through it.

    A key whose table doesn't resolve to a known, unambiguous DataTableId
    (genuinely external/untracked, or a name shared by more than one table -
    see `_table_id_and_name_maps`) is a dead end: it still shows up as a
    connected node (the edge into/out of it is recorded), but the walk
    doesn't expand past it. `build_downstream_index`/`build_upstream_index`
    are themselves keyed by bare name, so blindly querying "its" neighbors
    could silently return data that actually belongs to a different table
    sharing that same name - once identity is uncertain, nothing found past
    that point could be trusted either.
    """
    visited_fields = set(seed_keys)
    queue = list(seed_keys)

    visited_tables: set[str] = set()
    edge_seen: set[tuple[str, str]] = set()
    edges: list[dict] = []
    fields: list[dict] = []

    while queue:
        key = queue.pop(0)
        key_table = key.rsplit(".", 1)[0]
        resolved_id = name_to_id.get(key_table)
        key_table_id = resolved_id if resolved_id is not None else key_table

        if resolved_id is None:
            continue

        for neighbor in get_neighbors(key):
            neighbor_table_id = name_to_id.get(_normalize(neighbor["table"]), neighbor["table"])
            neighbor_key = _normalize(f"{neighbor['table']}.{neighbor['column']}")

            if neighbor_table_id != key_table_id:
                edge = (
                    (key_table_id, neighbor_table_id)
                    if direction == "downstream"
                    else (neighbor_table_id, key_table_id)
                )
                if edge not in edge_seen:
                    edge_seen.add(edge)
                    edges.append({"from": edge[0], "to": edge[1]})
                visited_tables.add(neighbor_table_id)

            if neighbor_key not in visited_fields:
                visited_fields.add(neighbor_key)
                queue.append(neighbor_key)
                fields.append({"table_id": neighbor_table_id, "column": neighbor["column"]})

    visited_tables.discard(exclude_table_id)
    return {"tables": sorted(visited_tables), "edges": edges, "fields": fields}


def get_lineage(structure: dict, table_id: str, direction: str, column: str | None = None) -> dict[str, list]:
    """Everything connected to `table_id` (or just one `column` on it, for a
    single clicked field) via ColumnLineage, transitively through however
    many hops - `direction` is "downstream" (what consumes this, down to
    wherever the data stops being used further) or "upstream" (what feeds
    this, back to wherever the trail goes cold). Returns the connected
    tables/views plus the table-to-table edges connecting them and the raw
    field list, all resolved to DataTableId values.

    `table_id` identifies the table by DataTableId; a semantic-layer table's
    id is the physical DataTableId it's built from, so this only ever walks
    real ColumnLineage data.
    """
    name_to_id, id_to_name = _table_id_and_name_maps(structure)
    start_name = id_to_name.get(table_id)
    if start_name is None:
        return {"tables": [], "edges": [], "fields": []}

    # If another table also has this name, bare "table.column" references
    # elsewhere can't be trusted to mean *this* table specifically (see
    # `_table_id_and_name_maps`) - so there's nothing safe to seed from.
    if name_to_id.get(_normalize(start_name)) != table_id:
        return {"tables": [], "edges": [], "fields": []}

    if direction == "downstream":
        index = build_downstream_index(structure)
        get_neighbors = lambda key: index.get(key, [])  # noqa: E731
    else:
        index = build_upstream_index(structure)
        get_neighbors = lambda key: _upstream_neighbors(index, key)  # noqa: E731

    if column:
        seed_keys = {_normalize(f"{start_name}.{column}")}
    else:
        # Both indexes are keyed the same way (normalized "table.column"),
        # and in both cases a key only exists for a field that actually has
        # somewhere to go (a consumer, or a source) - so this seeds exactly
        # the fields worth walking from, for either direction.
        start_prefix = _normalize(start_name) + "."
        seed_keys = {key for key in index if key.startswith(start_prefix)}

    return _walk(get_neighbors, name_to_id, seed_keys, exclude_table_id=table_id, direction=direction)
