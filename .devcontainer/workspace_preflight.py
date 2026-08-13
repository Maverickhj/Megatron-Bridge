# Copyright (c) 2026, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import argparse
import json
import logging
import platform
import re
import subprocess
from pathlib import Path
from typing import TypedDict


LOGGER = logging.getLogger(__name__)
WORKSPACE = Path("/opt/Megatron-Bridge")
WINDOWS_SOURCE_PATTERN = re.compile(r"^[A-Za-z]:\\")


class MountDetails(TypedDict):
    """Filesystem information for the workspace mount."""

    source: str | None
    filesystem_type: str | None
    options: str | None


class WorkspaceAssessment(TypedDict):
    """Versioned result of the workspace preflight."""

    schema_version: int
    profile: str
    status: str
    recommendation: str | None
    workspace: str
    kernel: str
    mount_source: str | None
    filesystem_type: str | None
    mount_options: str | None
    git_core_symlinks: bool | None
    git_core_filemode: bool | None
    git_core_autocrlf: str | None


def command_output(command: list[str]) -> str | None:
    """Return stripped command output without making preflight fail."""
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None


def git_config(key: str) -> str | None:
    """Read a repository-local or inherited Git configuration value."""
    return command_output(["git", "-C", str(WORKSPACE), "config", "--get", key])


def parse_git_bool(value: str | None) -> bool | None:
    """Parse Git's accepted boolean spellings."""
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "on", "1"}:
        return True
    if normalized in {"false", "no", "off", "0"}:
        return False
    return None


def mount_details(path: Path) -> MountDetails:
    """Read mount source, type, and options with findmnt when available."""
    output = command_output(["findmnt", "--json", "-T", str(path), "-o", "SOURCE,FSTYPE,OPTIONS"])
    if output is None:
        return {
            "source": None,
            "filesystem_type": command_output(["stat", "-f", "-c", "%T", str(path)]),
            "options": None,
        }

    try:
        filesystems = json.loads(output)["filesystems"]
        filesystem = filesystems[0]
    except (IndexError, KeyError, TypeError, json.JSONDecodeError):
        return {"source": None, "filesystem_type": None, "options": None}

    return {
        "source": filesystem.get("source"),
        "filesystem_type": filesystem.get("fstype"),
        "options": filesystem.get("options"),
    }


def classify_workspace(
    *,
    kernel: str,
    source: str | None,
    filesystem_type: str | None,
    options: str | None,
    core_symlinks: bool | None,
) -> tuple[str, str, str | None]:
    """Classify a checkout without confusing WSL2 ext4 with Windows NTFS."""
    normalized_source = source or ""
    normalized_type = (filesystem_type or "").lower()
    normalized_options = (options or "").lower()
    is_wsl2 = "microsoft" in kernel.lower() or "wsl" in kernel.lower()
    is_windows_source = bool(WINDOWS_SOURCE_PATTERN.match(normalized_source))
    is_drvfs = "aname=drvfs" in normalized_options or normalized_type in {"drvfs", "fuseblk"}
    is_windows_git_checkout = core_symlinks is False

    if is_windows_source or is_drvfs or (normalized_type in {"9p", "v9fs"} and is_windows_git_checkout):
        return (
            "windows_ntfs_bind",
            "warning",
            "Move the checkout to the WSL2 ext4 filesystem; avoid /mnt/c and Windows Git for this workspace.",
        )
    if is_wsl2:
        return "wsl2_linux_filesystem", "ok", None
    return "linux_native", "ok", None


def assess_workspace() -> WorkspaceAssessment:
    """Build the workspace assessment used by lifecycle scripts."""
    kernel = platform.release()
    mount = mount_details(WORKSPACE)
    core_symlinks = parse_git_bool(git_config("core.symlinks"))
    profile, status, recommendation = classify_workspace(
        kernel=kernel,
        source=mount["source"],
        filesystem_type=mount["filesystem_type"],
        options=mount["options"],
        core_symlinks=core_symlinks,
    )
    return {
        "schema_version": 1,
        "profile": profile,
        "status": status,
        "recommendation": recommendation,
        "workspace": str(WORKSPACE),
        "kernel": kernel,
        "mount_source": mount["source"],
        "filesystem_type": mount["filesystem_type"],
        "mount_options": mount["options"],
        "git_core_symlinks": core_symlinks,
        "git_core_filemode": parse_git_bool(git_config("core.filemode")),
        "git_core_autocrlf": git_config("core.autocrlf"),
    }


def main() -> None:
    """Write the workspace preflight report and emit a useful warning."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=WORKSPACE / ".devcontainer/generated/workspace.json",
    )
    args = parser.parse_args()

    assessment = assess_workspace()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(assessment, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(serialized, encoding="utf-8")

    if assessment["status"] == "warning":
        LOGGER.warning("Workspace profile: %s", assessment["profile"])
        LOGGER.warning("%s", assessment["recommendation"])
    else:
        LOGGER.info("Workspace profile: %s", assessment["profile"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
