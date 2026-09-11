"""Health check for the Omega Framework."""
from __future__ import annotations

import importlib
import shutil
from typing import Any, Dict

from .config import OmegaConfig


def health(config: OmegaConfig | None = None) -> Dict[str, Any]:
    config = config or OmegaConfig()
    issues = []
    deps = {}
    for mod in ("pydantic", "yaml", "requests", "pytest"):
        try:
            importlib.import_module(mod)
            deps[mod] = True
        except Exception:
            deps[mod] = False
            issues.append(f"missing dependency: {mod}")

    py = shutil.which("python") or shutil.which("python3")
    if not py:
        issues.append("python interpreter not found")

    api_key_present = bool(config.api_key())
    default = config.models["default"]

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "dependencies": deps,
        "python": py,
        "llm": {
            "provider": default.get("provider"),
            "base_url": default.get("base_url"),
            "model": default.get("model"),
            "api_key_present": api_key_present,
            "offline_fallback": True,
        },
        "sandbox": config.sandbox.get("type"),
        "output_dir": str(config.output_dir),
    }
