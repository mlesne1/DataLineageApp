"""Builds the sqlglot qualify_schema ({schema: {table: {column: type}}}) that
sql_col_lineage.Lineage uses to resolve unqualified column references.

This is the new-JSON-contract counterpart to the workspace-root
sql_generate_schema.py. That version was written for an older JSON shape
where a view/table's key was a "schema_name.table_name" string that had to
be split on "." to separate the two. In the nested JSON produced by
xml_to_nested_json.build_structure(), tables/views are keyed by their plain
name and each already carries its own SchemaName field, so no splitting is
needed - we just read it directly (falling back to the warehouse name if a
table has none).
"""


def generate_schema(structure: dict) -> dict:
    schema: dict[str, dict[str, dict[str, str]]] = {}

    for project in structure.get("Projects", {}).values():
        for warehouse_name, warehouse in project.get("DataWarehouses", {}).items():
            tables = {**warehouse.get("Tables", {}), **warehouse.get("Views", {})}

            for table_name, table in tables.items():
                columns = {field_name: "INT" for field_name in table.get("Fields", {})}
                if not columns:
                    # Match the old generator's behaviour: a table with no
                    # known fields isn't worth declaring in the schema.
                    continue

                schema_name = table.get("SchemaName") or warehouse_name
                schema.setdefault(schema_name, {})[table_name] = columns

    return schema
