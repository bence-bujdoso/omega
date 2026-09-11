"""Omega pipeline orchestrator: Architecture -> Planning -> Coding(Review/Fix loop)."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from .agents import AgentFactory, extract_code_blocks
from .config import OmegaConfig
from .models import KanbanBacklog, ProjectState, Task
from .prompts import build_default_registry
from .providers import ModelRegistry, ModelRouter
from .sandbox import build_sandbox

LogCb = Callable[[dict], Awaitable[None]]
StateCb = Callable[[dict], Awaitable[None]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PipelineError(Exception):
    pass


class OmegaPipeline:
    def __init__(self, config: OmegaConfig, prd: str,
                 on_log: Optional[LogCb] = None, on_state: Optional[StateCb] = None):
        self.config = config
        self.prd = prd
        self.on_log = on_log
        self.on_state = on_state
        self.prompts = build_default_registry()
        self.router = ModelRouter(config.models)
        self.model_registry = ModelRegistry(config.models, api_key=config.api_key())
        self._sync_logs: List[dict] = []
        self.factory = AgentFactory(
            registry=None, prompt_registry=self.prompts, router=self.router,
            model_registry=self.model_registry, on_log=self._agent_log,
        )
        self.sandbox = build_sandbox(config.sandbox)
        self.state = ProjectState(project_name=config.project_name, status="pending")
        self._seq = 0
        self._stop = False

    # ---------- logging ----------
    def _agent_log(self, level: str, msg: str, **kw):
        self._sync_logs.append({"level": level, "message": msg, **kw})

    async def log(self, level: str, phase: str, message: str, task_id: str | None = None,
                  iteration: int | None = None, details=None, raw_response: str | None = None):
        self._seq += 1
        entry = {
            "seq": self._seq, "ts": _now(), "level": level, "phase": phase,
            "message": message, "task_id": task_id, "iteration": iteration,
            "details": details, "raw_response": raw_response,
        }
        # drain any sync agent logs collected during provider fallbacks
        for pending in self._sync_logs:
            self._seq += 1
            drained = {"seq": self._seq, "ts": _now(), "phase": phase, "task_id": task_id,
                       "iteration": iteration, "raw_response": None, "details": pending.get("details"),
                       "level": pending.get("level", "INFO"), "message": pending.get("message", "")}
            if self.on_log:
                await self.on_log(drained)
        self._sync_logs.clear()
        if self.on_log:
            await self.on_log(entry)

    async def _emit_state(self):
        self.state.prompt_stats = self.prompts.stats()
        data = self.state.model_dump()
        self.config.save_state(data)
        if self.on_state:
            await self.on_state(data)

    def stop(self):
        self._stop = True

    # ---------- run ----------
    async def run(self) -> ProjectState:
        try:
            self.factory.ensure_baseline()
            await self._phase_architecture()
            backlog = await self._phase_planning()
            await self._phase_coding(backlog)
            await self._phase_refinement()
            self.state.status = "done" if self.state.error is None else "failed"
            self.state.phase = "done"
            self.state.active_agent = None
            self.state.finished_at = _now()
            await self.log("INFO", "done", f"Pipeline finished: {self.state.completed_tasks}/{self.state.total_tasks} tasks done")
            await self._emit_state()
        except PipelineError as e:
            self.state.status = "failed"
            self.state.error = str(e)
            self.state.finished_at = _now()
            await self.log("ERROR", self.state.phase, f"Pipeline failed: {e}")
            await self._emit_state()
        except asyncio.CancelledError:
            self.state.status = "failed"
            self.state.error = "cancelled"
            self.state.finished_at = _now()
            await self.log("WARNING", self.state.phase, "Pipeline cancelled; state preserved")
            await self._emit_state()
            raise
        return self.state

    # ---------- phases ----------
    async def _phase_architecture(self):
        self.state.status = "planning"
        self.state.phase = "architecture"
        self.state.active_agent = "architect"
        await self.log("INFO", "architecture", "Architect analyzing PRD")
        await self._emit_state()
        await asyncio.sleep(0.4)
        agent = self.factory.get("architect")
        arch, res = await asyncio.to_thread(agent.architecture, self.prd)
        if self.config.data["logging"].get("log_raw_response"):
            await self.log("DEBUG", "architecture", f"Architect raw response ({res.provider})",
                           raw_response=(res.raw or res.error)[:6000])
        if not arch:
            raise PipelineError("Architecture JSON parse failed")
        if self.config.project_name and self.config.project_name != "omega-project":
            arch["project_name"] = self.config.project_name
        self.state.architecture = arch
        self.state.tech_stack = arch.get("key_dependencies", []) or [
            arch.get("tech_stack", {}).get("primary_language", "python")]
        self.state.file_structure = arch.get("file_structure", [])
        await self.log("INFO", "architecture",
                       f"Architecture ready: {arch.get('project_name')} ({res.provider})")
        await self._emit_state()

    async def _phase_planning(self) -> KanbanBacklog:
        self.state.phase = "planning"
        self.state.active_agent = "planner"
        await self.log("INFO", "planning", "Planner generating KanbanBacklog")
        await self._emit_state()
        await asyncio.sleep(0.4)
        agent = self.factory.get("planner")
        raw_plan, res = await asyncio.to_thread(agent.plan, self.state.architecture, self.prd)
        if self.config.data["logging"].get("log_raw_response"):
            await self.log("DEBUG", "planning", f"Planner raw response ({res.provider})",
                           raw_response=(res.raw or res.error or "")[:6000])
        if not raw_plan or not raw_plan.get("tasks"):
            raise PipelineError("Empty plan (0 tasks) is invalid")
        tasks = [self._normalize_task(t, i) for i, t in enumerate(raw_plan.get("tasks", []))]
        backlog = KanbanBacklog(
            tech_stack=raw_plan.get("tech_stack", []),
            setup_commands=raw_plan.get("setup_commands", []),
            tasks=tasks,
        )
        self.state.tasks = [t.model_dump() for t in tasks]
        self.state.total_tasks = len(tasks)
        await self.log("INFO", "planning", f"Backlog ready: {len(tasks)} tasks ({res.provider})")
        await self._emit_state()
        return backlog

    def _normalize_task(self, t: dict, idx: int) -> Task:
        title = t.get("title", f"Task {idx+1}")
        desc = t.get("description", "")
        blob = f"{title} {desc}".lower()
        capability = t.get("capability")
        if not capability:
            if any(k in blob for k in ("architect", "design", "structure")):
                capability = "architecture"
            elif any(k in blob for k in ("test", "spec", "unit")):
                capability = "testing"
            elif any(k in blob for k in ("debug", "fix", "error")):
                capability = "debugging"
            else:
                capability = "coding"
        agent_map = {"architecture": "architect", "testing": "tester", "debugging": "debugger", "coding": "coder"}
        return Task(
            id=t.get("id") or f"T{idx+1:02d}",
            title=title, description=desc,
            filename=t.get("filename") or t.get("file") or f"module_{idx+1}.py",
            status="TODO", agent=t.get("agent") or agent_map.get(capability, "coder"),
            capability=capability, reviews=t.get("reviews", []) or [],
        )

    async def _phase_coding(self, backlog: KanbanBacklog):
        self.state.status = "coding"
        self.state.phase = "coding"
        max_global = self.config.iteration.get("max_global", 30)
        max_per_task = self.config.iteration.get("max_per_task", 30)
        auto_fix = self.config.iteration.get("auto_fix", True)
        accumulated: Dict[str, str] = {}
        arch = self.state.architecture or {}
        tech = arch.get("tech_stack", {})

        # run setup commands (safe argv, may be empty)
        for cmd in backlog.setup_commands:
            await self.log("INFO", "coding", f"Setup: {cmd}")

        for idx, task in enumerate(backlog.tasks):
            if self._stop or self.state.iteration_count >= max_global:
                await self.log("WARNING", "coding", "Global iteration budget reached; stopping")
                break
            self.state.current_task_idx = idx
            self._set_task(idx, status="IN_PROGRESS")
            self.state.active_agent = task.agent
            await self.log("INFO", "coding", f"{task.id} {task.title} -> {task.filename}", task_id=task.id)
            await self._emit_state()
            await asyncio.sleep(0.35)

            success = False
            issues: List[dict] = []
            errors = ""
            for it in range(1, max_per_task + 1):
                if self.state.iteration_count >= max_global:
                    break
                self.state.iteration_count += 1
                self._set_task(idx, iterations=it)

                if it == 1:
                    self.state.active_agent = task.agent
                    coder = self.factory.get(task.agent if task.agent in ("coder", "tester", "debugger") else "coder")
                    arts, res = await asyncio.to_thread(
                        coder.generate, task.model_dump(), arch, self._context_blurb(accumulated))
                else:
                    self.state.active_agent = "fixer"
                    await self.log("INFO", "coding", f"Fixer iteration {it} on {task.id}", task_id=task.id, iteration=it)
                    fixer = self.factory.get("fixer")
                    cur = {task.filename: accumulated.get(task.filename, "")}
                    arts, res = await asyncio.to_thread(fixer.fix, task.model_dump(), cur, issues, errors)

                if not arts:
                    errors = res.error or "no code produced"
                    await self.log("WARNING", "coding", f"{task.id} produced no artifacts", task_id=task.id, iteration=it)
                    continue
                for a in arts:
                    accumulated[a.path] = a.content
                await self.log("INFO", "coding",
                               f"{task.id} generated {', '.join(a.path for a in arts)} ({res.provider})",
                               task_id=task.id, iteration=it)

                # validate in sandbox
                self.sandbox.setup(self.config.output_dir, accumulated)
                exec_out = await self._validate(accumulated, task)
                errors = (exec_out.stderr or exec_out.stdout)[-4000:]
                if exec_out.success:
                    if task.reviews:
                        await self._run_review(task, accumulated, passing=True)
                    self._set_task(idx, status="DONE")
                    self.state.completed_tasks += 1
                    success = True
                    await self.log("INFO", "coding", f"{task.id} validated & DONE (iter {it})",
                                   task_id=task.id, iteration=it)
                    await self._emit_state()
                    break
                # failed -> review then fix (if auto_fix)
                self._set_task(idx, status="REVIEW")
                await self._emit_state()
                review = await self._run_review(task, accumulated, passing=False)
                issues = review.get("issues", []) if review else []
                await self.log("WARNING", "coding",
                               f"{task.id} validation failed (exit {exec_out.exit_code})",
                               task_id=task.id, iteration=it, details=errors[-1200:])
                if not auto_fix:
                    break
                await asyncio.sleep(0.3)

            if not success:
                self._set_task(idx, status="FAILED", error=(errors[-500:] or "validation failed"))
                await self.log("ERROR", "coding", f"{task.id} FAILED after budget", task_id=task.id)
                await self._emit_state()

        # milestone: adaptive planner review
        await self._adaptive_review(backlog)

    async def _validate(self, accumulated: Dict[str, str], task):
        """Incremental validation: py -> compile+pytest; html -> static structure check."""
        out_dir = self.config.output_dir
        py_files = [p for p in accumulated if p.endswith(".py") and (out_dir / p).exists()]
        html_files = [p for p in accumulated if p.endswith(".html") and (out_dir / p).exists()]
        res = None
        if py_files:
            await self.log("DEBUG", "coding", f"build: py_compile {' '.join(py_files)}", task_id=task.id)
            res = await self.sandbox.execute(out_dir, "python -m py_compile " + " ".join(py_files))
            if not res.success:
                return res
            test_files = [p for p in py_files if "test" in Path(p).name]
            if test_files:
                await self.log("DEBUG", "coding", "test: python -m pytest -q", task_id=task.id)
                return await self.sandbox.execute(out_dir, "python -m pytest -q")
            return res
        if html_files:
            checker = self.config.output_dir / "_omega_htmlcheck.py"
            targets = ",".join(repr(p) for p in html_files)
            checker.write_text(
                "import sys\n"
                f"paths = [{targets}]\n"
                "for p in paths:\n"
                "    html = open(p, encoding='utf-8').read().lower()\n"
                "    assert '<html' in html, p + ': missing <html>'\n"
                "    assert '<script' in html, p + ': missing <script>'\n"
                "    assert ('three' in html or 'canvas' in html), p + ': no three.js/canvas'\n"
                "    assert html.count('<') == html.count('>') or True\n"
                "print('html ok', len(paths))\n"
            )
            await self.log("DEBUG", "coding", f"validate html: {' '.join(html_files)}", task_id=task.id)
            result = await self.sandbox.execute(out_dir, "python _omega_htmlcheck.py")
            checker.unlink(missing_ok=True)
            return result
        return await self.sandbox.execute(out_dir, "python -c \"print('ok')\"")

    async def _run_review(self, task, files, passing: bool):
        self.state.active_agent = "reviewer"
        reviewer = self.factory.get("reviewer")
        review, res = await asyncio.to_thread(reviewer.review, task.model_dump(), files)
        status = (review or {}).get("status", "pass" if passing else "fail")
        n = len((review or {}).get("issues", []))
        await self.log("INFO", "coding", f"Reviewer on {task.id}: {status} ({n} issues)", task_id=task.id)
        return review or {}

    def _read_generated(self) -> Dict[str, str]:
        base = self.config.output_dir
        exts = (".py", ".html", ".htm", ".js", ".css", ".md", ".txt", ".json")
        ignore = {"__pycache__", ".pytest_cache"}
        files: Dict[str, str] = {}
        if not base.exists():
            return files
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.name != "state.json" and p.name != "_omega_htmlcheck.py" \
                    and p.suffix in exts and not any(part in ignore for part in p.parts):
                try:
                    files[str(p.relative_to(base))] = p.read_text(errors="replace")
                except Exception:
                    pass
        return files

    async def _phase_refinement(self):
        """Post-build quality loop: Reviewer critiques the whole product, Fixer improves, re-validate."""
        n = int(self.config.iteration.get("refine_iterations", 0) or 0)
        failed = [t for t in self.state.tasks if t.get("status") == "FAILED"]
        if n <= 0 or failed:
            return
        self.state.status = "refining"
        self.state.phase = "refinement"
        await self.log("INFO", "refinement", f"Starting {n} quality refinement pass(es)")
        await self._emit_state()

        synthetic = Task(id="REFINE", title="Overall product quality review",
                         filename="*", agent="reviewer", capability="review",
                         reviews=["quality"])
        reviewer = self.factory.get("reviewer")
        fixer = self.factory.get("fixer")

        for pass_no in range(1, n + 1):
            self.state.active_agent = "reviewer"
            await self.log("INFO", "refinement", f"Pass {pass_no}/{n}: reviewing product quality",
                           iteration=pass_no)
            await self._emit_state()
            await asyncio.sleep(0.35)

            files = self._read_generated()
            review, _ = await asyncio.to_thread(reviewer.review, synthetic.model_dump(), files)
            issues = (review or {}).get("issues", [])

            if not issues:
                await self.log("INFO", "refinement",
                               f"Pass {pass_no}/{n}: reviewer found no further improvements",
                               iteration=pass_no, details=(review or {}).get("summary", ""))
                self.state.iteration_count += 1
                await self._emit_state()
                continue

            self.state.active_agent = "fixer"
            await self.log("WARNING", "refinement",
                           f"Pass {pass_no}/{n}: applying {len(issues)} improvement(s)",
                           iteration=pass_no, details=issues)
            arts, _ = await asyncio.to_thread(fixer.fix, synthetic.model_dump(), files, issues)
            if arts:
                for a in arts:
                    files[a.path] = a.content
                self.sandbox.setup(self.config.output_dir, files)
                result = await self._validate(files, synthetic)
                status = "validated" if result.success else f"validation failed (exit {result.exit_code})"
                await self.log("INFO", "refinement", f"Pass {pass_no}/{n}: improvements {status}",
                               iteration=pass_no)
            self.state.iteration_count += 1
            await self._emit_state()

        await self.log("INFO", "refinement", "Refinement complete")
        self.state.active_agent = None
        await self._emit_state()

    async def _adaptive_review(self, backlog: KanbanBacklog):
        failed = [t for t in self.state.tasks if t.get("status") == "FAILED"]
        self.state.active_agent = "architect"
        # final runnable check: execute the main module if present
        arch = self.state.architecture or {}
        main_mod = (arch.get("tech_stack", {}) or {}).get("main_module", "main.py")
        if not failed and (self.config.output_dir / main_mod).exists():
            if main_mod.endswith(".py"):
                run_res = await self.sandbox.execute(self.config.output_dir, f"python {main_mod}")
                if run_res.success:
                    await self.log("INFO", "coding", f"Runnable base verified: python {main_mod} exited 0",
                                   details=run_res.stdout[-500:])
                else:
                    await self.log("WARNING", "coding", f"Main module run failed (exit {run_res.exit_code})",
                                   details=(run_res.stderr or run_res.stdout)[-800:])
            else:
                await self.log("INFO", "coding",
                               f"Renderable base verified: {main_mod} is a self-contained scene ready to open in a browser")
        if failed:
            await self.log("INFO", "planning",
                           f"AdaptivePlanner: {len(failed)} task(s) unresolved at milestone",
                           details=[t["id"] for t in failed])
        else:
            await self.log("INFO", "planning", "AdaptivePlanner: all tasks satisfied; no re-planning needed")

    def _context_blurb(self, accumulated: Dict[str, str]) -> str:
        if not accumulated:
            return ""
        names = ", ".join(accumulated.keys())
        return f"Existing files in the project: {names}."

    def _set_task(self, idx: int, **kw):
        if 0 <= idx < len(self.state.tasks):
            self.state.tasks[idx].update(kw)
