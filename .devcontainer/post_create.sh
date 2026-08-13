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
workspace_report="${workspace}/.devcontainer/generated/workspace.json"

cd "${workspace}"

for git_directory in "${workspace}" "${megatron_lm}"; do
  git config --global --get-all safe.directory | grep -Fxq "${git_directory}" || \
    git config --global --add safe.directory "${git_directory}"
done

uv run --no-sync python .devcontainer/workspace_preflight.py --output "${workspace_report}"
workspace_profile="$(uv run --no-sync python -c \
  "import json,sys; sys.stdout.write(json.load(open('${workspace_report}'))['profile'])")"

git submodule update --init --recursive

if [[ "${workspace_profile}" == "windows_ntfs_bind" ]]; then
  git -C "${megatron_lm}" config core.filemode false
  git config submodule.3rdparty/Megatron-LM.ignore dirty
fi

chmod +x .devcontainer/post_create.sh .devcontainer/post_start.sh scripts/run_detected.sh
