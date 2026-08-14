# Data Lineage App

A browser-based data lineage solution with a React frontend and Python backend.

## Goals

- Upload a TimeXtender XML file from the browser
- Create a project folder, store the XML, convert it into a nested JSON
  (project → data warehouses → tables/views → fields, plus semantic models),
  and run column-level lineage on every view's SQL definition and every
  table's inserts/related records/transformations/lookups/hash fields
- On demand (not part of project creation), find every field downstream of
  a given field, for a "click a field, toggle on what it feeds into" UI
  interaction

## Structure

- `backend/` — FastAPI server
  - `backend/backend/xml_to_nested_json.py` — parses the TimeXtender XML
    export into the nested JSON structure; runs automatically on project
    creation
  - `backend/backend/sql_generate_schema.py` — builds the
    `{schema: {table: {column: type}}}` schema sqlglot needs to qualify
    columns, read directly off the nested JSON (tables carry their own
    `SchemaName`)
  - `backend/backend/sql_col_lineage.py` — the column-level T-SQL lineage
    analyzer (format-agnostic)
  - `backend/backend/view_lineage.py` — runs `sql_col_lineage.Lineage` over
    every view's SQL script, using the generated schema; runs automatically
    on project creation, right after the XML → JSON step
  - `backend/backend/table_lineage.py` — lineage for tables (not views):
    table inserts, related records, transformations, conditional lookup
    fields, custom hash fields, known TX system fields. Runs automatically
    on project creation, right after view lineage.
  - `backend/backend/downstream_lineage.py` — given a field, finds every
    field downstream of it (whose lineage traces back to include it),
    walking `ColumnLineage` edges built by the two steps above. Not wired
    to an API endpoint yet - call it directly, on demand, when a field is
    clicked; it's intentionally not run at project-creation time.
- `frontend/` — React SPA

## Getting started (after cloning)

Prerequisites: [Git](https://git-scm.com/), [Node.js](https://nodejs.org/) 18+
(with npm), and Python 3.10+.

```powershell
git clone https://github.com/mlesne1/DataLineageApp.git
cd DataLineageApp

# Backend: install the package + its dependencies (fastapi, uvicorn, sqlglot,
# networkx, pyvis, openpyxl, python-docx). A virtual environment is optional
# but recommended.
cd backend
python -m pip install -e .
cd ..

# Frontend: install node_modules (not committed to the repo)
cd frontend
npm install
```

No `.env` file or API keys are required — the backend has no external
service dependencies.

## Running locally

Run both servers together from `frontend/`:

```powershell
cd frontend
npm start
```

This starts the React dev server and the FastAPI backend side by side
(labeled `[WEB]`/`[API]`), reusing the `python` on your PATH — make sure
that's the environment where you ran `pip install -e .`. The app opens at
http://localhost:3000 and calls the API at http://127.0.0.1:8000. To run the
backend on its own:

```powershell
cd backend
python -m uvicorn backend.main:app --reload
```

`sample_timextender_project.xml` (repo root) can be uploaded as a first
project once the app is running, to confirm everything works end to end.

Project data created through the app (`backend/projects/`) and build output
(`frontend/node_modules/`, `frontend/build/`) are gitignored — they're
generated locally and never need to be committed.

## Notes

- `POST /projects` accepts a project name + XML upload, saves the XML, then:
  1. runs `xml_to_nested_json.build_structure()` on it
  2. builds the qualify_schema once (`sql_generate_schema.generate_schema()`)
  3. runs `view_lineage.compute_view_lineage()`, attaching `LineageStatus` /
     `ColumnLineage` / `ColumnsRequired` / `TablesUsed` / `ColumnDuplicates`
     onto each view that has a SQL script
  4. runs `table_lineage.compute_table_lineage()`, attaching `ColumnLineage`
     / `TablesUsed` / `ColumnsRequired` (and `LineageErrors` if a table
     insert script fails to analyze) onto each table
  5. writes the combined result to `project.json` in that project's folder

  If the XML fails to parse, the project is still created and the response
  includes a `warning` instead of `json_file`/`view_lineage`/`table_lineage`.
  A view with no SQL script is skipped (not counted as failed); a view or
  table-insert script that fails to analyze is recorded as a failure without
  aborting the rest of the run.
- A few raw-field-name mappings are best-effort, not confirmed against a
  real TimeXtender export - each is called out with a `NOTE:` comment where
  it's used:
  - the view's SQL text: read from `ViewDefinitions.Script`, falling back to
    `Definition`/`SqlScript`
  - a table insert's SQL text: read from each `TableInsertScripts` entry's
    `Script`, falling back to `Text`/`SqlScript`
  - a conditional lookup field's source value: read from the raw
    `LookupFields` record's `SourceTableField`, falling back to
    `Source Table Field`/`SourceField`
  If a real export uses a different tag for any of these, that path
  silently finds nothing rather than erroring - worth checking first if
  lineage looks incomplete for a real project.
- `table_lineage.py`'s "custom fields" handling was folded into
  transformation lineage rather than kept as its own category: a custom
  field that's just a passthrough/aggregation of another field reads the
  same as a transformation with a simple expression, so it's expected to
  already be covered there.
