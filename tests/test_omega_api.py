"""Backend API tests for Omega Framework"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].splitlines()[0]
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api/omega"

SAMPLE_PRD = """# Task Tracker
Build a simple task tracker CLI.

## Features
- Add tasks with title and description
- List tasks
- Mark tasks as done
- Persist tasks to a JSON file

## Non-functional
- Written in Python 3.10+
- Include tests
"""


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Health / Config ----------
def test_health(session):
    r = session.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["llm"]["offline_fallback"] is True
    for dep in ("pydantic", "yaml", "requests", "pytest"):
        assert data["dependencies"].get(dep) is True


def test_config(session):
    r = session.get(f"{API}/config", timeout=15)
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["models"]["default"]["model"] == "9router-combo"


# ---------- Runs ----------
def test_start_empty_prd_returns_400(session):
    r = session.post(f"{API}/runs", json={"prd": "   "}, timeout=15)
    assert r.status_code == 400


@pytest.fixture(scope="module")
def run_id(session):
    r = session.post(f"{API}/runs", json={"prd": SAMPLE_PRD, "project_name": "task-tracker"}, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "id" in j
    return j["id"]


def test_run_progresses_to_done(session, run_id):
    deadline = time.time() + 60
    status = None
    last_state = None
    while time.time() < deadline:
        r = session.get(f"{API}/runs/{run_id}", timeout=15)
        assert r.status_code == 200
        last_state = r.json()
        status = last_state["status"]
        if status in ("done", "failed"):
            break
        time.sleep(1.2)
    assert status == "done", f"final state: {last_state}"
    arch = last_state.get("architecture")
    assert arch and "project_name" in arch and "tech_stack" in arch and "file_structure" in arch
    tasks = last_state.get("tasks") or []
    assert 3 <= len(tasks) <= 7
    assert last_state["completed_tasks"] == last_state["total_tasks"]


def test_logs_incremental(session, run_id):
    r = session.get(f"{API}/runs/{run_id}/logs?after=0", timeout=15)
    assert r.status_code == 200
    logs = r.json()
    assert len(logs) > 0
    for entry in logs[:3]:
        for k in ("seq", "level", "phase", "message"):
            assert k in entry
    last_seq = logs[-1]["seq"]
    r2 = session.get(f"{API}/runs/{run_id}/logs?after={last_seq}", timeout=15)
    assert r2.status_code == 200
    assert r2.json() == []


def test_files_listing_and_content(session, run_id):
    r = session.get(f"{API}/runs/{run_id}/files", timeout=15)
    assert r.status_code == 200
    files = [f["path"] for f in r.json()["files"]]
    for expected in ("core.py", "main.py", "test_core.py", "requirements.txt", "README.md", "state.json"):
        assert expected in files, f"missing {expected}, got {files}"

    r = session.get(f"{API}/runs/{run_id}/file", params={"path": "main.py"}, timeout=15)
    assert r.status_code == 200
    assert "content" in r.json() and len(r.json()["content"]) > 0


def test_file_path_traversal_rejected(session, run_id):
    r = session.get(f"{API}/runs/{run_id}/file", params={"path": "../../etc/passwd"}, timeout=15)
    assert r.status_code == 400


def test_stop_inactive_run_404(session, run_id):
    # after completion the run is no longer active
    r = session.post(f"{API}/runs/{run_id}/stop", timeout=15)
    assert r.status_code == 404


def test_list_runs_newest_first(session, run_id):
    r = session.get(f"{API}/runs", timeout=15)
    assert r.status_code == 200
    runs = r.json()
    assert len(runs) > 0
    ids = [x["id"] for x in runs]
    assert run_id in ids
    # verify sorted desc by started_at
    starts = [x["started_at"] for x in runs]
    assert starts == sorted(starts, reverse=True)


def test_generated_project_runnable(run_id):
    """Actually execute the generated main.py and pytest in the output dir."""
    import subprocess
    base = f"/app/backend/omega_runs/{run_id}/generated"
    assert os.path.isdir(base)
    r = subprocess.run(["python", "main.py"], cwd=base, capture_output=True, timeout=30)
    assert r.returncode == 0, r.stderr.decode()
    r = subprocess.run(["python", "-m", "pytest", "-q"], cwd=base, capture_output=True, timeout=60)
    assert r.returncode == 0, r.stdout.decode() + r.stderr.decode()


def test_stop_active_run(session):
    # Start a fresh run and immediately stop it
    r = session.post(f"{API}/runs", json={"prd": SAMPLE_PRD, "project_name": "to-stop"}, timeout=30)
    assert r.status_code == 200
    rid = r.json()["id"]
    time.sleep(0.3)
    r = session.post(f"{API}/runs/{rid}/stop", timeout=15)
    assert r.status_code in (200, 404)  # may have completed already (offline is fast)
