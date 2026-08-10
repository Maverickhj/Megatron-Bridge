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
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch


LOGGER = logging.getLogger(__name__)
WORKSPACE = Path("/opt/Megatron-Bridge")


def read_optional(path: str) -> str:
    """Read an optional host or container identity file."""
    file = Path(path)
    if not file.exists():
        return ""
    try:
        return file.read_text(errors="ignore").replace("\x00", "").strip()
    except OSError:
        return ""


def command_output(command: list[str]) -> str | None:
    """Return stripped command output without making detection fail."""
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None


def git_revision(path: Path) -> str | None:
    """Return the Git revision for a checkout when available."""
    return command_output(["git", "-C", str(path), "rev-parse", "HEAD"])


def system_memory_gib() -> float | None:
    """Return visible system memory in GiB."""
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / 1024**3, 2)
    except (AttributeError, OSError, ValueError):
        return None


def detected_profile(*, machine: str, kernel: str, gpu_name: str, hardware_identity: str) -> tuple[str, str]:
    """Classify the supported host while preserving a generic fallback."""
    override = os.environ.get("MINIMIND_RUNTIME_PROFILE")
    if override:
        return override, "environment_override"

    is_x86_64 = machine in {"x86_64", "amd64"}
    is_arm64 = machine in {"aarch64", "arm64"}
    is_wsl2 = is_x86_64 and ("microsoft" in kernel or "wsl" in kernel)
    is_dgx_spark = is_arm64 and any(marker in hardware_identity for marker in ("dgx spark", "gb10", "grace blackwell"))

    if is_wsl2 and "4070 ti super" in gpu_name.lower():
        return "windows_wsl2_ada_16g", "automatic"
    if is_dgx_spark:
        return "dgx_spark_arm64_uma", "automatic"
    if torch.cuda.is_available() and is_x86_64:
        return "nvidia_x86_64_generic", "automatic_fallback"
    if torch.cuda.is_available() and is_arm64:
        return "nvidia_arm64_generic", "automatic_fallback"
    if torch.cuda.is_available():
        return "nvidia_generic", "automatic_fallback"
    return "cpu_only", "automatic_fallback"


def profile_defaults(profile: str) -> dict[str, Any]:
    """Return conservative resource defaults without changing model semantics."""
    defaults: dict[str, Any] = {
        "nproc_per_node": 1,
        "tensor_model_parallel_size": 1,
        "pipeline_model_parallel_size": 1,
        "context_parallel_size": 1,
        "micro_batch_size": 1,
        "precision": "bf16",
        "fp8": False,
        "torch_compile": False,
    }
    if profile == "windows_wsl2_ada_16g":
        defaults.update(dataloader_workers=2, gradient_checkpointing=True, sequence_length_hint=256)
    elif profile == "dgx_spark_arm64_uma":
        defaults.update(dataloader_workers=4, gradient_checkpointing=True, sequence_length_hint=512)
    else:
        defaults.update(dataloader_workers=2, gradient_checkpointing=True, sequence_length_hint=256)
    return defaults


def detect_runtime() -> dict[str, Any]:
    """Build the versioned runtime record for the current container."""
    machine = platform.machine().lower()
    kernel = platform.release().lower()
    gpu_available = torch.cuda.is_available()
    device_count = torch.cuda.device_count() if gpu_available else 0
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else ""
    gpu_props = torch.cuda.get_device_properties(0) if gpu_available else None
    capability = torch.cuda.get_device_capability(0) if gpu_available else None

    identity_parts = [
        gpu_name,
        read_optional("/proc/device-tree/model"),
        read_optional("/proc/device-tree/compatible"),
        read_optional("/sys/class/dmi/id/product_name"),
        read_optional("/sys/devices/virtual/dmi/id/product_name"),
    ]
    hardware_identity = " ".join(part for part in identity_parts if part).lower()
    profile, detection_source = detected_profile(
        machine=machine,
        kernel=kernel,
        gpu_name=gpu_name,
        hardware_identity=hardware_identity,
    )
    compute_capability = f"{capability[0]}.{capability[1]}" if capability else None

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "profile": profile,
        "detection_source": detection_source,
        "machine": machine,
        "kernel": kernel,
        "hardware_identity": hardware_identity,
        "gpu_available": gpu_available,
        "device_count": device_count,
        "gpu_name": gpu_name or None,
        "compute_capability": compute_capability,
        "gpu_memory_gib": round(gpu_props.total_memory / 1024**3, 2) if gpu_props else None,
        "system_memory_gib": system_memory_gib(),
        "memory_model": "unified" if profile == "dgx_spark_arm64_uma" else "discrete" if gpu_available else "none",
        "nvidia_driver_version": command_output(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"]),
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "torch_cuda_arch_list": compute_capability,
        "container_image": os.environ.get("MINIMIND_NEMO_IMAGE"),
        "bridge_source_tag": os.environ.get("MINIMIND_BRIDGE_SOURCE_TAG"),
        "megatron_bridge_commit": git_revision(WORKSPACE),
        "megatron_lm_commit": git_revision(WORKSPACE / "3rdparty/Megatron-LM"),
        "resource_defaults": profile_defaults(profile),
    }


def main() -> None:
    """Detect the runtime and write its JSON record."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=WORKSPACE / ".devcontainer/generated/runtime.json",
    )
    args = parser.parse_args()

    runtime = detect_runtime()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(runtime, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(serialized, encoding="utf-8")
    LOGGER.info("Runtime profile written to %s\n%s", args.output, serialized.rstrip())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
