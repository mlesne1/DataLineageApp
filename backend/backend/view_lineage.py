"""Runs column-level lineage (sql_col_lineage.Lineage) against every view's
SQL definition in the nested project JSON, using a schema built from that
same JSON (sql_generate_schema.generate_schema).

This is the new-JSON-contract equivalent of the workspace-root
Step3_compute_views_col_lineage.py: same idea (build a schema, then run
Lineage on each view's script, recording status/duplicates/required
columns/tables used), adapted to run in-process against the structure
produced by xml_to_nested_json.build_structure() rather than reading and
writing its own JSON files.
"""

from .sql_col_lineage import Lineage

# The raw <ViewDefinitions> record's SQL-text tag isn't confirmed against a
# real TimeXtender export yet - "Script" matches what the old pipeline read,
# the others are fallbacks in case an export uses a different tag.
SCRIPT_KEYS = ("Script", "Definition", "SqlScript")

USAGE_CONTEXTS = (
    ("sql_where_statement", "where"),
    ("sql_join_statement", "join"),
    ("sql_having_statement", "having"),
    ("sql_group_by_statement", "group_by"),
)


def _script_from_view(view: dict) -> str | None:
    definition = view.get("ViewDefinitions") or {}
    for key in SCRIPT_KEYS:
        script = definition.get(key)
        if script:
            return script
    return None


def _columns_required(usage: dict) -> dict[str, list[str]]:
    required: dict[str, list[str]] = {}
    for context, usage_key in USAGE_CONTEXTS:
        for column in usage.get(usage_key, []):
            required.setdefault(column, []).append(context)
    return required


def _duplicate_column_names(columns: list[dict]) -> list[str]:
    seen = set()
    duplicates: list[str] = []
    for col in columns:
        name = col.get("name")
        if not name:
            continue
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)
    return duplicates


def compute_view_lineage(structure: dict, schema: dict) -> dict:
    """Mutates each view in `structure` in place with its lineage result,
    and returns a {succeeded_views, failed_views} run summary. `schema` is
    the qualify_schema from sql_generate_schema.generate_schema(structure) -
    built once by the caller and shared with the table-lineage step.
    """
    succeeded_views: list[str] = []
    failed_views: list[str] = []

    for project_name, project in structure.get("Projects", {}).items():
        for warehouse_name, warehouse in project.get("DataWarehouses", {}).items():
            for view_name, view in warehouse.get("Views", {}).items():
                script = _script_from_view(view)
                if not script:
                    continue

                view_path = f"{project_name}.{warehouse_name}.{view_name}"

                try:
                    result = Lineage(script, dialect="tsql", qualify_schema=schema).run()
                except Exception as exc:
                    view["LineageStatus"] = "failed"
                    view["LineageError"] = str(exc)
                    failed_views.append(view_path)
                    continue

                view["LineageStatus"] = "succeeded"
                succeeded_views.append(view_path)

                columns = result.get("columns", [])
                view["ColumnDuplicates"] = _duplicate_column_names(columns)

                columns_by_name: dict[str, dict] = {}
                for col in columns:
                    name = col.get("name")
                    if name and name not in columns_by_name:
                        columns_by_name[name] = col
                view["ColumnLineage"] = columns_by_name

                usage = result.get("usage", {})
                view["ColumnsRequired"] = _columns_required(usage)
                view["TablesUsed"] = usage.get("tables", [])

    return {"succeeded_views": succeeded_views, "failed_views": failed_views}
