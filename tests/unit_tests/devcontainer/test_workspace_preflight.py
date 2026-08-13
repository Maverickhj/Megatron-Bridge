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

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def load_preflight_module() -> ModuleType:
    """Load the standalone Dev Container preflight script."""
    script = Path(__file__).parents[3] / ".devcontainer" / "workspace_preflight.py"
    spec = importlib.util.spec_from_file_location("workspace_preflight", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
@pytest.mark.parametrize(
    ("source", "filesystem_type", "options"),
    [
        (r"C:\[Users/example/Project/Megatron-Bridge]", "9p", "rw,aname=drvfs"),
        ("/dev/sdc", "drvfs", "rw"),
    ],
)
def test_classifies_windows_checkout_as_slow(source: str, filesystem_type: str, options: str) -> None:
    module = load_preflight_module()
    profile, status, recommendation = module.classify_workspace(
        kernel="6.6.87.2-microsoft-standard-WSL2",
        source=source,
        filesystem_type=filesystem_type,
        options=options,
        core_symlinks=False,
    )

    assert profile == "windows_ntfs_bind"
    assert status == "warning"
    assert recommendation is not None


@pytest.mark.unit
def test_classifies_wsl_ext4_checkout_as_optimized() -> None:
    module = load_preflight_module()
    profile, status, recommendation = module.classify_workspace(
        kernel="6.6.87.2-microsoft-standard-WSL2",
        source="/dev/sdc",
        filesystem_type="ext4",
        options="rw,relatime",
        core_symlinks=True,
    )

    assert profile == "wsl2_linux_filesystem"
    assert status == "ok"
    assert recommendation is None


@pytest.mark.unit
def test_classifies_native_linux_checkout() -> None:
    module = load_preflight_module()
    profile, status, recommendation = module.classify_workspace(
        kernel="6.8.0-generic",
        source="/dev/nvme0n1p2",
        filesystem_type="ext4",
        options="rw,relatime",
        core_symlinks=True,
    )

    assert profile == "linux_native"
    assert status == "ok"
    assert recommendation is None
