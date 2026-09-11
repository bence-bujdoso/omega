"""LLM providers + offline heuristic engine + model routing."""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import requests


class ProviderError(Exception):
    pass


class RateLimitError(ProviderError):
    pass


class ModelProvider(ABC):
    name = "base"

    @abstractmethod
    def complete(self, system: str, prompt: str, temperature: float = 0.3,
                 schema: Optional[dict] = None, timeout: int = 300,
                 example: Optional[str] = None, role: str = "coder",
                 context: Optional[dict] = None) -> str:
        ...


class OpenAICompatProvider(ModelProvider):
    """OpenAI-compatible chat completions (OpenRouter / 9router proxy / Gemini compat)."""

    name = "openai-compat"

    def __init__(self, base_url: str, api_key: str, model: str, max_tokens: int = 8192):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, system, prompt, temperature=0.3, schema=None, timeout=300,
                 example=None, role="coder", context=None) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=min(timeout, 120))
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"{self.name} connection failed: {e}") from e
        if resp.status_code in (429, 402):
            raise RateLimitError(f"{self.name} rate/quota: {resp.status_code}")
        if resp.status_code >= 400:
            raise ProviderError(f"{self.name} http {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class OllamaProvider(OpenAICompatProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434/v1", model: str = "llama3", max_tokens: int = 8192):
        super().__init__(base_url, api_key="ollama", model=model, max_tokens=max_tokens)


# ---------------- Offline heuristic engine ----------------
class HeuristicProvider(ModelProvider):
    """Deterministic offline generator so the pipeline runs without a live LLM.

    Produces valid, runnable Python project artifacts shaped for each agent role.
    """

    name = "heuristic-offline"

    def complete(self, system, prompt, temperature=0.3, schema=None, timeout=300,
                 example=None, role="coder", context=None) -> str:
        context = context or {}
        if role == "architect":
            return json.dumps(self._architecture(context), indent=2)
        if role == "planner":
            return json.dumps(self._backlog(context), indent=2)
        if role in ("coder", "fixer", "tester", "debugger"):
            return self._code(context)
        if role == "reviewer":
            return json.dumps(self._review(context), indent=2)
        return "{}"

    # -- helpers --
    @staticmethod
    def _project_name(prd: str) -> str:
        for line in (prd or "").splitlines():
            m = re.match(r"^#\s+(.*)", line.strip())
            if m:
                slug = re.sub(r"[^a-z0-9]+", "-", m.group(1).lower()).strip("-")
                return (slug or "omega-project")[:48]
        return "omega-project"

    @staticmethod
    def _description(prd: str) -> str:
        for line in (prd or "").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and not s.startswith("---"):
                return s[:240]
        return "A generated software project."

    @staticmethod
    def _is_web(prd: str) -> bool:
        blob = (prd or "").lower()
        keywords = ("three.js", "threejs", "webgl", "html", "canvas", "scene",
                    "shader", "3d", "browser", "css", "javascript", "landing page")
        return any(k in blob for k in keywords)

    def _stack(self, ctx: dict) -> str:
        arch = ctx.get("architecture") or {}
        lang = (arch.get("tech_stack") or {}).get("primary_language")
        if lang:
            return "web" if lang.lower() in ("javascript", "typescript", "html") else "python"
        return "web" if self._is_web(ctx.get("prd", "")) else "python"

    def _architecture(self, ctx: dict) -> dict:
        if self._stack(ctx) == "web":
            return self._architecture_web(ctx)
        return self._architecture_python(ctx)

    @staticmethod
    def _adjust_tasks(tasks: list, n: int, extra_stub) -> list:
        if not n or n <= 0:
            return tasks
        if len(tasks) > n:
            return tasks[:n]
        k = len(tasks)
        while len(tasks) < n:
            k += 1
            tasks.append(extra_stub(k))
        return tasks

    def _backlog(self, ctx: dict) -> dict:
        n = ctx.get("num_tasks")
        if self._stack(ctx) == "web":
            backlog = self._backlog_web(ctx)
            backlog["tasks"] = self._adjust_tasks(backlog["tasks"], n, self._web_extra)
        else:
            backlog = self._backlog_python(ctx)
            backlog["tasks"] = self._adjust_tasks(backlog["tasks"], n, self._python_extra)
        return backlog

    @staticmethod
    def _python_extra(k: int) -> dict:
        return {"id": f"T{k:02d}", "title": f"Add helper module {k}",
                "description": f"Create helper module module_{k}.py exposing a small utility function.",
                "filename": f"module_{k}.py", "status": "TODO", "agent": "coder",
                "capability": "coding", "reviews": []}

    @staticmethod
    def _web_extra(k: int) -> dict:
        return {"id": f"T{k:02d}", "title": f"Scene detail pass {k}",
                "description": "Refine geometry, materials and lighting in index.html.",
                "filename": "index.html", "status": "TODO", "agent": "coder",
                "capability": "coding", "reviews": []}

    def _architecture_web(self, ctx: dict) -> dict:
        prd = ctx.get("prd", "")
        name = self._project_name(prd)
        return {
            "project_name": name,
            "description": self._description(prd),
            "tech_stack": {
                "primary_language": "javascript",
                "framework": "three.js",
                "database": "none",
                "dependencies": ["three@0.160.0"],
                "build_command": "",
                "test_command": "",
                "main_module": "index.html",
            },
            "file_structure": [
                {"path": "index.html", "purpose": "Self-contained Three.js scene", "type": "code"},
                {"path": "README.md", "purpose": "How to open and use the scene", "type": "doc"},
            ],
            "modules": [
                {"name": "scene", "description": "Renderer, camera, lights, Parthenon, hill, instancing", "file": "index.html"},
                {"name": "controls", "description": "Time / haze / crowd sliders and camera modes", "file": "index.html"},
            ],
            "key_dependencies": ["three@0.160.0"],
            "architecture_notes": (
                "Single self-contained HTML file. Three.js loaded via a pinned ES module import map. "
                "Instanced columns, olive trees, city massing and people; time-of-day, haze and crowd "
                "controls plus postcard/inspect/flyover cameras. DPR clamped below 2."
            ),
        }

    def _backlog_web(self, ctx: dict) -> dict:
        return {
            "tech_stack": ["javascript", "three.js", "html"],
            "setup_commands": [],
            "tasks": [
                {"id": "T01", "title": "Build the self-contained Three.js scene", "description":
                 "Create index.html with renderer, sky, sun light, Parthenon (stylobate, instanced "
                 "columns, entablature, pediments, roof), rocky Acropolis hill and carved steps.",
                 "filename": "index.html", "status": "TODO", "agent": "coder", "capability": "coding",
                 "reviews": ["correctness"]},
                {"id": "T02", "title": "Add environment & instancing", "description":
                 "Instanced olive trees, distant city massing and robed figures for scale.",
                 "filename": "index.html", "status": "TODO", "agent": "coder", "capability": "coding", "reviews": []},
                {"id": "T03", "title": "Wire interactive controls & cameras", "description":
                 "Time-of-day, haze and crowd sliders plus postcard/inspect/flyover camera modes; clamp DPR.",
                 "filename": "index.html", "status": "TODO", "agent": "coder", "capability": "coding", "reviews": []},
                {"id": "T04", "title": "Document the scene", "description":
                 "Create README.md describing how to open index.html and use the controls.",
                 "filename": "README.md", "status": "TODO", "agent": "coder", "capability": "coding", "reviews": []},
            ],
            "acceptance_report": {},
        }

    def _architecture_python(self, ctx: dict) -> dict:
        prd = ctx.get("prd", "")
        name = self._project_name(prd)
        return {
            "project_name": name,
            "description": self._description(prd),
            "tech_stack": {
                "primary_language": "python",
                "framework": "stdlib",
                "database": "none",
                "dependencies": ["pytest"],
                "build_command": "python -m py_compile core.py main.py",
                "test_command": "python -m pytest -q",
                "main_module": "main.py",
            },
            "file_structure": [
                {"path": "core.py", "purpose": "Core domain logic", "type": "code"},
                {"path": "main.py", "purpose": "Entry point / CLI", "type": "code"},
                {"path": "test_core.py", "purpose": "Unit tests for core logic", "type": "test"},
                {"path": "requirements.txt", "purpose": "Python dependencies", "type": "config"},
                {"path": "README.md", "purpose": "Project documentation", "type": "doc"},
            ],
            "modules": [
                {"name": "core", "description": "Domain model and operations", "file": "core.py"},
                {"name": "main", "description": "Runnable entry point", "file": "main.py"},
            ],
            "key_dependencies": ["pytest"],
            "architecture_notes": (
                "Single-package Python project. core.py holds a Store domain object and helper "
                "functions; main.py wires them into a runnable demo; test_core.py validates behaviour."
            ),
        }

    def _backlog_python(self, ctx: dict) -> dict:
        return {
            "tech_stack": ["python", "pytest"],
            "setup_commands": [],
            "tasks": [
                {"id": "T01", "title": "Implement core domain logic", "description":
                 "Create core.py with add/subtract helpers and a Store class managing items.",
                 "filename": "core.py", "status": "TODO", "agent": "coder", "capability": "coding", "reviews": []},
                {"id": "T02", "title": "Build runnable entry point", "description":
                 "Create main.py that imports core and prints a working demo.",
                 "filename": "main.py", "status": "TODO", "agent": "coder", "capability": "coding", "reviews": []},
                {"id": "T03", "title": "Write unit tests for core", "description":
                 "Create test_core.py with pytest tests covering the Store and helpers.",
                 "filename": "test_core.py", "status": "TODO", "agent": "tester", "capability": "testing",
                 "reviews": ["correctness"]},
                {"id": "T04", "title": "Declare dependencies", "description":
                 "Create requirements.txt listing pytest.",
                 "filename": "requirements.txt", "status": "TODO", "agent": "coder", "capability": "coding", "reviews": []},
                {"id": "T05", "title": "Document the project", "description":
                 "Create README.md describing how to run and test.",
                 "filename": "README.md", "status": "TODO", "agent": "coder", "capability": "coding", "reviews": []},
            ],
            "acceptance_report": {},
        }

    def _code(self, ctx: dict) -> str:
        task = ctx.get("task", {}) or {}
        fn = task.get("filename", "main.py")
        name = (ctx.get("architecture", {}) or {}).get("project_name", "omega-project")
        if fn == "index.html":
            from .templates import THREEJS_SCENE
            return "```html:index.html\n" + THREEJS_SCENE.replace("__PROJECT__", name) + "```\n"
        if fn == "README.md" and self._stack(ctx) == "web":
            from .templates import WEB_README
            return "```markdown:README.md\n" + WEB_README.replace("__PROJECT__", name) + "```\n"
        blocks = {
            "core.py": (
                "python:core.py",
                '"""Core domain logic."""\n\n\n'
                "def add(a, b):\n    return a + b\n\n\n"
                "def subtract(a, b):\n    return a - b\n\n\n"
                "class Store:\n"
                '    """A tiny in-memory item store."""\n\n'
                "    def __init__(self):\n        self._items = []\n\n"
                "    def add(self, item):\n        self._items.append(item)\n        return item\n\n"
                "    def all(self):\n        return list(self._items)\n\n"
                "    def count(self):\n        return len(self._items)\n",
            ),
            "main.py": (
                "python:main.py",
                '"""Runnable entry point for %s."""\n\n'
                "from core import add, subtract, Store\n\n\n"
                "def main():\n"
                '    store = Store()\n'
                '    store.add("hello")\n'
                '    store.add("world")\n'
                '    print("Project: %s")\n'
                '    print("2 + 3 =", add(2, 3))\n'
                '    print("10 - 4 =", subtract(10, 4))\n'
                '    print("items:", store.all())\n'
                '    return 0\n\n\n'
                'if __name__ == "__main__":\n    raise SystemExit(main())\n' % (name, name),
            ),
            "test_core.py": (
                "python:test_core.py",
                "from core import add, subtract, Store\n\n\n"
                "def test_add():\n    assert add(2, 3) == 5\n\n\n"
                "def test_subtract():\n    assert subtract(10, 4) == 6\n\n\n"
                "def test_store():\n"
                "    s = Store()\n    s.add('a')\n    s.add('b')\n"
                "    assert s.count() == 2\n    assert s.all() == ['a', 'b']\n",
            ),
            "requirements.txt": ("text:requirements.txt", "pytest\n"),
            "README.md": (
                "markdown:README.md",
                "# %s\n\nGenerated by the Omega Framework pipeline.\n\n"
                "## Run\n\n```bash\npython main.py\n```\n\n"
                "## Test\n\n```bash\npython -m pytest -q\n```\n" % name,
            ),
        }
        header, content = blocks.get(fn, ("python:" + fn, "# %s\nprint('generated %s')\n" % (fn, fn)))
        return "```%s\n%s```\n" % (header, content)

    def _review(self, ctx: dict) -> dict:
        return {"issues": [], "status": "pass", "summary": "Code compiles and tests pass; no blocking issues found."}


# ---------------- Routing ----------------
TASK_CAPABILITY_AGENT = {
    "architecture": "architect",
    "coding": "coder",
    "testing": "tester",
    "debugging": "debugger",
    "review": "reviewer",
    "reasoning": "architect",
}


class ModelRouter:
    def __init__(self, models_config: Dict[str, Any]):
        self.default = models_config.get("default", {})
        self.roles = models_config.get("roles", {})

    def route(self, capability: str) -> Dict[str, Any]:
        role = TASK_CAPABILITY_AGENT.get(capability, "coder")
        entry = dict(self.default)
        entry.update(self.roles.get(role, {}))
        entry["role"] = role
        return entry


class ModelRegistry:
    """Builds provider candidate chains for an agent role (with offline fallback)."""

    def __init__(self, models_config: Dict[str, Any], api_key: str = ""):
        self.models_config = models_config
        self.api_key = api_key

    def build_provider(self, entry: Dict[str, Any]) -> ModelProvider:
        provider = (entry.get("provider") or self.models_config["default"].get("provider", "openai")).lower()
        base_url = entry.get("base_url") or self.models_config["default"].get("base_url")
        model = entry.get("model") or self.models_config["default"].get("model")
        max_tokens = entry.get("max_tokens") or self.models_config["default"].get("max_tokens", 8192)
        if provider == "ollama":
            return OllamaProvider(base_url=base_url or "http://localhost:11434/v1", model=model, max_tokens=max_tokens)
        return OpenAICompatProvider(base_url=base_url, api_key=self.api_key, model=model, max_tokens=max_tokens)

    def candidates(self, entry: Dict[str, Any]) -> List[ModelProvider]:
        chain: List[ModelProvider] = []
        try:
            chain.append(self.build_provider(entry))
        except Exception:
            pass
        chain.append(HeuristicProvider())  # always-available offline fallback
        return chain
