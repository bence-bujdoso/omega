# Omega Framework — PRD → Product Pipeline

## Original Problem Statement
Build the Omega Framework: a multi-agent AI pipeline that transforms a markdown PRD into a
runnable software project. Architect agent → JSON architecture spec; Planner agent →
KanbanBacklog of 3–7 coding tasks; each task runs Coder → Reviewer → Fixer with sandbox
build/test validation until pass or iteration budget exhausted. Includes prompt versioning with
auto-disable, capability-based model routing, adaptive planning, secure sandbox execution,
state persistence, health check, CLI (`omega`) and a real-time monitoring dashboard.

## User Choices
- Web app version of Omega + CLI wrapper (both).
- LLM provider: local **9router proxy** (OpenAI-compatible, `http://localhost:20128/v1`, model `9router-combo`).
- Full pipeline incl. sandbox execution; real code generation to disk AND visualized pipeline in UI.
- No authentication (open developer tool).

## Architecture
- **omega core package** `/app/backend/omega/`: config (omega.yaml + .env + state.json),
  models (Pydantic), prompts (versioned registry + auto-disable), providers (OpenAICompat / Ollama /
  offline Heuristic), router (capability→model), agents (Architect/Planner/Coder/Reviewer/Fixer +
  factory + JSON/code-block fallback parsing), sandbox (ProcessSandbox, no-shell argv, safe_join),
  pipeline (async orchestrator), health, cli.
- **Backend** FastAPI `/app/backend/server.py`: `/api/omega/*` endpoints; runs pipeline as background
  asyncio task; persists to Mongo (`omega_runs`, `omega_logs`); generated projects written to
  `/app/data/omega_runs/<id>/generated` (outside `/app/backend` so hot-reload never touches them).
- **Frontend** React dashboard `/app/frontend/src/components/omega/`: PRD input, live pipeline header
  + phase stepper, agent activity bar, Kanban board, architecture viewer, live log stream, generated
  file explorer, config panel, runs history. Polls every 1.3s. Dark IDE aesthetic.
- **LLM**: default 9router (unreachable in-container) → automatic deterministic **offline heuristic
  engine** fallback that still generates a real runnable Python project (compiles + pytest passes).

## Implemented (2026-06-11)
- Full 5-phase pipeline: Architecture → Planning → Coding (Coder→Reviewer→Fixer loop) → Done, with
  incremental sandbox validation (py_compile + pytest) and final runnable-base check.
- Prompt versioning with auto-disable (<40% success over ≥5 runs); JSON fallback chain +
  schema-echo detection; capability→agent→model routing; provider fallback chain.
- Secure sandbox (fixed argv, no shell; path-traversal guard); state.json persistence; graceful stop.
- CLI: `python -m omega.cli {init,start,status,dashboard,health}`.
- Web dashboard with all views + runs history + toasts.
- Endpoints: start/list/get/logs/files/file/stop/delete/health/config.
- Startup reconciliation marks orphaned runs failed; delete removes on-disk artifacts.
- Verified: backend 11/11 pytest pass; sample Task Tracker PRD completes 5/5 tasks in ~6s,
  generated `main.py` runs and pytest passes.

## Core Requirements (static)
Multi-agent orchestration, iterative fix loop, sandbox validation, adaptive planning, prompt
versioning, model routing, real-time dashboard, CLI, state persistence, security (no shell / no
traversal), health check.

## Backlog / Remaining
- P1: Wire a live 9router/Ollama endpoint for PRD-specific code generation (offline engine is the
  in-container fallback). Run provider HTTP calls via executor already done.
- P2: Docker sandbox real isolation (currently falls back to process). Adaptive planner adding new
  tasks at milestones. Prompt-stats surfacing in UI. Mongo indexes on logs/runs.
- P2: Support non-Python target stacks; multi-agent parallel execution.

## Next Tasks
- Connect a reachable LLM endpoint and validate PRD-specific generation.
- Optional: Docker sandbox, adaptive re-planning that injects debug tasks, prompt analytics panel.
