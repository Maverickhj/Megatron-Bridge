# Megatron-Bridge ↔ AI-Infra 文档联动

本目录记录 Megatron-Bridge 文档与私有 Obsidian 知识库（AI-Infra）之间的低耦合联动约定。
Megatron-Bridge 是编辑源，AI-Infra 只接收经过挑选的剪藏笔记，两个仓库不维护自动同步。

## 原则

- **单一编辑源**：技术文档先在 `docs/` 写完整；AI-Infra 中不编辑共享文档的副本。
- **低耦合**：只在 AI-Infra 的 `01_Inbox/` 放“来源 + 待整理要点”的剪藏笔记，不自动镜像整个目录。
- **公开安全**：Megatron-Bridge 是公开仓库，只向 AI-Infra 传递可公开的内容；不传密钥、日志、checkpoint、私有路径。
- **只收用户撰写的内容**：默认只同步用户本人撰写的 Markdown；`SKILL.md`、上游/官方文档和其他非用户撰写的 md 一律不进入 AI-Infra，除非用户明确指定。
- **整理责任在 AI-Infra**：Inbox 中的笔记按 `10_Projects/Megatron-Bridge/`、`20_Knowledge/`、`40_Runbooks/`、`80_MOCs/` 归位。

## 操作流程

1. 在 Megatron-Bridge 编辑或新增用户自己撰写的 Markdown；不确定来源时先问用户。
2. 认为值得沉淀时，在 AI-Infra 的 `01_Inbox/` 新建剪藏笔记，frontmatter 的 `source` 指向本仓库对应文件，并加 `> [!todo]`。
3. 在 AI-Infra 侧阅读、整理、归位；完成后把剪藏从 Inbox 移出，并将 `status` 从 `seed` 推进。
4. 不在 AI-Infra 反向修改来源文档；发现文档问题时回 Megatron-Bridge 修改。

## 自动化脚本

`scripts/sync_ai_infra_inbox.py` 通过 GitHub Contents API 把清单中的文档写入 AI-Infra 的 `01_Inbox/`，不需要 clone AI-Infra 仓库。

- 清单：`docs/ai-infra/inbox-manifest.json`，只同步显式列出的文档。
- 目标仓库通过环境变量传入，不把私有仓库地址写进公开清单：`export AI_INFRA_REPO=<owner>/AI-Infra`。
- 认证：`GITHUB_TOKEN` 环境变量，或已登录的 `gh` CLI；token 需要对 AI-Infra 具有 `contents:write` 权限。
- 幂等：只更新由本脚本生成、且未被手工修改的笔记；手工编辑过的 Inbox 笔记会被跳过。
- 清单只放用户明确认可的、用户自己撰写的 md；`SKILL.md` 与上游文档不得写入清单，除非用户另行指定。

```bash
python scripts/sync_ai_infra_inbox.py --print-content   # 本地预览，不写远程
python scripts/sync_ai_infra_inbox.py --apply           # 实际写入 AI-Infra
```

## docs/debug/ 同步选题

按当前约定，除 `qwen35-vl-800m-sft-smoke.md` 外，其余文档都进入 AI-Infra：

| 来源文档 | 建议 AI-Infra 落位 |
| --- | --- |
| `docs/debug/megatron-lm 链路可观测性 roadmap.md` | `10_Projects/Megatron-Bridge/Notes/` |
| `docs/debug/qwen3.5 vl 链路观测指南.md` | `10_Projects/Megatron-Bridge/Notes/` |
| `docs/debug/qwen35-vl-800m-sft-memory.md` | `10_Projects/Megatron-Bridge/Experiments/` |
| `docs/debug/megatron-bridge-estimator-count-parameters.md` | `20_Knowledge/`，参数估算方法通用化后再归位 |

排除：`docs/debug/qwen35-vl-800m-sft-smoke.md` 留在 Megatron-Bridge，不进入 AI-Infra。

## 已建立的 Inbox 剪藏

以下 4 篇是基于上游文档建立的旧剪藏，按新规则需与你确认是否移除：

- `01_Inbox/Megatron-Bridge - AutoBridge 与模型接入链路.md`
- `01_Inbox/Megatron-Bridge - HF 到 MCore 转换与参数映射.md`
- `01_Inbox/Megatron-Bridge - Recipe 与训练入口.md`
- `01_Inbox/Megatron-Bridge - 并行与性能优化主题.md`

## 默认排除

- 所有 `skills/**/SKILL.md` 与 `skills/` 下的其他说明文档。
- 上游/官方文档：`docs/bridge-guide.md`、`docs/bridge-tech-details.md`、`docs/adding-new-models.md`、`docs/training/`、`docs/models/` 等。
- 任何无法确认是用户本人撰写的 md；若要例外，必须由用户逐篇明确指定。
