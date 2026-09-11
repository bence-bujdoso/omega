"""Pydantic data models for the Omega Framework."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------- Architecture phase ----------------
class TechStack(BaseModel):
    primary_language: str = "python"
    framework: str = "stdlib"
    database: str = "none"
    dependencies: List[str] = Field(default_factory=list)
    build_command: str = ""
    test_command: str = ""
    main_module: str = "main.py"


class FileSpec(BaseModel):
    path: str
    purpose: str = ""
    type: str = "code"


class ModuleSpec(BaseModel):
    name: str
    description: str = ""
    file: str = ""


class Architecture(BaseModel):
    project_name: str
    description: str = ""
    tech_stack: TechStack = Field(default_factory=TechStack)
    file_structure: List[FileSpec] = Field(default_factory=list)
    modules: List[ModuleSpec] = Field(default_factory=list)
    key_dependencies: List[str] = Field(default_factory=list)
    architecture_notes: str = ""


# ---------------- Planning phase ----------------
class Task(BaseModel):
    id: str
    title: str
    description: str = ""
    filename: str
    status: str = "TODO"  # TODO | IN_PROGRESS | REVIEW | DONE | FAILED | BLOCKED
    agent: str = "coder"
    capability: str = "coding"
    reviews: List[str] = Field(default_factory=list)
    iterations: int = 0
    error: Optional[str] = None


class KanbanBacklog(BaseModel):
    tech_stack: List[str] = Field(default_factory=list)
    setup_commands: List[str] = Field(default_factory=list)
    tasks: List[Task] = Field(default_factory=list)
    acceptance_report: Dict[str, Any] = Field(default_factory=dict)


# ---------------- Execution ----------------
class ExecutionResult(BaseModel):
    success: bool
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    command: str = ""


class ReviewIssue(BaseModel):
    type: str = "issue"
    description: str = ""
    severity: str = "medium"
    line_number: Optional[int] = None


class ValidationResult(BaseModel):
    status: str = "pass"  # pass | fail
    issues: List[ReviewIssue] = Field(default_factory=list)
    summary: str = ""


class AgentResult(BaseModel):
    role: str
    ok: bool = True
    raw: str = ""
    parsed: Optional[Dict[str, Any]] = None
    provider: str = ""
    error: Optional[str] = None


class FileArtifact(BaseModel):
    path: str
    content: str
    language: str = ""


# ---------------- State ----------------
class ProjectState(BaseModel):
    project_name: str = "omega-project"
    status: str = "pending"  # pending | planning | coding | done | failed
    phase: str = "init"
    active_agent: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    file_structure: List[Dict[str, Any]] = Field(default_factory=list)
    architecture: Optional[Dict[str, Any]] = None
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    current_task_idx: int = 0
    completed_tasks: int = 0
    total_tasks: int = 0
    iteration_count: int = 0
    started_at: str = Field(default_factory=_now_iso)
    finished_at: Optional[str] = None
    error: Optional[str] = None
