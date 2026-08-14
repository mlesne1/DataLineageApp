"""
Column-level T-SQL lineage analyzer.

Goal
----
For every output column of a (view) query, determine:

  * its STATUS in the table structure:
        - "sourced"  : passthrough of a single upstream column
        - "computed" : expression built from one or more upstream columns
                       (or a non-deterministic function such as GETDATE())
        - "constant" : a literal / NULL (part of the structure, no upstream)
        - "star"     : produced by SELECT * / table.*
  * the full PATH walked to reach the source(s): the chain of hops
        view_output -> derived/cte column -> ... -> physical table column

We work with ONLY the T-SQL text (no database schema required). When a column
cannot be resolved unambiguously without a schema (e.g. an unqualified column
that could come from several joined tables) it is flagged "ambiguous": true and
all candidate paths are returned, rather than silently guessing.

Recursive CTE handling
----------------------
A name introduced by WITH ... AS (...) shadows any physical table/view of the
same name for the duration of the statement. Therefore, if the current CTE body
contains FROM <same_cte_name>, that is a recursive self-reference, not a base
table read, and must not be classified as a physical table source.

This analyzer symbolically represents recursive self-references as CTE hops.
It does not attempt recursive fixpoint expansion of recursive lineage.

Output is JSON-serializable (see `Lineage.run()` / `Lineage.to_json()`).
"""

from __future__ import annotations

import argparse
import json
from collections import namedtuple
import traceback
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify


STAR_SOURCES_KEY = "__star_sources__"

# A single step in a lineage path.
#   node   -> alias / cte name / physical table name / view name
#   column -> column name at that level
#   kind   -> "output" | "cte" | "derived" | "table" | "unknown"
Hop = namedtuple("Hop", ["node", "column", "kind"])


class ScopeSource:
    """A resolved FROM/JOIN source available in the current query scope."""

    __slots__ = ("kind", "name", "columns", "star_sources")

    def __init__(self, kind, name=None, columns=None, star_sources=None):
        self.kind = kind  # "table" | "cte" | "derived" | "recursive_cte"
        self.name = name
        self.columns = columns or {}
        self.star_sources = star_sources or set()


class Lineage:
    def __init__(self, sql, dialect="tsql", debug=False, qualify_schema=None):
        self.sql = sql
        self.dialect = dialect
        self.debug = debug
        self.qualify_schema = qualify_schema

        parsed = sqlglot.parse_one(sql, read=dialect)

        # Target object name (CREATE VIEW [schema].[name] AS ...)
        self.target = self.extract_target(parsed)

        # Schema/namespace of the target view (everything before the last part),
        # normalized. Used to qualify physical tables that are referenced without
        # a schema prefix, e.g. FROM Fact_Controlling -> MDW.Fact_Controlling.
        self.target_schema = self.extract_target_schema()

        # Analyze the query expression of a CREATE statement, else the statement.
        self.root = self.extract_query_from_statement(parsed)

        if qualify_schema:
            for i, v in qualify_schema.items():
                for j, w in v.items():
                    if len(w) == 0:
                        print(f"⚠️ Schema {i} {j} has no tables defined in the schema file.")

        try:
            self.tree = qualify(
                self.root.copy(),
                dialect=dialect,
                schema=qualify_schema,
                # optional but often useful if schema is incomplete:
                allow_partial_qualification=True,
            )
        except Exception as e:
            #print("Exception encountered during SQL qualification. Using unqualified parse tree instead.")
            
            #print(f"Type: {type(e).__name__}")
            print(f"Message: {e}")
            print("SQL:\n", sql)
            #traceback.print_exc()

            self.tree = self.root


        self.ctes = {}

        # Global usage across the whole SQL (CTEs + derived tables included).
        self.usage = {
            "where": set(),
            "join": set(),
            "having": set(),
            "group_by": set(),
            "tables": set(),
        }

    # --------------------------------------------------
    # Normalization helpers
    # --------------------------------------------------
    def clean(self, value):
        if value is None:
            return None

        value = str(value)
        value = value.replace("[", "").replace("]", "")
        value = value.replace('"', "")
        value = value.strip()

        return value

    def norm(self, value):
        value = self.clean(value)

        if value is None:
            return None

        return value.lower()

    # --------------------------------------------------
    # Statement helpers
    # --------------------------------------------------
    def extract_target(self, parsed):
        if not isinstance(parsed, exp.Create):
            return None

        this = parsed.this

        # CREATE TABLE/VIEW may wrap the table in a Schema (with column defs).
        if isinstance(this, exp.Schema):
            this = this.this

        if isinstance(this, exp.Table):
            return self.table_name(this)

        return None

    def extract_target_schema(self):
        """Return the normalized schema/namespace of the target view.

        For a target like ``MDW.VW_Fact_Controlling`` this returns ``mdw``;
        for ``DB.MDW.VW_Fact_Controlling`` it returns ``db.mdw``. Returns
        ``None`` when the target has no schema part (or there is no target).
        """
        if not self.target:
            return None

        parts = self.target.split(".")
        if len(parts) < 2:
            return None

        return self.norm(".".join(parts[:-1]))

    def extract_query_from_statement(self, parsed):
        if isinstance(parsed, exp.Create):
            expression = parsed.args.get("expression")

            if expression is not None:
                return expression

        return parsed

    def table_name(self, table):
        catalog = self.clean(table.args.get("catalog"))
        db = self.clean(table.args.get("db"))
        name = self.clean(table.name)

        parts = [p for p in [catalog, db, name] if p]

        return ".".join(parts)

    def short_name(self, full_name):
        if not full_name:
            return None

        return full_name.split(".")[-1]

    # --------------------------------------------------
    # CTE extraction
    # --------------------------------------------------
    def extract_ctes(self):
        with_exp = self.tree.find(exp.With)

        if not with_exp:
            return

        for cte in with_exp.find_all(exp.CTE):
            cte_name = self.norm(cte.alias)
            self.ctes[cte_name] = cte.this

    # --------------------------------------------------
    # Direct FROM/JOIN sources
    #
    # Returns alias -> source where source is:
    #   - str               : table / cte name
    #   - exp.Expression    : derived table inner query (Select / Union)
    # --------------------------------------------------
    def get_sources(self, node):
        sources = {}

        # sqlglot stores the FROM clause under "from" or "from_" depending on
        # the version; support both.
        from_exp = node.args.get("from") or node.args.get("from_")

        if from_exp and from_exp.this is not None:
            self.add_source(sources, from_exp.this)

        for join in node.args.get("joins") or []:
            if join.this is not None:
                self.add_source(sources, join.this)

        return sources

    def add_source(self, sources, source_expr):
        # Real table / cte reference
        if isinstance(source_expr, exp.Table):
            alias = self.norm(source_expr.alias_or_name)
            sources[alias] = self.norm(self.table_name(source_expr))
            return

        # Derived table: FROM (SELECT ...) BT
        if isinstance(source_expr, exp.Subquery):
            alias = self.norm(source_expr.alias_or_name) or "__subquery__"
            sources[alias] = source_expr.this
            return

        # Defensive: direct SELECT / UNION as a source
        if isinstance(source_expr, (exp.Select, exp.Union)):
            alias = self.norm(source_expr.alias_or_name) or "__subquery__"
            sources[alias] = source_expr

    # --------------------------------------------------
    # Build paths from a single scope source for one column
    # --------------------------------------------------
    def paths_from_source(self, alias, src, column_key):
        out = set()

        if src.kind == "table":
            # No schema: assume the column belongs to this table.
            out.add((Hop(src.name, column_key, "table"),))
            return out

        if src.kind == "recursive_cte":
            # Symbolic recursive self-reference.
            # Do NOT classify this as a physical table.
            if alias == src.name:
                out.add((Hop(src.name, column_key, "cte"),))
            else:
                out.add(
                    (
                        Hop(alias, column_key, "cte"),
                        Hop(src.name, column_key, "cte"),
                    )
                )
            return out

        # cte / derived
        if column_key in src.columns:
            for sub_path in src.columns[column_key]:
                out.add((Hop(alias, column_key, src.kind),) + sub_path)
        elif src.star_sources:
            for base in src.star_sources:
                out.add(
                    (
                        Hop(alias, column_key, src.kind),
                        Hop(base, column_key, "table"),
                    )
                )

        return out

    # --------------------------------------------------
    # Resolve one column reference against the current scope
    # Returns (set_of_paths, ambiguous)
    # --------------------------------------------------
    def resolve_column(self, table, column, scope):
        column_key = self.norm(column)
        table_key = self.norm(table)

        if not column_key:
            return set(), False

        # Qualified column, e.g. BT.BK_ASSET_CD
        if table_key:
            src = scope.get(table_key)

            if src is None:
                # Alias not resolvable from the available SQL.
                return {(Hop(table_key, column_key, "unknown"),)}, False

            return self.paths_from_source(table_key, src, column_key), False

        # Unqualified column: gather every contributing source.
        contributing = []

        for alias, src in scope.items():
            paths = self.paths_from_source(alias, src, column_key)
            if paths:
                contributing.append(paths)

        result = set()
        for paths in contributing:
            result |= paths

        # Ambiguous when more than one source could provide the column and we
        # have no schema to decide which one is correct.
        return result, len(contributing) > 1

    # --------------------------------------------------
    # Resolve an expression's lineage
    # Returns (set_of_paths, ambiguous, had_column)
    # --------------------------------------------------
    def resolve_expr(self, expr, scope):
        if expr is None:
            return set(), False, False

        paths = set()
        ambiguous = False
        had_column = False

        for col in expr.find_all(exp.Column):
            if col.is_star:
                continue

            had_column = True
            col_paths, col_amb = self.resolve_column(col.table, col.name, scope)
            paths |= col_paths
            ambiguous = ambiguous or col_amb

        return paths, ambiguous, had_column

    # --------------------------------------------------
    # Expand SELECT * / table.*
    # Returns (ordered dict col -> set_of_paths, star_sources)
    # --------------------------------------------------
    def expand_star(self, scope, table_alias=None):
        cols = {}
        star_sources = set()

        if table_alias:
            table_alias = self.norm(table_alias)
            selected = (
                [(table_alias, scope[table_alias])]
                if table_alias in scope
                else []
            )
        else:
            selected = list(scope.items())

        for alias, src in selected:
            if src.kind == "table":
                # Unknown columns without a schema -> wildcard pseudo column.
                key = f"{src.name}.*"
                cols[key] = {(Hop(src.name, "*", "table"),)}
                star_sources.add(src.name)
            elif src.kind == "recursive_cte":
                # We don't know the shape without recursively resolving the CTE
                # to a fixpoint, so keep it symbolic.
                key = f"{src.name}.*"
                cols[key] = {(Hop(src.name, "*", "cte"),)}
            else:
                for col_name, sub_paths in src.columns.items():
                    if col_name == STAR_SOURCES_KEY:
                        continue

                    prepend = Hop(alias, col_name, src.kind)
                    cols[col_name] = {(prepend,) + sp for sp in sub_paths}

                star_sources |= src.star_sources

        return cols, star_sources

    # --------------------------------------------------
    # Projection name + expression
    # --------------------------------------------------
    def projection_output_name_and_expr(self, proj):
        if isinstance(proj, exp.Alias):
            return self.norm(proj.alias), proj.this

        return self.norm(proj.alias_or_name), proj

    # --------------------------------------------------
    # Status of an output column
    # --------------------------------------------------
    def column_status(self, expr, had_column):
        if isinstance(expr, exp.Column) and not expr.is_star:
            return "sourced"

        if had_column:
            return "computed"

        if isinstance(expr, (exp.Literal, exp.Null, exp.Boolean)):
            return "constant"

        if isinstance(expr, exp.Neg) and isinstance(expr.this, exp.Literal):
            return "constant"

        # Function call with no columns (GETDATE(), NEWID(), ...) etc.
        return "computed"

    # --------------------------------------------------
    # Resolve a query source (SELECT or UNION)
    # --------------------------------------------------
    def resolve_query_source(
        self,
        query,
        resolved_ctes,
        collect_global_usage=True,
        current_cte_name=None,
    ):
        if isinstance(query, exp.Select):
            return self.resolve_select(
                query,
                resolved_ctes,
                collect_global_usage,
                current_cte_name=current_cte_name,
            )

        if isinstance(query, exp.Union):
            return self.resolve_union(
                query,
                resolved_ctes,
                collect_global_usage,
                current_cte_name=current_cte_name,
            )

        select = query.find(exp.Select)
        if select:
            return self.resolve_select(
                select,
                resolved_ctes,
                collect_global_usage,
                current_cte_name=current_cte_name,
            )

        return self.empty_result()

    def empty_result(self):
        return {
            "columns": {},
            "column_meta": {},
            "star_sources": set(),
            "where": set(),
            "having": set(),
            "group_by": set(),
            "join": set(),
            "tables": set(),
        }

    # --------------------------------------------------
    # UNION: merge lineage by output position
    # --------------------------------------------------
    def resolve_union(
        self,
        node,
        resolved_ctes,
        collect_global_usage=True,
        current_cte_name=None,
    ):
        left = self.resolve_query_source(
            node.left,
            resolved_ctes,
            collect_global_usage,
            current_cte_name=current_cte_name,
        )
        right = self.resolve_query_source(
            node.right,
            resolved_ctes,
            collect_global_usage,
            current_cte_name=current_cte_name,
        )

        merged_cols = {}
        merged_meta = {}

        left_items = list(left["columns"].items())
        right_items = list(right["columns"].items())
        left_meta = list(left["column_meta"].values())
        right_meta = list(right["column_meta"].values())

        max_len = max(len(left_items), len(right_items))

        for i in range(max_len):
            if i < len(left_items):
                out_name, paths = left_items[i][0], set(left_items[i][1])
                meta = dict(left_meta[i])
            else:
                out_name, paths = right_items[i][0], set()
                meta = dict(right_meta[i])

            if i < len(right_items):
                paths |= set(right_items[i][1])

            position_mismatch = (
                i < len(left_items)
                and i < len(right_items)
                and left_items[i][0] != right_items[i][0]
            )
            meta["ambiguous"] = meta.get("ambiguous", False) or position_mismatch

            merged_cols[out_name] = paths
            merged_meta[out_name] = meta

        return {
            "columns": merged_cols,
            "column_meta": merged_meta,
            "star_sources": left["star_sources"] | right["star_sources"],
            "where": left["where"] | right["where"],
            "having": left["having"] | right["having"],
            "group_by": left["group_by"] | right["group_by"],
            "join": left["join"] | right["join"],
            "tables": left["tables"] | right["tables"],
        }

    # --------------------------------------------------
    # Resolve SELECT
    # --------------------------------------------------
    def resolve_select(
        self,
        node,
        resolved_ctes,
        collect_global_usage=True,
        current_cte_name=None,
    ):
        raw_sources = self.get_sources(node)
        scope = {}

        for alias, source in raw_sources.items():
            alias_key = self.norm(alias)

            if isinstance(source, exp.Expression):
                sub = self.resolve_query_source(
                    source,
                    resolved_ctes,
                    collect_global_usage,
                    current_cte_name=current_cte_name,
                )
                scope[alias_key] = ScopeSource(
                    "derived",
                    columns=sub["columns"],
                    star_sources=sub["star_sources"],
                )
                continue

            source_key = self.norm(source)

            # IMPORTANT:
            # A CTE name shadows any real table/view of the same name inside
            # this statement. A self-reference inside the current CTE body is
            # recursive CTE usage, not a physical table read.
            if source_key == current_cte_name:
                scope[alias_key] = ScopeSource("recursive_cte", name=source_key)

            elif source_key in resolved_ctes:
                cte = resolved_ctes[source_key]
                scope[alias_key] = ScopeSource(
                    "cte",
                    name=source_key,
                    columns=cte["columns"],
                    star_sources=cte["star_sources"],
                )

            elif source_key in self.ctes:
                # Reference to a CTE declared in the WITH clause that has not
                # yet been resolved. In valid T-SQL, forward references are not
                # generally allowed; preserve as symbolic CTE rather than
                # misclassifying it as a physical table.
                scope[alias_key] = ScopeSource("cte", name=source_key)

            else:
                # Physical table. If it was referenced without a schema prefix,
                # qualify it with the current view's schema so the source column
                # is not left schema-less.
                table_name = source_key
                if (
                    table_name
                    and "." not in table_name
                    and self.target_schema
                ):
                    table_name = f"{self.target_schema}.{table_name}"
                scope[alias_key] = ScopeSource("table", name=table_name)

        if self.debug:
            print("\nSCOPE:")
            for alias, src in scope.items():
                if src.kind in {"table", "cte", "recursive_cte"}:
                    print(f"  {alias} -> {src.kind}:{src.name}")
                else:
                    print(f"  {alias} -> {src.kind}:{list(src.columns)}")

        columns = {}
        column_meta = {}
        star_sources = set()

        # -------- SELECT projections --------
        for proj in node.expressions:
            # SELECT *
            if isinstance(proj, exp.Star):
                expanded, ss = self.expand_star(scope)
                for col_name, paths in expanded.items():
                    columns[col_name] = paths
                    column_meta[col_name] = {"status": "star", "ambiguous": False}
                star_sources |= ss
                continue

            # SELECT table.*
            if isinstance(proj, exp.Column) and proj.is_star:
                expanded, ss = self.expand_star(scope, table_alias=proj.table)
                for col_name, paths in expanded.items():
                    columns[col_name] = paths
                    column_meta[col_name] = {"status": "star", "ambiguous": False}
                star_sources |= ss
                continue

            output_name, expr = self.projection_output_name_and_expr(proj)
            if not output_name:
                continue

            paths, ambiguous, had_column = self.resolve_expr(expr, scope)
            columns[output_name] = paths
            column_meta[output_name] = {
                "status": self.column_status(expr, had_column),
                "ambiguous": ambiguous,
            }

        # -------- WHERE / HAVING / GROUP BY / JOIN --------
        where_result = self.resolve_clause(node.args.get("where"), scope)
        having_result = self.resolve_clause(node.args.get("having"), scope)

        group_by_result = set()
        group = node.args.get("group")
        if group:
            for group_expr in group.expressions:
                paths, _, _ = self.resolve_expr(group_expr, scope)
                group_by_result |= paths

        join_result = set()
        for join in node.args.get("joins") or []:
            on_expr = join.args.get("on")
            if on_expr:
                paths, _, _ = self.resolve_expr(on_expr, scope)
                join_result |= paths

        tables = self.collect_tables(scope, columns, where_result, join_result)

        if collect_global_usage:
            self.usage["where"] |= where_result
            self.usage["join"] |= join_result
            self.usage["having"] |= having_result
            self.usage["group_by"] |= group_by_result
            self.usage["tables"] |= tables

        return {
            "columns": columns,
            "column_meta": column_meta,
            "star_sources": star_sources,
            "where": where_result,
            "having": having_result,
            "group_by": group_by_result,
            "join": join_result,
            "tables": tables,
        }

    def resolve_clause(self, clause, scope):
        if not clause:
            return set()

        paths, _, _ = self.resolve_expr(clause, scope)
        return paths

    # --------------------------------------------------
    # Collect base tables touched
    # --------------------------------------------------
    def collect_tables(self, scope, columns, where_result, join_result):
        tables = set()

        for src in scope.values():
            if src.kind == "table":
                tables.add(src.name)
            tables |= src.star_sources

        path_sets = list(columns.values()) + [where_result, join_result]
        for paths in path_sets:
            for path in paths:
                for hop in path:
                    if hop.kind == "table":
                        tables.add(hop.node)

        return tables

    # --------------------------------------------------
    # Resolve CTEs (in definition order)
    # --------------------------------------------------
    def resolve_ctes(self):
        resolved = {}

        for name, query in self.ctes.items():
            cte_name = self.norm(name)
            result = self.resolve_query_source(
                query,
                resolved,
                collect_global_usage=True,
                current_cte_name=cte_name,
            )
            resolved[cte_name] = {
                "columns": result["columns"],
                "star_sources": result["star_sources"],
            }

            if self.debug:
                print(f"\nRESOLVED CTE: {cte_name}")
                for col, paths in result["columns"].items():
                    print(f"  {col} -> {len(paths)} path(s)")

        return resolved

    # --------------------------------------------------
    # Rendering helpers (paths -> JSON-friendly structures)
    # --------------------------------------------------
    def hop_str(self, hop):
        return f"{hop.node}.{hop.column}"

    def render_path(self, path):
        return [self.hop_str(hop) for hop in path]

    def render_paths(self, paths):
        rendered = [self.render_path(p) for p in paths]
        rendered.sort(key=lambda chain: " -> ".join(chain))
        return rendered

    def base_sources(self, paths):
        sources = set()
        for path in paths:
            if not path:
                continue
            last = path[-1]
            if last.kind == "table":
                sources.add(f"{last.node}.{last.column}")
            elif last.kind == "unknown":
                sources.add(f"{last.node}.{last.column} (unresolved)")
        return sorted(sources)

    # --------------------------------------------------
    # Run -> JSON-serializable lineage
    # --------------------------------------------------
    def run(self):
        self.extract_ctes()
        resolved_ctes = self.resolve_ctes()

        final = self.resolve_query_source(
            self.tree,
            resolved_ctes,
            collect_global_usage=True,
            current_cte_name=None,
        )

        view_node = self.short_name(self.target)

        columns_out = []
        for col, paths in final["columns"].items():
            meta = final["column_meta"].get(
                col,
                {"status": "computed", "ambiguous": False},
            )

            # Prepend the view output hop so each path starts at the view column.
            if view_node and meta["status"] != "star" and paths:
                paths = {(Hop(view_node, col, "output"),) + p for p in paths}

            columns_out.append(
                {
                    "name": "*" if "*" in col else col,
                    "status": meta["status"],
                    "ambiguous": meta["ambiguous"],
                    "sources": self.base_sources(paths),
                    "paths": self.render_paths(paths),
                }
            )

        return {
            "target": self.target,
            "columns": columns_out,
            "usage": {
                "where": self.base_sources(self.usage["where"]),
                "join": self.base_sources(self.usage["join"]),
                "having": self.base_sources(self.usage["having"]),
                "group_by": self.base_sources(self.usage["group_by"]),
                "tables": sorted(self.usage["tables"]),
            },
        }

    def to_json(self, indent=2):
        return json.dumps(self.run(), indent=indent, ensure_ascii=False)


# --------------------------------------------------
# CLI
# --------------------------------------------------
def _strip_comments(sql):
    import re

    token_re = re.compile(
        r"(--[^\n]*"
        r"|/\*[\s\S]*?\*/"
        r"|'(?:[^'\\]|\\.)*'"
        r'|"(?:[^"\\]|\\.)*")',
        re.DOTALL,
    )

    def repl(m):
        s = m.group(0)
        if s.startswith("--"):
            return ""
        if s.startswith("/*"):
            return " "
        return s

    return token_re.sub(repl, sql).strip()


def _load_sql(args):
    if args.sql:
        return args.sql

    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            return fh.read()

    if args.schema and args.view:
        from sql_service import ViewService

        svc = ViewService()
        return svc.get_definition(args.schema, args.view, strip=args.strip)

    return None


def _run_demo():
        demo_sql = """
        WITH Nums(Number) AS (
            SELECT 0 AS Number
            UNION ALL
            SELECT Number + 1
            FROM Nums
            WHERE Number < 59
        )
        SELECT Number
        FROM Nums
        """
        lineage = Lineage(demo_sql, debug=False)
        print(lineage.to_json())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Column-level T-SQL lineage analyzer.")
    parser.add_argument("--sql", help="Inline T-SQL to analyze.")
    parser.add_argument("--file", help="Path to a .sql file to analyze.")
    parser.add_argument("--schema", help="Schema name (used with --view to fetch from DB).")
    parser.add_argument("--view", help="View name (used with --schema to fetch from DB).")
    parser.add_argument("--strip", action="store_true", help="Strip SQL comments first.")
    parser.add_argument("--dialect", default="tsql", help="sqlglot dialect (default: tsql).")
    parser.add_argument("--debug", action="store_true", help="Print scope/CTE debug info.")
    args = parser.parse_args(argv)

    sql = _load_sql(args)

    if sql is None:
        _run_demo()
        return

    if args.strip and not (args.schema and args.view):
        sql = _strip_comments(sql)

    lineage = Lineage(sql, dialect=args.dialect, debug=args.debug)
    print(lineage.to_json())


# --------------------------------------------------
# Demo
# --------------------------------------------------
def _run_demo():
    demo_queries = [
        # 1. CREATE VIEW + derived table + CASE + ISNULL + unqualified column
        """CREATE VIEW [DSA].[VW_HR_Grouping_Anaplan] AS\nSELECT\n'PK#Y' AS [PK_HR_Grouping]\n,'Anaplan HR GroupingCode'AS [HR_Grouping_Code]\n,'Anaplan HR GroupingDesc'AS [HR_Grouping_Desc]\n,'Anaplan HR SubGroupingCode'AS [HR_SubGrouping_Code]\n,'Anaplan HR SubGroupingDesc'AS [HR_SubGrouping_Desc]\n,'Y' AS [HR_Grouping_Is_Seasonal]\nUNION\nSELECT\n'PK#N' AS [PK_HR_Grouping]\n,'Anaplan HR GroupingCode'AS [HR_Grouping_Code]\n,'Anaplan HR GroupingDesc'AS [HR_Grouping_Desc]\n,'Anaplan HR SubGroupingCode'AS [HR_SubGrouping_Code]\n,'Anaplan HR SubGroupingDesc'AS [HR_SubGrouping_Desc]\n,'N' AS [HR_Grouping_Is_Seasonal]"""

    ]

    for i, sql in enumerate(demo_queries, start=1):
        print(f"\n===== Demo query {i} =====")
        print(Lineage(sql, dialect="tsql").to_json())


if __name__ == "__main__":
    main()
