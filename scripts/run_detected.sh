#!/usr/bin/env bash
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

set -euo pipefail

workspace=/opt/Megatron-Bridge
runtime_json="${workspace}/.devcontainer/generated/runtime.json"

uv run --no-sync python "${workspace}/.devcontainer/detect_runtime.py" \
  --output "${runtime_json}"

runtime_profile="$(uv run --no-sync python -c \
  "import json,sys; sys.stdout.write(json.load(open('${runtime_json}'))['profile'])")"

cuda_arch="$(uv run --no-sync python -c \
  "import json,sys; sys.stdout.write(json.load(open('${runtime_json}')).get('torch_cuda_arch_list') or '')")"

export MINIMIND_RUNTIME_PROFILE="${runtime_profile}"

if [[ -n "${cuda_arch}" ]]; then
  export TORCH_CUDA_ARCH_LIST="${cuda_arch}"
fi

exec "$@"
