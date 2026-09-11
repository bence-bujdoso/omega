"""Configuration + state persistence for Omega."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG: Dict[str, Any] = {
    "dashboard": {"host": "0.0.0.0", "port": 8090, "title": "Omega Pipeline Dashboard"},
    "iteration": {"auto_fix": True, "max_global": 30, "max_per_task": 30, "require_tests": False, "refine_iterations": 2, "num_tasks": 5},
    "logging": {"file": "omega.log", "level": "DEBUG", "log_raw_response": True},
    "models": {
        "default": {
            "api_key_env": "OPENROUTER_API_KEY",
            "base_url": "http://localhost:20128/v1",
            "model": "9router-combo",
            "provider": "openai",
            "temperature": 0.3,
            "max_tokens": 8192,
        },
        "roles": {
            "architect": {"model": "9router-combo", "temperature": 0.3},
            "planner": {"model": "9router-combo", "temperature": 0.2},
            "coder": {"model": "9router-combo", "temperature": 0.2},
            "reviewer": {"model": "9router-combo", "temperature": 0.2},
            "fixer": {"model": "9router-combo", "temperature": 0.2},
            "tester": {"model": "9router-combo", "temperature": 0.2},
            "debugger": {"model": "9router-combo", "temperature": 0.2},
        },
    },
    "project": {"name": "omega-project", "output_dir": "./generated"},
    "sandbox": {"type": "process", "timeout": 120},
    "agent": {"num_tasks": 5},
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class OmegaConfig:
    def __init__(self, data: Optional[Dict[str, Any]] = None, output_dir: Optional[str] = None):
        load_dotenv()
        self.data = _deep_merge(DEFAULT_CONFIG, data or {})
        if output_dir:
            self.data["project"]["output_dir"] = output_dir

    # ---- accessors ----
    @property
    def project_name(self) -> str:
        return self.data["project"]["name"]

    @project_name.setter
    def project_name(self, value: str) -> None:
        self.data["project"]["name"] = value

    @property
    def output_dir(self) -> Path:
        return Path(self.data["project"]["output_dir"]).resolve()

    @property
    def iteration(self) -> Dict[str, Any]:
        return self.data["iteration"]

    @property
    def sandbox(self) -> Dict[str, Any]:
        return self.data["sandbox"]

    @property
    def models(self) -> Dict[str, Any]:
        return self.data["models"]

    @property
    def dashboard(self) -> Dict[str, Any]:
        return self.data["dashboard"]

    def api_key(self) -> str:
        env_name = self.data["models"]["default"].get("api_key_env", "OPENROUTER_API_KEY")
        return os.environ.get(env_name, "") or os.environ.get("OPENAI_API_KEY", "")

    # ---- yaml ----
    @classmethod
    def load(cls, path: str | Path) -> "OmegaConfig":
        path = Path(path)
        data = yaml.safe_load(path.read_text()) if path.exists() else {}
        return cls(data)

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.data, sort_keys=False)

    def save_yaml(self, path: str | Path) -> None:
        Path(path).write_text(self.to_yaml())

    # ---- state ----
    def state_path(self) -> Path:
        return self.output_dir / "state.json"

    def save_state(self, state: Dict[str, Any]) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_path().write_text(json.dumps(state, indent=2, default=str))

    def load_state(self) -> Optional[Dict[str, Any]]:
        p = self.state_path()
        if p.exists():
            return json.loads(p.read_text())
        return None
