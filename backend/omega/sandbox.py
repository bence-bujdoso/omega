"""Secure sandbox execution: writes files + runs commands as fixed argv (no shell)."""
from __future__ import annotations

import asyncio
import os
import shlex
import sys
import time
from pathlib import Path
from typing import Dict, List

from .models import ExecutionResult


def safe_join(base: Path, rel: str) -> Path:
    """Join preventing path traversal / absolute escapes."""
    rel = rel.strip().lstrip("/")
    if ".." in Path(rel).parts:
        raise ValueError(f"Unsafe path component in {rel!r}")
    target = (base / rel).resolve()
    base = base.resolve()
    if base != target and base not in target.parents:
        raise ValueError(f"Path escapes sandbox: {rel!r}")
    return target


def parse_commands(raw: str) -> List[str]:
    """Split a compound command string on ; && || and newlines (no shell)."""
    parts: List[str] = []
    for chunk in raw.replace("&&", "\n").replace("||", "\n").replace(";", "\n").splitlines():
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts


class BaseSandbox:
    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    def setup(self, output_dir: Path, files: Dict[str, str]) -> List[str]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        written = []
        for rel, content in files.items():
            target = safe_join(output_dir, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            written.append(str(target.relative_to(output_dir)))
        return written


class ProcessSandbox(BaseSandbox):
    """Runs commands locally as fixed argv (never shell=True)."""

    async def execute(self, output_dir: Path, command: str, timeout: int | None = None) -> ExecutionResult:
        output_dir = Path(output_dir)
        timeout = timeout or self.timeout
        start = time.time()
        combined_out, combined_err, last_code = [], [], 0
        env = dict(os.environ)
        for single in parse_commands(command):
            argv = self._resolve(single)
            if not argv:
                continue
            try:
                proc = await asyncio.create_subprocess_exec(
                    *argv, cwd=str(output_dir), env=env,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                last_code = proc.returncode or 0
                combined_out.append(out.decode("utf-8", "replace"))
                combined_err.append(err.decode("utf-8", "replace"))
                if last_code != 0:
                    break
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                combined_err.append(f"Command timed out after {timeout}s: {single}")
                last_code = 124
                break
            except FileNotFoundError as e:
                combined_err.append(f"Command not found: {single} ({e})")
                last_code = 127
                break
        return ExecutionResult(
            success=last_code == 0, exit_code=last_code,
            stdout="\n".join(combined_out), stderr="\n".join(combined_err),
            duration=round(time.time() - start, 3), command=command,
        )

    @staticmethod
    def _resolve(single: str) -> List[str]:
        argv = shlex.split(single)
        if not argv:
            return argv
        # normalize interpreter references to the running python
        if argv[0] in ("python", "python3", "py"):
            argv[0] = sys.executable
        if argv[0] == "pip" or (len(argv) > 2 and argv[:2] == ["python", "-m"] and False):
            argv = [sys.executable, "-m", "pip"] + argv[1:]
        return argv


class DockerSandbox(ProcessSandbox):
    """Placeholder: falls back to process execution when Docker is unavailable."""
    name = "docker"


def build_sandbox(sandbox_cfg: dict) -> BaseSandbox:
    timeout = int(sandbox_cfg.get("timeout", 120))
    if sandbox_cfg.get("type") == "docker":
        return DockerSandbox(timeout=timeout)
    return ProcessSandbox(timeout=timeout)
