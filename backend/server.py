import asyncio
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from omega.config import DEFAULT_CONFIG, OmegaConfig
from omega.health import health as omega_health
from omega.pipeline import OmegaPipeline

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

RUNS_DIR = Path("/app/data/omega_runs")
RUNS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Omega Framework API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("omega.server")

# in-memory registry of active pipelines
ACTIVE: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------- Models ----------------
class StartRunRequest(BaseModel):
    prd: str
    project_name: Optional[str] = None
    sandbox_type: str = "process"
    max_per_task: int = 30
    max_global: int = 30
    refine_iterations: int = 2


class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


# ---------------- Health / config ----------------
@api_router.get("/")
async def root():
    return {"message": "Omega Framework API", "version": "1.0.0"}


@api_router.get("/omega/health")
async def health_endpoint():
    return omega_health()


@api_router.get("/omega/config")
async def get_config():
    return DEFAULT_CONFIG


# ---------------- Runs ----------------
def _run_output_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id / "generated"


@api_router.post("/omega/runs")
async def start_run(req: StartRunRequest):
    if not req.prd.strip():
        raise HTTPException(status_code=400, detail="PRD is empty")
    run_id = str(uuid.uuid4())
    project_name = req.project_name or "omega-project"
    output_dir = _run_output_dir(run_id)

    cfg = OmegaConfig(output_dir=str(output_dir))
    cfg.project_name = project_name
    cfg.data["sandbox"]["type"] = req.sandbox_type
    cfg.data["iteration"]["max_per_task"] = req.max_per_task
    cfg.data["iteration"]["max_global"] = req.max_global
    cfg.data["iteration"]["refine_iterations"] = req.refine_iterations

    run_doc = {
        "id": run_id,
        "project_name": project_name,
        "prd": req.prd,
        "status": "pending",
        "phase": "init",
        "active_agent": None,
        "architecture": None,
        "tasks": [],
        "completed_tasks": 0,
        "total_tasks": 0,
        "iteration_count": 0,
        "error": None,
        "config": cfg.data,
        "started_at": _now(),
        "finished_at": None,
    }
    await db.omega_runs.insert_one({**run_doc})

    async def on_log(entry: dict):
        await db.omega_logs.insert_one({"run_id": run_id, **entry})

    async def on_state(state: dict):
        update = {k: state[k] for k in (
            "status", "phase", "active_agent", "architecture", "tasks",
            "completed_tasks", "total_tasks", "iteration_count", "prompt_stats", "error", "finished_at",
        ) if k in state}
        await db.omega_runs.update_one({"id": run_id}, {"$set": update})

    pipe = OmegaPipeline(cfg, req.prd, on_log=on_log, on_state=on_state)

    async def runner():
        try:
            await pipe.run()
        except asyncio.CancelledError:
            await db.omega_runs.update_one({"id": run_id}, {"$set": {"status": "failed", "error": "cancelled", "finished_at": _now()}})
        except Exception as e:  # noqa
            logger.exception("pipeline crashed")
            await db.omega_runs.update_one({"id": run_id}, {"$set": {"status": "failed", "error": str(e), "finished_at": _now()}})
        finally:
            ACTIVE.pop(run_id, None)

    task = asyncio.create_task(runner())
    ACTIVE[run_id] = {"pipeline": pipe, "task": task}
    return {"id": run_id, "status": "pending"}


@api_router.get("/omega/runs")
async def list_runs():
    runs = await db.omega_runs.find(
        {}, {"_id": 0, "prd": 0, "config": 0, "architecture": 0}
    ).sort("started_at", -1).to_list(200)
    return runs


@api_router.get("/omega/runs/{run_id}")
async def get_run(run_id: str):
    run = await db.omega_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@api_router.get("/omega/runs/{run_id}/logs")
async def get_logs(run_id: str, after: int = 0):
    logs = await db.omega_logs.find(
        {"run_id": run_id, "seq": {"$gt": after}}, {"_id": 0}
    ).sort("seq", 1).to_list(1000)
    return logs


@api_router.post("/omega/runs/{run_id}/stop")
async def stop_run(run_id: str):
    entry = ACTIVE.get(run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="run not active")
    entry["pipeline"].stop()
    return {"id": run_id, "stopping": True}


@api_router.get("/omega/runs/{run_id}/files")
async def get_files(run_id: str):
    base = _run_output_dir(run_id)
    if not base.exists():
        return {"files": []}
    files = []
    ignore = {"__pycache__", ".pytest_cache", ".git"}
    for p in sorted(base.rglob("*")):
        if p.is_file() and not any(part in ignore for part in p.parts):
            rel = str(p.relative_to(base))
            files.append({"path": rel, "size": p.stat().st_size})
    return {"files": files}


@api_router.get("/omega/runs/{run_id}/file")
async def get_file(run_id: str, path: str):
    base = _run_output_dir(run_id).resolve()
    target = (base / path).resolve()
    if base != target and base not in target.parents:
        raise HTTPException(status_code=400, detail="invalid path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return {"path": path, "content": target.read_text(errors="replace")}


@api_router.get("/omega/runs/{run_id}/raw")
async def get_raw_file(run_id: str, path: str):
    base = _run_output_dir(run_id).resolve()
    target = (base / path).resolve()
    if base != target and base not in target.parents:
        raise HTTPException(status_code=400, detail="invalid path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    content = target.read_text(errors="replace")
    if path.endswith((".html", ".htm")):
        return HTMLResponse(content=content)
    return PlainTextResponse(content=content)


@api_router.delete("/omega/runs/{run_id}")
async def delete_run(run_id: str):
    await db.omega_runs.delete_one({"id": run_id})
    await db.omega_logs.delete_many({"run_id": run_id})
    run_path = RUNS_DIR / run_id
    if run_path.exists():
        shutil.rmtree(run_path, ignore_errors=True)
    return {"deleted": run_id}


# ---------------- legacy status ----------------
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.model_dump())
    doc = status_obj.model_dump()
    doc["timestamp"] = doc["timestamp"].isoformat()
    await db.status_checks.insert_one(doc)
    return status_obj


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def reconcile_orphaned_runs():
    """Mark runs left mid-flight by a restart as failed (they cannot resume)."""
    res = await db.omega_runs.update_many(
        {"status": {"$in": ["pending", "planning", "coding"]}},
        {"$set": {"status": "failed", "error": "orphaned by server restart", "finished_at": _now()}},
    )
    if res.modified_count:
        logger.info("reconciled %s orphaned run(s)", res.modified_count)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
