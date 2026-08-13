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
megatron_lm="${workspace}/3rdparty/Megatron-LM"
generated="${workspace}/.devcontainer/generated"

cd "${workspace}"

for git_directory in "${workspace}" "${megatron_lm}"; do
  git config --global --get-all safe.directory | grep -Fxq "${git_directory}" || \
    git config --global --add safe.directory "${git_directory}"
done

uv run --no-sync python .devcontainer/workspace_preflight.py \
  --output "${generated}/workspace.json"
uv run --no-sync python .devcontainer/detect_runtime.py \
  --output "${generated}/runtime.json"
uv run --no-sync python .devcontainer/verify_env.py \
  --runtime "${generated}/runtime.json" \
  --output "${generated}/verification.json"
