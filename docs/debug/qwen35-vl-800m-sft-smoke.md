---
type: how-to
status: growing
created: 2026-08-14
updated: 2026-08-14
domains:
  - megatron
  - distributed-training
  - multimodal-training
aliases:
  - Qwen3.5-VL 0.8B SFT smoke
related:
  - "[[qwen3.5 vl 链路观测指南]]"
  - "[[megatron-lm 链路可观测性 roadmap]]"
  - "[[qwen35-vl-800m-sft-memory]]"
---

# Qwen3.5-VL 0.8B SFT Smoke 链路

`qwen35_vl_800m_sft_smoke_config()` 是一个最小 SFT 测试 recipe，用于验证
Qwen3.5-VL 0.8B 的配置构建、数据加载、模型构建、forward/backward 和 optimizer
是否能串起来。默认不依赖真实数据集。

## 配置特点

- `TP=1`，`PP=1`
- `global_batch_size=1`，`micro_batch_size=1`
- `train_iters=2`，`eval_iters=0`
- 默认 `seq_length=256`
- 默认关闭 checkpoint save（只验证训练链路，避免小内存环境在保存阶段 OOM）
- 默认使用 `MockVLMConversationProvider`，生成随机图像和短对话
- 可选使用 `PreloadedVLMConversationProvider` 读取本地 JSON/JSONL

## 前置条件

模型需要先缓存到 Hugging Face 缓存，或使用本地路径。当前 devcontainer 默认
`HF_HOME=/data/hf`：

```bash
export HF_HOME=/data/hf
hf download Qwen/Qwen3.5-0.8B
```

模型快照当前已存在于此 devcontainer 的 `/data/hf/hub/models--Qwen--Qwen3.5-0.8B`。
如果换到新环境，执行上面的 `hf download` 即可。

如果使用本地模型目录，将命令中的 `--hf_path` 指向本地路径即可：

```bash
--hf_path /path/to/Qwen3.5-0.8B
```

## 方式一：Mock 数据 smoke

直接通过 `run_recipe.py` 使用默认 recipe：

```bash
uv run --no-sync python -m torch.distributed.run --nproc_per_node=1 \
  scripts/training/run_recipe.py \
  --recipe qwen35_vl_800m_sft_smoke_config \
  --step_func qwen3_vl_step
```

默认会跑 2 个 iteration，不需要 checkpoint 或真实数据。只想做最快验证时，可以
在命令末尾追加：

```text
train.train_iters=1
```

## 方式二：本地少量 JSON 数据 smoke

准备一个 `train.json`，例如：

```json
[
  {
    "conversation": [
      {"role": "user", "content": [{"type": "text", "text": "Describe this image."}]},
      {"role": "assistant", "content": [{"type": "text", "text": "A simple smoke test."}]}
    ]
  }
]
```

然后运行：

```bash
uv run --no-sync python -m torch.distributed.run --nproc_per_node=1 \
  scripts/training/run_recipe.py \
  --recipe qwen35_vl_800m_sft_smoke_config \
  --dataset vlm-preloaded \
  --step_func qwen3_vl_step \
  dataset.train_data_path=/tmp/qwen35vl_smoke.json \
  dataset.hf_processor_path=Qwen/Qwen3.5-0.8B
```

`--dataset vlm-preloaded` 会真正把 provider 切换为
`PreloadedVLMConversationProvider`；只覆盖 `dataset.train_data_path` 不会改变默认
的 mock provider 类型。

如果 JSON 中的图片是相对路径，可以额外加：

```text
dataset.image_folder=/tmp/qwen35vl_images
```

## 自定义关键参数

```text
--hf_path /path/to/Qwen3.5-0.8B
train.train_iters=1
train.global_batch_size=1
train.micro_batch_size=1
model.seq_length=256
dataset.num_images=1
validation.eval_iters=0
```

说明：

- `--hf_path` 是 `run_recipe.py` 的合法参数，会传给本 recipe 的 `hf_path`。
- 使用 `--dataset vlm-preloaded` 时，`dataset.hf_processor_path` 也需要同时指定；
  若使用本地模型目录，两者通常都指向同一个本地路径。
- 直接调用 recipe 代码时也可以显式传入本地路径和 `train_data_path`，适合写自定义
  launcher：

```python
from megatron.bridge.recipes.qwen_vl import qwen35_vl_800m_sft_smoke_config

config = qwen35_vl_800m_sft_smoke_config(
    hf_path="/path/to/Qwen3.5-0.8B",
    train_data_path="/tmp/qwen35vl_smoke.json",
    image_folder="/tmp/qwen35vl_images",
    train_iters=1,
)
```

## 预期结果

- 日志中应出现 `Starting training loop at iteration 0`。
- 每个 iteration 应出现 `Step Time`、loss、grad norm 和 memory 输出。
- 应出现 `[after training is done]`，随后以退出码 `0` 结束。
- smoke recipe 默认 `checkpoint.save=None`，所以不应出现 `saving checkpoint`。
- 使用 mock 数据时不需要下载 Flickr8k/CORD-v2。
- 首次运行需要编译 dataset index helper，冷启动约 60 秒；后续运行会明显更快。

## 与观测指南的关系

这个 smoke recipe 适合作为
[[qwen3.5 vl 链路观测指南]] 中 L0/L1/L3 观测的最小载体。可以在上面直接开启
PyTorch profiler 或 Nsys，而不会被长时间数据加载和大 checkpoint 干扰。

显存估算与容量结论见 [[qwen35-vl-800m-sft-memory]]。
