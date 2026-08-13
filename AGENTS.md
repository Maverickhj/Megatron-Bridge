# AGENTS.md — Megatron Bridge (Personal Learning)

个人学习用途的精简说明。完整项目规范见 `AGENTS.md.bkp`。

## Project map
- Package: `megatron.bridge`; Python 3.12.
- HF <-> Megatron bridge code: `src/megatron/bridge/`.
- Per-model family:
  - `models/<family>/bridge.py`: HF <-> Megatron conversion
  - `models/<family>/config_mapping.py`: HF config -> Megatron config
  - `models/<family>/param_mapping.py`: parameter name mapping
  - `models/<family>/hf_pretrained/`: HF model definitions
  - `recipes/<family>/`: pretraining/SFT/LoRA recipes
- `AutoBridge`: `models/conversion/auto_bridge.py`, selects bridge from HF model name/path.
- Megatron-LM submodule: `3rdparty/Megatron-LM/`.

## Focus areas
- Integrate small models.
- Run the pipeline end-to-end and trace the code path, including Megatron-LM.
- Make small functional changes: scheduling, operators.
- Profile with available tools.

## Common commands
- `uv sync`
- `uv sync --group dev`
- `uv run python -m pytest tests/unit_tests/...`
- `uv run python -m torch.distributed.run --nproc_per_node=2 script.py`
- `uv run pre-commit run --all-files` (optional)
- `uv run mypy --strict path/to/file.py`
- `git submodule update --init`

## Relevant skills (read as needed)
- Model integration: `skills/adding-model-support/SKILL.md`
- Training pipeline: `skills/nemo-mbridge-mlm-bridge-training/SKILL.md`
- Environment: `skills/build-and-dependency/SKILL.md`
- Testing: `skills/testing/SKILL.md`
- Perf/profiling:
  - `skills/nemo-mbridge-perf-parallelism-strategies/SKILL.md`
  - `skills/nemo-mbridge-perf-tp-dp-comm-overlap/SKILL.md`
  - `skills/nemo-mbridge-perf-cuda-graphs/SKILL.md`
  - `skills/nemo-mbridge-perf-activation-recompute/SKILL.md`
  - `skills/nemo-mbridge-perf-memory-tuning/SKILL.md`
  - `skills/nemo-mbridge-perf-moe-*/SKILL.md` (if working on MoE)

## Working rules
- Prefer reading Megatron-LM code before editing the submodule; avoid direct changes if possible.
- Use `logging.getLogger(__name__)` / `print_rank_0()` instead of bare `print()`.
- Run only tests related to the current change.
- Don't commit secrets, `.env`, or personal paths.
