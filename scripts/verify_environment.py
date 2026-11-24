from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    required: bool = True


def _command_version(command: str, *args: str) -> str:
    executable = shutil.which(command)
    if executable is None:
        return "not found"
    completed = subprocess.run(
        [executable, *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return output[0] if output else f"exit code {completed.returncode}"


def collect_checks() -> list[CheckResult]:
    checks = [
        CheckResult(
            "Python 3.12+",
            sys.version_info >= (3, 12),
            sys.version.split()[0],
        ),
        CheckResult("SQLite (Python)", True, sqlite3.sqlite_version),
        CheckResult("Git", shutil.which("git") is not None, _command_version("git", "--version")),
        CheckResult(
            "SQLite CLI",
            shutil.which("sqlite3") is not None,
            _command_version("sqlite3", "--version"),
        ),
        CheckResult(
            "uv (recommended)",
            shutil.which("uv") is not None,
            _command_version("uv", "--version"),
            required=False,
        ),
        CheckResult("specs directory", (PROJECT_ROOT / "specs").is_dir(), str(PROJECT_ROOT / "specs")),
        CheckResult("source directory", (PROJECT_ROOT / "src").is_dir(), str(PROJECT_ROOT / "src")),
        CheckResult("Git repository", (PROJECT_ROOT / ".git").exists(), str(PROJECT_ROOT / ".git")),
    ]
    return checks


def main() -> int:
    results = collect_checks()
    print("Smart Daily System environment verification")
    print(f"Project root: {PROJECT_ROOT}")
    print()
    for result in results:
        marker = "PASS" if result.passed else ("WARN" if not result.required else "FAIL")
        print(f"[{marker}] {result.name}: {result.detail}")

    failed = [result for result in results if result.required and not result.passed]
    print()
    if failed:
        print(f"Required checks failed: {len(failed)}")
        return 1
    print("All required checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
