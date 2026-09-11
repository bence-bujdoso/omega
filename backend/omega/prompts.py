"""Versioned prompt registry with auto-disable of underperforming prompts."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PromptVersion:
    def __init__(self, body: str, version: str):
        self.body = body
        self.version = version
        self.runs = 0
        self.successes = 0
        self.disabled = False
        self.created_at = _now()
        self.updated_at = _now()

    @property
    def success_rate(self) -> float:
        return (self.successes / self.runs) if self.runs else 1.0

    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "runs": self.runs,
            "successes": self.successes,
            "disabled": self.disabled,
            "success_rate": round(self.success_rate, 3),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PromptRegistry:
    """Tracks prompt versions and auto-disables weak ones (<40% over >=5 runs)."""

    MIN_RUNS = 5
    MIN_RATE = 0.40

    def __init__(self):
        self._store: Dict[str, List[PromptVersion]] = {}

    def register(self, name: str, body: str, version: str = "v1", force: bool = False) -> None:
        versions = self._store.setdefault(name, [])
        existing = next((v for v in versions if v.version == version), None)
        if existing:
            if force:
                existing.body = body
                existing.disabled = False
                existing.runs = 0
                existing.successes = 0
                existing.updated_at = _now()
            return
        versions.append(PromptVersion(body, version))

    def get(self, name: str) -> Optional[str]:
        versions = self._store.get(name, [])
        active = [v for v in versions if not v.disabled]
        if active:
            best = max(active, key=lambda v: (v.success_rate, v.runs))
            return best.body
        return versions[-1].body if versions else None

    def record_result(self, name: str, success: bool, version: Optional[str] = None) -> None:
        versions = self._store.get(name, [])
        if not versions:
            return
        target = None
        if version:
            target = next((v for v in versions if v.version == version), None)
        if target is None:
            target = next((v for v in versions if not v.disabled), versions[-1])
        target.runs += 1
        if success:
            target.successes += 1
        target.updated_at = _now()
        if target.runs >= self.MIN_RUNS and target.success_rate < self.MIN_RATE:
            target.disabled = True

    def stats(self) -> Dict[str, List[Dict]]:
        return {name: [v.to_dict() for v in vs] for name, vs in self._store.items()}


# ---- Seed prompts ----
def build_default_registry() -> PromptRegistry:
    reg = PromptRegistry()
    reg.register(
        "architect",
        "You are the Architect. Analyze the PRD and output ONLY a single JSON object "
        "describing the architecture with keys: project_name, description, tech_stack "
        "(primary_language, framework, database, dependencies[], build_command, test_command, "
        "main_module), file_structure[{path,purpose,type}], modules[{name,description,file}], "
        "key_dependencies[], architecture_notes. Output a concrete instance, never a JSON schema.",
    )
    reg.register(
        "planner",
        "You are the Planner. Convert the architecture JSON into a KanbanBacklog JSON with keys: "
        "tech_stack[], setup_commands[], tasks[] and acceptance_report{}. Produce 3-7 small "
        "file-level tasks that yield a RUNNABLE base. Each task: id (T01..), title, description, "
        "filename, status='TODO', agent, capability, reviews[]. Output a concrete instance with a "
        "non-empty tasks array, never a JSON schema with $defs or properties.",
    )
    reg.register(
        "coder",
        "You are the Coder. Produce complete, runnable code for the given task. Output ONLY fenced "
        "code blocks in the form ```lang:relative/path.py\\n<code>\\n```. Never emit placeholders or "
        "TODOs. Include tests and dependency files when the task requires them.",
    )
    reg.register(
        "reviewer",
        "You are the Reviewer. Review the code for correctness and best practices. Output ONLY a JSON "
        "object with keys issues[] (type, description, severity, line_number), status ('pass'|'fail'), "
        "and summary. Be constructive and specific.",
    )
    reg.register(
        "fixer",
        "You are the Fixer. Given the code and reviewer issues, return corrected code as fenced code "
        "blocks ```lang:relative/path.py\\n<code>\\n```. Fix every listed issue and keep the project runnable.",
    )
    return reg
