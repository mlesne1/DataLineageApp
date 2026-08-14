"""Column-level lineage for TABLES (views are handled by view_lineage.py):
table inserts, related records, transformations, conditional lookup fields,
custom hash fields, and known TX system fields.

This is the new-JSON-contract equivalent of the workspace-root
Step4_compute_tables_col_lineage.py. The lineage *logic* - which category
contributes what, and how - is kept the same. What changes is data access:
the old script needed a separately built "tree structure" file to look up
things like a table insert's source table name, because its JSON didn't
carry that directly (its field-category dicts read like TimeXtender's own
UI property labels - "Copy Field(s)", "Source Field", "Field Mapping(s)" -
suggesting it came from a structure/tree export rather than a raw XML dump).
In the nested JSON produced by xml_to_nested_json.py, that information is
already resolved and attached directly (SourceTableName, LookupTableName,
DataFieldName, ...), so no tree lookup is needed anymore.

Two categories from the old script don't have a confirmed equivalent here
and are handled accordingly rather than guessed at:
  - "custom_fields" (Copy Field(s) / Source Field aggregation): a custom
    field that's just a passthrough/aggregation of another field reads the
    same as a transformation with a simple expression, so it's expected to
    already be covered by _transformations_lineage() rather than needing
    its own category.
  - The exact raw field holding "what a conditional lookup field's value is
    copied from" isn't confirmed against a real export - see
    LOOKUP_SOURCE_FIELD_KEYS below, same category of uncertainty as
    view_lineage.py's SCRIPT_KEYS.
"""

import re

from .sql_col_lineage import Lineage

# NOTE: same category of uncertainty as view_lineage.py's SCRIPT_KEYS -
# "Script" matches the old pipeline's TableInsert field name, not confirmed
# against a real export.
TABLE_INSERT_SCRIPT_KEYS = ("Script", "Text", "SqlScript")

# NOTE: best-effort/unconfirmed. The old JSON's "Source Table Field" (the
# field whose value gets copied into a conditional lookup field) doesn't
# have a clearly identified equivalent in LookupFields' raw payload yet.
LOOKUP_SOURCE_FIELD_KEYS = ("SourceTableField", "Source Table Field", "SourceField")

# TimeXtender's own automatically-added audit/SCD columns (from Step5_3's
# SystemFields list) - a fixed, known vocabulary, so unlike the categories
# above this is a confident match rather than a schema guess.
SYSTEM_FIELD_NAMES = {
    "dw_id",
    "dw_batch",
    "dw_sourcecode",
    "dw_timestamp",
    "scdfromdatetime",
    "scdtodatetime",
    "scdiscurrent",
    "scdistombstone",
}

TRANSFORMATION_FIELD_RE = re.compile(r"\[([^\[\]]+)\]")

USAGE_CONTEXTS = (
    ("sql_where_statement", "where"),
    ("sql_join_statement", "join"),
    ("sql_having_statement", "having"),
    ("sql_group_by_statement", "group_by"),
)


def _add_column_lineage(lineage, target_column, source=None, path=None):
    entry = lineage.setdefault(target_column, {"name": target_column, "sources": [], "paths": []})
    if source and source not in entry["sources"]:
        entry["sources"].append(source)
    if path:
        entry["paths"].append(path)


def _add_required_column(required, column_path, context):
    if not column_path:
        return
    contexts = required.setdefault(column_path, [])
    if context not in contexts:
        contexts.append(context)


def _add_table_used(tables_used, current_path, source_path, context):
    if not source_path or source_path == current_path:
        return
    contexts = tables_used.setdefault(source_path, [])
    if context not in contexts:
        contexts.append(context)


def _extract_transformation_fields(text):
    # Bracket-scan for [Field] references in a free-text Expression/
    # Condition, skipping anything that's actually a function call like
    # [MyFunc](...) - same approach as the old script.
    if not text:
        return []

    matches = []
    for match in TRANSFORMATION_FIELD_RE.finditer(text):
        value = match.group(1)
        cursor = match.end()
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor < len(text) and text[cursor] == "(":
            continue
        matches.append(value)
    return matches


def _table_insert_script(insert):
    for script_record in insert.get("TableInsertScripts", {}).values():
        for key in TABLE_INSERT_SCRIPT_KEYS:
            script = script_record.get(key)
            if script:
                return script
    return None


def _lookup_source_path(lookup_field):
    for key in LOOKUP_SOURCE_FIELD_KEYS:
        value = lookup_field.get(key)
        if value:
            return value.replace("[", "").replace("]", "")
    return None


def _table_inserts_lineage(table, table_path, schema, lineage, tables_used, required, errors):
    for insert_name, insert in table.get("TableInserts", {}).items():
        script = _table_insert_script(insert)

        if script:
            script = script[1:] if script.startswith(";") else script

            try:
                result = Lineage(script, dialect="tsql", qualify_schema=schema).run()
            except Exception as exc:
                errors.append({"context": "TableInsert", "name": insert_name, "error": str(exc)})
                continue

            usage = result.get("usage", {})
            for context, usage_key in USAGE_CONTEXTS:
                for col in usage.get(usage_key, []):
                    _add_required_column(required, col, context)

            for used in usage.get("tables", []):
                _add_table_used(tables_used, table_path, used, "Table Insert Script")

            for col in result.get("columns", []):
                name = col.get("name")
                if not name:
                    continue
                _add_required_column(required, f"{table_path}.{name}", "Table Insert")
                lineage.setdefault(name, col)
            continue

        mappings = insert.get("TableInsertMappings", {})
        if mappings:
            source_table = insert.get("SourceTableName")
            _add_table_used(tables_used, table_path, source_table, "Table Insert Mapping")

            for mapping in mappings.values():
                target_field = mapping.get("DestinationFieldName")
                source_field = mapping.get("SourceFieldName")
                if not target_field:
                    continue

                source_path = f"{source_table}.{source_field}" if source_table and source_field else None
                _add_required_column(required, source_path, "Table Insert")
                _add_column_lineage(
                    lineage,
                    target_field,
                    source_path,
                    ["Table Insert", source_path] if source_path else ["Table Insert"],
                )


def _related_records_lineage(table, table_path, lineage, tables_used, required):
    for related_record in table.get("RelatedRecords", {}).values():
        source_table = related_record.get("LookupTableName")
        _add_table_used(tables_used, table_path, source_table, "Related Record Mapping")

        for mapping in related_record.get("RelatedRecordMappingFields", {}).values():
            target_field = mapping.get("DataFieldName")
            source_field = mapping.get("MappedDataFieldName")
            if not target_field:
                continue

            source_path = f"{source_table}.{source_field}" if source_table and source_field else None
            _add_required_column(required, source_path, "Related Record")
            _add_column_lineage(
                lineage,
                target_field,
                source_path,
                ["Table Transform", source_path] if source_path else ["Table Transform"],
            )

        for relation in related_record.get("RelatedRecordRelations", {}).values():
            field_name = relation.get("DataFieldName")
            if field_name and source_table:
                _add_required_column(required, f"{source_table}.{field_name}", "Related Record Condition")


def _lookup_fields_lineage(table, table_path, lineage, tables_used, required):
    for lookup_field in table.get("LookupFields", {}).values():
        target_field = lookup_field.get("LookupDataFieldName") or lookup_field.get("ConditionalLookupFieldName")
        if not target_field:
            continue

        source_path = _lookup_source_path(lookup_field)
        if source_path:
            source_table = source_path.rsplit(".", 1)[0] if "." in source_path else None
            _add_table_used(tables_used, table_path, source_table, "Lookup Field Mapping")
            _add_required_column(required, source_path, "Lookup Field")
            _add_column_lineage(lineage, target_field, source_path, ["Lookup Field", source_path])

            for join in lookup_field.get("Joins", {}).values():
                join_field = join.get("JoinDataFieldName")
                if join_field:
                    _add_required_column(required, f"{source_table}.{join_field}", "Lookup Field Join")

        for condition in lookup_field.get("Conditions", {}).values():
            cond_field = condition.get("DataFieldName")
            if cond_field:
                _add_column_lineage(lineage, target_field, None, ["Lookup Field Condition", cond_field])


def _transformations_lineage(table, table_path, lineage):
    for transformation in table.get("Transformations", {}).values():
        field = transformation.get("DataFieldName")
        if not field:
            continue

        matches = _extract_transformation_fields(transformation.get("Expression", ""))

        for condition in transformation.get("Conditions", {}).values():
            cond_field = condition.get("DataFieldName")
            if cond_field:
                matches.append(cond_field)

        matches = [m for m in matches if m and m.lower() != field.lower()]

        if matches:
            for match in matches:
                _add_column_lineage(lineage, field, f"{table_path}.{match}", ["Transformation", match])
        else:
            _add_column_lineage(lineage, field, None, ["Fixed Value"])


def _custom_hash_fields_lineage(table, table_path, lineage):
    for host_field, source_fields in table.get("CustomHashFields", {}).items():
        for source_field in source_fields:
            _add_column_lineage(
                lineage,
                host_field,
                f"{table_path}.{source_field}",
                ["Hash Field", source_field],
            )


def _system_fields_lineage(table, lineage):
    for field_name in table.get("Fields", {}):
        if field_name.lower().replace(" ", "") in SYSTEM_FIELD_NAMES:
            _add_column_lineage(lineage, field_name, None, ["System Field"])


def compute_table_lineage(structure: dict, schema: dict) -> dict:
    """Mutates each table (not view) in `structure` in place with
    ColumnLineage / TablesUsed / ColumnsRequired / LineageErrors, and
    returns a {processed_tables} run summary. `schema` is the
    qualify_schema from sql_generate_schema.generate_schema(structure).
    """
    processed_tables: list[str] = []

    for project_name, project in structure.get("Projects", {}).items():
        for warehouse_name, warehouse in project.get("DataWarehouses", {}).items():
            for table_name, table in warehouse.get("Tables", {}).items():
                table_path = f"{warehouse_name}.{table_name}"

                lineage: dict = {}
                tables_used: dict = {}
                required: dict = {}
                errors: list = []

                _table_inserts_lineage(table, table_path, schema, lineage, tables_used, required, errors)
                _related_records_lineage(table, table_path, lineage, tables_used, required)
                _lookup_fields_lineage(table, table_path, lineage, tables_used, required)
                _transformations_lineage(table, table_path, lineage)
                _custom_hash_fields_lineage(table, table_path, lineage)
                _system_fields_lineage(table, lineage)

                table["ColumnLineage"] = lineage
                table["TablesUsed"] = tables_used
                table["ColumnsRequired"] = required
                if errors:
                    table["LineageErrors"] = errors

                processed_tables.append(f"{project_name}.{table_path}")

    return {"processed_tables": processed_tables}
