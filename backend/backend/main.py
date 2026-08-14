from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import json
import shutil
import xml.etree.ElementTree as ET

from .downstream_lineage import get_lineage
from .sql_generate_schema import generate_schema
from .table_lineage import compute_table_lineage
from .view_lineage import compute_view_lineage
from .xml_to_nested_json import build_structure

app = FastAPI(title="Data Lineage Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECTS_DIR = Path(__file__).resolve().parent.parent / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/projects")
def list_projects():
    return sorted(p.name for p in PROJECTS_DIR.iterdir() if p.is_dir())


@app.post("/projects")
async def create_project(name: str = Form(...), xml_file: UploadFile = File(...)):
    project_dir = PROJECTS_DIR / name
    project_dir.mkdir(parents=True, exist_ok=True)

    xml_path = project_dir / xml_file.filename
    with xml_path.open("wb") as f:
        shutil.copyfileobj(xml_file.file, f)

    response = {"project": name, "xml_file": xml_file.filename}

    # Step 1: turn the TimeXtender XML export into the nested JSON
    # (project -> data warehouses -> tables/views -> fields, plus semantic
    # models) that the left panel and whiteboard are built from.
    try:
        tree = ET.parse(xml_path)
        structure = build_structure(tree.getroot())
    except ET.ParseError as exc:
        response["warning"] = f"Could not parse XML file: {exc}"
    else:
        # Step 2: build the qualify_schema once, then run column-level
        # lineage on every view's SQL definition (Step 2a) and every
        # table's inserts/related records/transformations/lookups/hash
        # fields (Step 2b). Both mutate `structure` in place.
        schema = generate_schema(structure)
        response["view_lineage"] = compute_view_lineage(structure, schema)
        response["table_lineage"] = compute_table_lineage(structure, schema)

        json_path = project_dir / "project.json"
        json_path.write_text(json.dumps(structure, indent=2), encoding="utf-8")
        response["json_file"] = json_path.name

    return response


@app.get("/projects/{project_name}/data")
async def get_project_data(project_name: str):
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists():
        return JSONResponse(status_code=404, content={"error": "Project not found"})

    json_path = project_dir / "project.json"
    if not json_path.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "No analysis data for this project yet"},
        )

    return json.loads(json_path.read_text(encoding="utf-8"))


@app.get("/projects/{project_name}/lineage/{table_id}")
async def get_table_lineage(project_name: str, table_id: str, direction: str = "downstream", column: str | None = None):
    if direction not in ("downstream", "upstream"):
        return JSONResponse(status_code=400, content={"error": "direction must be 'downstream' or 'upstream'"})

    json_path = PROJECTS_DIR / project_name / "project.json"
    if not json_path.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "No analysis data for this project yet"},
        )

    structure = json.loads(json_path.read_text(encoding="utf-8"))
    return get_lineage(structure, table_id, direction, column)


def run():
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
