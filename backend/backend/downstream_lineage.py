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

Resolving a source name to a table, precisely
-----------------------------------------------
The same table name is routinely reused across warehouses in a TimeXtender
project (a staging table and its MDW counterpart, say), so a bare name isn't
enough to know which table a reference means. Sources produced by
view_lineage.py (sql_col_lineage.py parsing a view's SQL) are schema-
qualified almost always - sql_col_lineage.py's table_name() preserves the
schema/catalog from the SQL, and even a schema-less `FROM x` gets the
referencing view's own schema attached as a fallback (see
sql_col_lineage.Lineage.resolve_select). That schema segment is exactly what
disambiguates a same-named table in a different warehouse, so this file
resolves against it whenever it's present, via a (schema, table) ->
DataTableId map built the same way sql_generate_schema.py builds its
qualify_schema (SchemaName, falling back to the warehouse name).

Known gap: sources produced by table_lineage.py's non-script categories
(table insert mappings, related records, lookup fields) are built straight
from resolved table/field NAMES with no schema attached, so those stay
ambiguous when the name collides - resolved only if the bare name happens
to be globally unique, left unresolved (shown as a dead end, not guessed)
otherwise.
"""

from __future__ import annotations


def _normalize(value: str) -> str:
    return value.strip().lower()


def _parse_source_ref(path: str) -> tuple[str | None, str, str] | None:
    """Split a lineage source path into (schema_or_None, table, column).

    2-part ("table.column") means no schema was available - see the module
    docstring. 3+ parts means the last three are (schema, table, column);
    a leading catalog segment (sql_col_lineage.table_name() includes one
    when present) is dropped, since nothing here tracks catalogs.
    """
    parts = [p for p in path.split(".") if p]
    if len(parts) < 2:
        return None
    if len(parts) == 2:
        return None, parts[0], parts[1]
    return parts[-3], parts[-2], parts[-1]


def _iter_entities(structure: dict):
    """Yield (table_path, entity_name, entity_dict, warehouse_name) for
    every table and view across every project/warehouse."""
    for project in structure.get("Projects", {}).values():
        for warehouse_name, warehouse in project.get("DataWarehouses", {}).items():
            for kind in ("Tables", "Views"):
                for entity_name, entity in warehouse.get(kind, {}).items():
                    yield f"{warehouse_name}.{entity_name}", entity_name, entity, warehouse_name


def _table_registry(structure: dict) -> tuple[dict[tuple[str, str], str], dict[str, str], dict[str, str]]:
    """Three maps built from every table/view in the project:
      - (normalized schema, normalized name) -> DataTableId: resolves a
        schema-qualified reference exactly, even when the bare name is
        reused elsewhere.
      - normalized name -> DataTableId, only for names that are globally
        unique - the best that can be done for a reference with no schema.
      - DataTableId -> name, for turning a resolved id back into the name
        the rest of this file matches sources against.

    Schema is `entity.get("SchemaName") or warehouse_name` - the exact
    fallback sql_generate_schema.generate_schema() uses to build the
    qualify_schema sql_col_lineage.py qualifies every table reference
    against, so this lines up with the schema segment of a 3-part source.
    """
    schema_table_to_id: dict[tuple[str, str], str] = {}
    name_to_ids: dict[str, set[str]] = {}
    id_to_name: dict[str, str] = {}

    for _table_path, entity_name, entity, warehouse_name in _iter_entities(structure):
        table_id = entity.get("DataTableId") or entity_name
        schema_name = entity.get("SchemaName") or warehouse_name
        schema_table_to_id[(_normalize(schema_name), _normalize(entity_name))] = table_id
        name_to_ids.setdefault(_normalize(entity_name), set()).add(table_id)
        id_to_name[table_id] = entity_name

    name_to_id = {name: next(iter(ids)) for name, ids in name_to_ids.items() if len(ids) == 1}
    return schema_table_to_id, name_to_id, id_to_name


def _resolve_table_id(
    schema_name: str | None,
    table_name: str,
    schema_table_to_id: dict[tuple[str, str], str],
    name_to_id: dict[str, str],
) -> str | None:
    """Resolve a (schema, table) reference to a specific DataTableId.

    A schema-qualified reference resolves exactly - no ambiguity, even when
    another table elsewhere shares the same bare name. A schema-less
    reference only resolves if the bare name is unique across the whole
    project; otherwise there's no way to tell which same-named table it
    means, so it's left unresolved rather than guessed at.
    """
    if schema_name:
        return schema_table_to_id.get((_normalize(schema_name), _normalize(table_name)))
    return name_to_id.get(_normalize(table_name))


def build_downstream_index(
    structure: dict,
    schema_table_to_id: dict[tuple[str, str], str],
    name_to_id: dict[str, str],
) -> dict[tuple[str, str], list[dict]]:
    """Maps a resolved (source_table_id, normalized source_column) to every
    field that consumes it, by scanning every entity's ColumnLineage
    (populated by view_lineage.compute_view_lineage /
    table_lineage.compute_table_lineage).

    A source that can't be resolved to a specific table is skipped here -
    it just means that particular consumer can't be attributed as feeding
    off of one of our known tables; get_lineage still shows the clicked
    table's own node regardless.
    """
    index: dict[tuple[str, str], list[dict]] = {}

    for _table_path, entity_name, entity, _warehouse_name in _iter_entities(structure):
        entity_id = entity.get("DataTableId") or entity_name
        for column, lineage in entity.get("ColumnLineage", {}).items():
            for source in lineage.get("sources", []):
                parsed = _parse_source_ref(source)
                if not parsed:
                    continue
                source_schema, source_table, source_column = parsed
                source_id = _resolve_table_id(source_schema, source_table, schema_table_to_id, name_to_id)
                if not source_id:
                    continue
                index.setdefault((source_id, _normalize(source_column)), []).append(
                    {"table_id": entity_id, "column": column}
                )

    return index


def build_upstream_index(structure: dict) -> dict[tuple[str, str], dict]:
    """Maps (table_id, normalized column) to that field's own lineage dict
    (with its "sources"), by scanning every entity's ColumnLineage. Unlike
    `build_downstream_index`, this isn't inverted - a field's sources are
    already sitting right there on the field itself, so no separate
    consumer-lookup is needed to walk upstream.
    """
    index: dict[tuple[str, str], dict] = {}
    for _table_path, entity_name, entity, _warehouse_name in _iter_entities(structure):
        entity_id = entity.get("DataTableId") or entity_name
        for column, lineage in entity.get("ColumnLineage", {}).items():
            index[(entity_id, _normalize(column))] = lineage
    return index


def _upstream_neighbors(
    index: dict[tuple[str, str], dict],
    key: tuple[str, str],
    schema_table_to_id: dict[tuple[str, str], str],
    name_to_id: dict[str, str],
) -> list[dict]:
    """The `sources` of the field at `key`, as {"table_id", "column"}
    neighbors, so upstream and downstream walks can share one BFS in
    `_walk`. A source that can't be resolved to a specific table still
    produces a neighbor - using a pseudo table_id (the raw schema.table or
    table string) so it shows up as a dead-end connected node rather than
    silently vanishing (same treatment a genuinely external/untracked table
    like a raw source table already gets).
    """
    lineage = index.get(key)
    if not lineage:
        return []
    neighbors = []
    for source in lineage.get("sources", []):
        parsed = _parse_source_ref(source)
        if not parsed:
            continue
        schema, table, column = parsed
        table_id = _resolve_table_id(schema, table, schema_table_to_id, name_to_id)
        if table_id is None:
            table_id = f"{schema}.{table}" if schema else table
        neighbors.append({"table_id": table_id, "column": column})
    return neighbors


def _walk(
    get_neighbors,
    seed_keys: set[tuple[str, str]],
    exclude_table_id: str,
    direction: str,
) -> dict[str, list]:
    """Breadth-first walk from `seed_keys` (each a (table_id, normalized
    column) pair), collapsing the field-level ColumnLineage graph into
    table-level nodes/edges (plus the raw field list). `get_neighbors(key)`
    returns the next hop's [{"table_id", "column"}, ...] - consumers for a
    downstream walk, sources for an upstream one.

    Edges are always recorded as {"from": <feeds>, "to": <consumes>} - the
    true data-flow direction - regardless of which direction was walked, so
    lineage reads the same way on the whiteboard either way.

    Table-level edges are derived by collapsing the field-level walk:
    whenever a field in one table is connected to a field in a different
    table, that's an edge between the two tables. Two fields in the same
    table feeding each other (e.g. a hash field over sibling columns) isn't
    a table edge, but the walk still continues through it.

    A key belonging to an unresolved pseudo table_id is a dead end: both
    build_downstream_index and build_upstream_index are keyed by *resolved*
    table_id, so a pseudo id (a raw name string, never a real DataTableId)
    naturally finds no neighbors, and the walk stops there on its own.
    """
    visited_fields = set(seed_keys)
    queue = list(seed_keys)

    visited_tables: set[str] = set()
    edge_seen: set[tuple[str, str]] = set()
    edges: list[dict] = []
    fields: list[dict] = []

    while queue:
        key = queue.pop(0)
        key_table_id = key[0]

        neighbors = get_neighbors(key)
        print(f"[lineage] {key!r} -> {len(neighbors)} neighbor(s): {neighbors}", flush=True)

        for neighbor in neighbors:
            neighbor_table_id = neighbor["table_id"]
            neighbor_key = (neighbor_table_id, _normalize(neighbor["column"]))

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
    print(f"[lineage] get_lineage(table_id={table_id!r}, direction={direction!r}, column={column!r})", flush=True)

    schema_table_to_id, name_to_id, id_to_name = _table_registry(structure)
    start_name = id_to_name.get(table_id)
    print(f"[lineage] id_to_name[{table_id!r}] = {start_name!r}", flush=True)
    if start_name is None:
        print(f"[lineage] {table_id!r} isn't a known DataTableId - nothing to walk", flush=True)
        return {"tables": [], "edges": [], "fields": []}

    if direction == "downstream":
        index = build_downstream_index(structure, schema_table_to_id, name_to_id)
        get_neighbors = lambda key: index.get(key, [])  # noqa: E731
    else:
        index = build_upstream_index(structure)
        get_neighbors = lambda key: _upstream_neighbors(index, key, schema_table_to_id, name_to_id)  # noqa: E731

    if column:
        seed_keys = {(table_id, _normalize(column))}
    else:
        # Both indexes are keyed by (this table's id, column), and in both
        # cases a key only exists for a field that actually has somewhere
        # to go (a consumer, or a source) - so this seeds exactly the
        # fields worth walking from, for either direction.
        seed_keys = {key for key in index if key[0] == table_id}

    print(f"[lineage] seed_keys = {sorted(seed_keys)}", flush=True)

    result = _walk(get_neighbors, seed_keys, exclude_table_id=table_id, direction=direction)
    print(
        f"[lineage] result: {len(result['tables'])} table(s), {len(result['edges'])} edge(s), "
        f"{len(result['fields'])} field(s) -> {result}",
        flush=True,
    )
    return result
