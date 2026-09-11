"""Omega CLI: init, start, status, dashboard, health."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from .config import DEFAULT_CONFIG, OmegaConfig
from .health import health as run_health
from .pipeline import OmegaPipeline

GITIGNORE = "generated/\n__pycache__/\n*.pyc\nomega.log\n.env\n"


def _print(msg: str):
    print(f"[omega] {msg}")


def cmd_init(args):
    root = Path(args.name)
    root.mkdir(parents=True, exist_ok=True)
    (root / "generated").mkdir(exist_ok=True)
    cfg = OmegaConfig()
    cfg.project_name = args.name
    cfg.save_yaml(root / "omega.yaml")
    (root / ".gitignore").write_text(GITIGNORE)
    _print(f"Initialized project at {root}/ (omega.yaml, generated/, .gitignore)")


def cmd_start(args):
    prd = sys.stdin.read() if args.prd_file in (None, "-") else Path(args.prd_file).read_text()
    if not prd.strip():
        _print("ERROR: empty PRD")
        sys.exit(1)
    cfg_path = Path("omega.yaml")
    cfg = OmegaConfig.load(cfg_path) if cfg_path.exists() else OmegaConfig()
    if args.name:
        cfg.project_name = args.name
    cfg.data["project"]["output_dir"] = args.output or "./generated"

    async def _log(e):
        lvl = e["level"]
        if lvl == "DEBUG" and cfg.data["logging"].get("level") != "DEBUG":
            return
        tid = f" {e['task_id']}" if e.get("task_id") else ""
        _print(f"{lvl:<7} {e['phase']:<12}{tid} | {e['message']}")

    async def _state(s):
        pass

    pipe = OmegaPipeline(cfg, prd, on_log=_log, on_state=_state)

    async def _run():
        return await pipe.run()

    try:
        state = asyncio.run(_run())
    except KeyboardInterrupt:
        _print("Interrupted; state preserved in state.json")
        sys.exit(130)
    _print("=" * 48)
    _print(f"status: {state.status}")
    _print(f"tasks: {state.completed_tasks}/{state.total_tasks}")
    _print(f"iterations: {state.iteration_count}")
    if state.error:
        _print(f"error: {state.error}")
    _print(f"output: {cfg.output_dir}")


def cmd_status(args):
    cfg = OmegaConfig.load("omega.yaml") if Path("omega.yaml").exists() else OmegaConfig()
    state = cfg.load_state()
    if not state:
        _print("No state.json found. Run `omega start` first.")
        return
    print(json.dumps(state, indent=2, default=str))


def cmd_dashboard(args):
    cfg = OmegaConfig.load("omega.yaml") if Path("omega.yaml").exists() else OmegaConfig()
    d = cfg.dashboard
    _print(f"Web dashboard served by the Omega backend. Local Flask target: http://{d['host']}:{d['port']}")
    _print("In this environment the dashboard runs as the React web UI (see REACT_APP_BACKEND_URL).")


def cmd_health(args):
    print(json.dumps(run_health(), indent=2))


def build_parser():
    p = argparse.ArgumentParser(prog="omega", description="Omega Framework — PRD → product pipeline")
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Scaffold a new Omega project")
    p_init.add_argument("name")
    p_init.set_defaults(func=cmd_init)

    p_start = sub.add_parser("start", help="Run the full pipeline")
    p_start.add_argument("--prd-file", default="-")
    p_start.add_argument("--name", default=None)
    p_start.add_argument("--output", default=None)
    p_start.set_defaults(func=cmd_start)

    p_status = sub.add_parser("status", help="Show pipeline state")
    p_status.set_defaults(func=cmd_status)

    p_dash = sub.add_parser("dashboard", help="Show dashboard info")
    p_dash.set_defaults(func=cmd_dashboard)

    p_health = sub.add_parser("health", help="Run health check")
    p_health.set_defaults(func=cmd_health)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
