# Multi-Architecture Development Container

This repository includes a Dev Container for development on both Windows with WSL2 and NVIDIA DGX Spark. It uses one pinned, multi-architecture NeMo image and lets Docker select the `linux/amd64` or `linux/arm64` manifest automatically.

## Supported development hosts

| Host | Container architecture | Workspace recommendation |
| --- | --- | --- |
| Windows 11, Docker Desktop, WSL2, NVIDIA GPU | `linux/amd64` | Clone under the WSL2 Linux home directory |
| NVIDIA DGX Spark | `linux/arm64` | Clone on the native Linux filesystem |

Do not place the active Windows checkout under `C:\...` or `/mnt/c/...`. Those paths use a Windows filesystem bind mount, which can make Git, pre-commit, and tests substantially slower.

## Windows setup

List the installed WSL distributions from PowerShell:

```powershell
wsl --list --verbose
```

Choose a working Ubuntu distribution and clone the development branch under its Linux home directory. Replace the repository URL with the HTTPS URL of the fork that contains the branch:

```powershell
$WslDistribution = "Ubuntu-22.04"
wsl -d $WslDistribution
```

```bash
mkdir -p ~/projects
cd ~/projects
REPOSITORY_URL="https://github.com/<your-account>/Megatron-Bridge.git"
git clone --branch codex/dev-v0.5.1-minimind --single-branch \
  "${REPOSITORY_URL}"
cd Megatron-Bridge
git config core.autocrlf input
git config core.filemode true
git config core.symlinks true
git submodule update --init --recursive
```

Verify that the checkout is not under `/mnt/c` and is backed by the WSL2 Linux filesystem:

```bash
pwd
stat -f -c '%T' .
git status --short
```

Open VS Code from that shell and select **Dev Containers: Reopen in Container**:

```bash
code .
```

## DGX Spark setup

Clone the same branch on the DGX Spark filesystem, initialize the submodule, and open the checkout through VS Code Remote SSH:

```bash
mkdir -p ~/projects
cd ~/projects
REPOSITORY_URL="https://github.com/<your-account>/Megatron-Bridge.git"
git clone --branch codex/dev-v0.5.1-minimind --single-branch \
  "${REPOSITORY_URL}"
cd Megatron-Bridge
git submodule update --init --recursive
```

Run **Dev Containers: Reopen in Container** after connecting with Remote SSH. The ARM64 NeMo manifest and DGX Spark runtime profile still require validation on the physical machine.

## Starting without VS Code

From the Linux checkout:

```bash
docker compose -f .devcontainer/compose.yaml up -d --wait
docker compose -f .devcontainer/compose.yaml exec -T dev \
  bash .devcontainer/post_create.sh
docker compose -f .devcontainer/compose.yaml exec -T dev \
  bash .devcontainer/post_start.sh
```

Open a shell:

```bash
docker compose -f .devcontainer/compose.yaml exec dev bash
```

Stop the container while preserving all named volumes:

```bash
docker compose -f .devcontainer/compose.yaml down
```

Do not add `-v` unless the Hugging Face cache, datasets, checkpoints, run outputs, and other persistent volumes should be deleted.

## Mount layout

| Container path | Source | Purpose |
| --- | --- | --- |
| `/opt/Megatron-Bridge` | Current checkout | Source and Git metadata |
| `/data/hf` | Named volume | Hugging Face cache |
| `/data/datasets` | Named volume | Datasets |
| `/data/checkpoints` | Named volume | Checkpoints |
| `/data/runs` | Named volume | Run artifacts |
| `/data/cache` | Named volume | uv and general caches |
| `/opt/vendor` | Named volume | External reference source |

Named volumes use the stable Compose project name `minimind-megatron-bridge`, so moving the checkout does not delete or duplicate those volumes when the old container is stopped first.

## Automatic checks

The first container creation runs `.devcontainer/post_create.sh`:

1. Trust only the fixed repository and Megatron-LM submodule paths inside the container.
2. Generate `.devcontainer/generated/workspace.json`.
3. Initialize the pinned Megatron-LM submodule.
4. Apply Windows Git compatibility only for an actual Windows filesystem checkout.

Every start runs `.devcontainer/post_start.sh` and writes:

- `workspace.json`: filesystem and Git checkout assessment;
- `runtime.json`: architecture, GPU, CUDA, and version information;
- `verification.json`: CUDA, Transformer Engine, and workspace import results.

Inspect the reports:

```bash
python -m json.tool .devcontainer/generated/workspace.json
python -m json.tool .devcontainer/generated/runtime.json
python -m json.tool .devcontainer/generated/verification.json
```

An optimized WSL2 checkout reports:

```text
profile: wsl2_linux_filesystem
status: ok
```

A Windows filesystem checkout reports `windows_ntfs_bind` and recommends moving to WSL2 ext4.

## Validation and performance

Run the relevant checks inside the container:

```bash
time git status --short
time git diff --quiet
time uv run --no-sync pre-commit run --all-files
```

Recommended acceptance targets for a clean WSL2 ext4 checkout:

| Check | Target |
| --- | ---: |
| `git status --short` | less than 1 second |
| `git diff --quiet` | less than 2 seconds |
| Full pre-commit | less than 30 seconds |
| Post-start GPU gate | less than 60 seconds |

The exact result depends on host load and whether hook environments are already cached.

### Observed Windows validation

The WSL2 ext4 migration was validated on an RTX 4070 Ti SUPER host with warm caches:

| Check | Observed |
| --- | ---: |
| Workspace mount | `ext4` |
| Workspace profile | `wsl2_linux_filesystem` |
| `git status --short` | 0.224 seconds |
| `git diff --no-ext-diff --ignore-submodules` | 0.010 seconds |
| Pre-commit on the changed files | 0.320 seconds |
| Full pre-commit | 0.594 seconds |
| Post-start GPU and import gates | 22.1 seconds |

CUDA matrix multiplication, a Transformer Engine BF16 forward/backward pass, and both Bridge and Megatron-LM imports passed. DGX Spark ARM64 validation remains a required hardware-side follow-up.

## Troubleshooting

### Workspace reports `windows_ntfs_bind`

Confirm that the checkout is not under `/mnt/c` and was cloned with Linux Git. Do not copy an existing Windows `.git` directory into WSL2. Clone again under `~/projects` if necessary.

### Submodule appears dirty only in Windows Git

Windows Git cannot represent some Megatron-LM symlinks in the same way as Linux. Use the WSL2 ext4 checkout as the source of truth. The compatibility setting for a Windows checkout ignores dirty content but still reports a changed submodule commit.

### A WSL distribution fails to start

Try another installed distribution from `wsl --list --verbose`, then repair the failed distribution separately. The Dev Container configuration does not depend on a specific Ubuntu release.

### CUDA is unavailable

Verify Docker Desktop WSL integration and run:

```bash
docker run --rm --gpus all \
  nvcr.io/nvidia/nemo:26.06@sha256:912033288c982a8c4af05df46a1d670c34350f1427c758f5da9c485bdec57264 \
  python -c 'import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name())'
```
