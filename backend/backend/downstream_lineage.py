"""Given a field, find every other field downstream of it - i.e. every
field whose lineage traces back to include it as a source - so the UI can
auto-toggle the whole downstream chain when a user clicks a field.

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

The direction is also inverted from Step5_3. Its drill_down() walks
UPSTREAM: from a field to the sources that feed it ("where did this come
from"), which is what makes sense when seeding a graph from semantic/report
fields and tracing back to raw sources. Toggling fields on click needs the
opposite: from a field to what CONSUMES it ("what does this feed into"),
so this walks the same ColumnLineage edges in reverse.

This only reads from `structure`; it doesn't mutate it and isn't run as
part of project creation - call it on demand when a field is clicked.

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


def get_downstream_fields(structure: dict, table: str, column: str) -> list[dict]:
    """Full transitive set of fields downstream of `table.column` (`table`
    is the plain table/view name, matching the ColumnLineage source keys -
    not a DataTableId and not warehouse-qualified).

    Returns a flat, deduplicated list of {"table", "table_path", "column"}
    - every field whose lineage traces back through zero or more hops to
    this one - in breadth-first (nearest-first) order, so the UI can toggle
    them all on directly without needing to walk the graph itself.
    """
    index = build_downstream_index(structure)

    start_key = _normalize(f"{table}.{column}")
    visited = {start_key}
    result: list[dict] = []
    queue = [start_key]

    while queue:
        key = queue.pop(0)
        for consumer in index.get(key, []):
            consumer_key = _normalize(f"{consumer['table']}.{consumer['column']}")
            if consumer_key in visited:
                continue
            visited.add(consumer_key)
            result.append(consumer)
            queue.append(consumer_key)

    return result
