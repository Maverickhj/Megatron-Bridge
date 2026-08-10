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
from pathlib import Path

import torch
import transformer_engine  # type: ignore[import-untyped]  # Upstream package does not publish type information.
import transformer_engine.pytorch as te  # type: ignore[import-untyped]  # Upstream package has no typed marker.
import transformers
from megatron import (  # type: ignore[import-untyped]  # Namespace packages do not publish type information.
    bridge,
    core,
)


LOGGER = logging.getLogger(__name__)
WORKSPACE = Path("/opt/Megatron-Bridge").resolve()


def is_workspace_import(module_file: str | None) -> bool:
    """Return whether a module was imported from the mounted checkout."""
    if not module_file:
        return False
    try:
        return Path(module_file).resolve().is_relative_to(WORKSPACE)
    except (OSError, ValueError):
        return False


def main() -> None:
    """Run the bounded GPU, Transformer Engine, and import-path gate."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=WORKSPACE / ".devcontainer/generated/verification.json",
    )
    args = parser.parse_args()

    runtime = json.loads(args.runtime.read_text(encoding="utf-8"))
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available inside the development container")
    if not is_workspace_import(bridge.__file__):
        raise RuntimeError(f"megatron.bridge is not imported from workspace: {bridge.__file__}")
    if not is_workspace_import(core.__file__):
        raise RuntimeError(f"megatron.core is not imported from workspace: {core.__file__}")

    torch.manual_seed(1)
    matrix = torch.randn(1024, 1024, device="cuda", dtype=torch.float32)
    matmul = matrix @ matrix
    matmul_finite = bool(torch.isfinite(matmul).all())
    if not matmul_finite:
        raise RuntimeError("CUDA FP32 matmul produced non-finite output")

    layer = te.Linear(128, 128, params_dtype=torch.bfloat16).cuda()
    inputs = torch.randn(4, 128, device="cuda", dtype=torch.bfloat16, requires_grad=True)
    outputs = layer(inputs)
    loss = outputs.float().square().mean()
    loss.backward()
    gradient_finite = inputs.grad is not None and bool(torch.isfinite(inputs.grad).all())
    if not gradient_finite:
        raise RuntimeError("Transformer Engine backward produced invalid gradients")

    report = {
        "schema_version": 1,
        "runtime_profile": runtime["profile"],
        "gpu": torch.cuda.get_device_name(0),
        "matmul_finite": matmul_finite,
        "te_forward_shape": list(outputs.shape),
        "te_forward_dtype": str(outputs.dtype),
        "te_loss": loss.item(),
        "te_input_grad_finite": gradient_finite,
        "torch_version": torch.__version__,
        "transformer_engine_version": transformer_engine.__version__,
        "transformers_version": transformers.__version__,
        "bridge_import": bridge.__file__,
        "core_import": core.__file__,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(serialized, encoding="utf-8")
    LOGGER.info("Environment verification passed; report written to %s\n%s", args.output, serialized.rstrip())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
