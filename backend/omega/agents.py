"""Agents + robust JSON/code-block parsing with fallback chain."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .models import AgentResult, FileArtifact
from .providers import ModelProvider, ProviderError, RateLimitError


# ---------------- Parsing helpers ----------------
def extract_json(content: str) -> Optional[dict]:
    """Fallback chain: direct -> fenced -> brace-balanced -> field-key patterns."""
    if not content:
        return None
    # 1. direct
    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    # 2. markdown fenced
    for pat in (r"```json\s*(\{.*?\})\s*```", r"```\s*(\{.*?\})\s*```"):
        m = re.search(pat, content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                continue
    # 3. brace-balanced outermost object
    start = content.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(content)):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    chunk = content[start:i + 1]
                    try:
                        return json.loads(chunk)
                    except Exception:
                        break
    # 4. field-key salvage
    for key in ("project_name", "tech_stack", "file_structure", "tasks"):
        if key in content:
            idx = content.find("{", content.find(key) - 200 if content.find(key) > 200 else 0)
            if idx != -1:
                try:
                    return json.loads(content[idx:])
                except Exception:
                    pass
    return None


def is_schema_echo(obj: dict) -> bool:
    if not isinstance(obj, dict):
        return False
    if "$defs" in obj or "definitions" in obj:
        return True
    if "properties" in obj and "tasks" not in obj:
        return True
    return False


def extract_code_blocks(content: str) -> List[FileArtifact]:
    """Parse ```lang:path\n...``` or ```path\n...``` fenced blocks."""
    artifacts: List[FileArtifact] = []
    pattern = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
    for header, body in pattern.findall(content or ""):
        header = header.strip()
        lang, path = "", ""
        if ":" in header:
            lang, path = header.split(":", 1)
        elif "/" in header or "." in header:
            path = header
        else:
            lang = header
        path = path.strip()
        if not path:
            continue
        artifacts.append(FileArtifact(path=path, content=body, language=lang.strip()))
    return artifacts


# ---------------- Agents ----------------
class BaseAgent:
    def __init__(self, role: str, system_prompt: str, providers: List[ModelProvider],
                 temperature: float = 0.3, registry=None, on_log=None):
        self.role = role
        self.system_prompt = system_prompt
        self.providers = providers
        self.temperature = temperature
        self.registry = registry
        self.on_log = on_log

    def _log(self, level: str, msg: str, **kw):
        if self.on_log:
            self.on_log(level, msg, **kw)

    def run(self, prompt: str, context: Optional[dict] = None, timeout: int = 300) -> AgentResult:
        last_err = None
        for provider in self.providers:
            try:
                raw = provider.complete(
                    system=self.system_prompt, prompt=prompt, temperature=self.temperature,
                    timeout=timeout, role=self.role, context=context or {},
                )
                if self.registry:
                    self.registry.record_result(self.role, True)
                return AgentResult(role=self.role, ok=True, raw=raw, provider=provider.name)
            except RateLimitError as e:
                last_err = str(e)
                self._log("WARNING", f"{provider.name} rate-limited; trying next candidate", details=str(e))
                continue
            except (ProviderError, Exception) as e:
                last_err = str(e)
                self._log("WARNING", f"{provider.name} failed; trying next candidate", details=str(e))
                continue
        if self.registry:
            self.registry.record_result(self.role, False)
        return AgentResult(role=self.role, ok=False, error=last_err or "all providers failed")


class ArchitectAgent(BaseAgent):
    def architecture(self, prd: str) -> Tuple[Optional[dict], AgentResult]:
        res = self.run(f"PRD:\n{prd}\n\nProduce the architecture JSON.", context={"prd": prd})
        if not res.ok:
            return None, res
        obj = extract_json(res.raw)
        res.parsed = obj
        return obj, res


class PlannerAgent(BaseAgent):
    def plan(self, architecture: dict, prd: str) -> Tuple[Optional[dict], AgentResult]:
        res = self.run(
            f"Architecture JSON:\n{json.dumps(architecture)}\n\nProduce the KanbanBacklog JSON.",
            context={"architecture": architecture, "prd": prd},
        )
        if not res.ok:
            return None, res
        obj = extract_json(res.raw)
        if obj and is_schema_echo(obj):
            self._log("WARNING", "Planner echoed a schema; retrying with concrete example injection")
            res2 = self.run(
                "The previous output was a JSON schema. Return a CONCRETE instance with a non-empty "
                f"tasks array for this architecture:\n{json.dumps(architecture)}",
                context={"architecture": architecture, "prd": prd, "force_example": True},
            )
            obj = extract_json(res2.raw) or obj
            res = res2
        res.parsed = obj
        return obj, res


class CoderAgent(BaseAgent):
    def generate(self, task: dict, architecture: dict, context_extra: str = "") -> Tuple[List[FileArtifact], AgentResult]:
        res = self.run(
            f"Task:\n{json.dumps(task)}\n\n{context_extra}\nReturn the code as fenced blocks.",
            context={"task": task, "architecture": architecture},
        )
        if not res.ok:
            return [], res
        return extract_code_blocks(res.raw), res


class ReviewerAgent(BaseAgent):
    def review(self, task: dict, files: Dict[str, str]) -> Tuple[Optional[dict], AgentResult]:
        joined = "\n\n".join(f"### {p}\n{c}" for p, c in files.items())
        res = self.run(
            f"Task:\n{json.dumps(task)}\n\nFiles:\n{joined}\n\nReturn the review JSON.",
            context={"task": task, "files": files},
        )
        if not res.ok:
            return None, res
        res.parsed = extract_json(res.raw)
        return res.parsed, res


class FixerAgent(BaseAgent):
    def fix(self, task: dict, files: Dict[str, str], issues: List[dict],
            errors: str = "") -> Tuple[List[FileArtifact], AgentResult]:
        joined = "\n\n".join(f"### {p}\n{c}" for p, c in files.items())
        res = self.run(
            f"Task:\n{json.dumps(task)}\n\nCurrent files:\n{joined}\n\n"
            f"Reviewer issues:\n{json.dumps(issues)}\n\nBuild errors:\n{errors}\n\n"
            "Return the corrected code as fenced blocks.",
            context={"task": task, "architecture": {}, "files": files, "issues": issues, "errors": errors},
        )
        if not res.ok:
            return [], res
        return extract_code_blocks(res.raw), res


class AgentFactory:
    """Dynamically instantiates agents; always ensures architect + coder baseline."""

    ROLE_CLASS = {
        "architect": ArchitectAgent,
        "planner": PlannerAgent,
        "coder": CoderAgent,
        "tester": CoderAgent,
        "debugger": CoderAgent,
        "reviewer": ReviewerAgent,
        "fixer": FixerAgent,
    }

    def __init__(self, registry, prompt_registry, router, model_registry, on_log=None):
        self.registry = registry
        self.prompts = prompt_registry
        self.router = router
        self.models = model_registry
        self.on_log = on_log
        self._cache: Dict[str, BaseAgent] = {}

    def get(self, role: str) -> BaseAgent:
        if role in self._cache:
            return self._cache[role]
        cls = self.ROLE_CLASS.get(role, CoderAgent)
        capability = next((c for c, r in _ROLE_CAP.items() if r == role), "coding")
        entry = self.router.route(capability)
        providers = self.models.candidates(entry)
        system = self.prompts.get(role) or self.prompts.get("coder") or "You are a helpful agent."
        agent = cls(role, system, providers, temperature=entry.get("temperature", 0.3),
                    registry=self.prompts, on_log=self.on_log)
        self._cache[role] = agent
        return agent

    def ensure_baseline(self) -> None:
        self.get("architect")
        self.get("coder")


_ROLE_CAP = {
    "architecture": "architect",
    "coding": "coder",
    "testing": "tester",
    "debugging": "debugger",
    "review": "reviewer",
}
