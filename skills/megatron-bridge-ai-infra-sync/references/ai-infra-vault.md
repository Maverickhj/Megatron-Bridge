# AI-Infra Vault Conventions

Reference for planning where synced docs land and for presenting confirmation plans.

## Contents

- Layout
- Placement rules
- Frontmatter
- Privacy checklist
- Confirmation template

## Layout

```text
00_Home/          Daily dashboards, active work, quick access.
01_Inbox/         Temporary, unsorted, clipped, unreviewed material.
10_Projects/      Work tied to a concrete goal, repository, or deliverable.
20_Knowledge/     Reusable, project-independent technical knowledge.
30_Sources/       Papers, documentation, repositories, talks, standards.
40_Runbooks/      Repeatable operational and troubleshooting procedures.
50_Experiments/   Experiments, benchmarks, and validation records.
60_Decisions/     ADRs and important choices.
70_Timeline/      Daily notes, reviews, meetings, incident timelines.
80_MOCs/          Long-lived topic maps and curated navigation.
90_Templates/     Obsidian note templates.
91_AI/            Reusable AI prompts, workflows, and evaluations only.
98_Archive/       Deprecated, imported, or inactive material.
99_Assets/        Images, diagrams, attachments, exported charts.
```

## Placement rules

- Do not create new top-level directories. If placement is ambiguous, use `01_Inbox/Unsorted/` rather than inventing taxonomy.
- Choose location by lifecycle first, then ownership, then content type:
  1. Unsorted, incomplete, or unverified: `01_Inbox/`.
  2. Active project-specific: `10_Projects/<Project>/`.
  3. Mature and reusable: `20_Knowledge/` through `60_Decisions/`.
  4. Inactive or deprecated: `98_Archive/`, only when authorized.
- Megatron-Bridge docs usually map as follows:
  - Model integration and bridge internals: `10_Projects/Megatron-Bridge/Notes/`.
  - Memory, smoke, or run results: `10_Projects/Megatron-Bridge/Experiments/`.
  - Reusable estimation methods or general optimization: `20_Knowledge/`.
  - Copy-paste operational commands: `40_Runbooks/`.
  - Cross-topic navigation: `80_MOCs/`.
- Avoid empty or speculative directories. Create a category only when it has roughly 5-10 items or needs independent browsing.
- Each project has one entry note: `10_Projects/<Project>/_Project - <Project>.md` plus `Notes/`, `Meetings/`, `Experiments/`, `Decisions/`, and `Assets/` only when needed.

## Frontmatter

Minimal frontmatter for new formal knowledge notes:

```yaml
---
type: knowledge
status: seed
created: YYYY-MM-DD
updated: YYYY-MM-DD
domains: []
aliases: []
source: []
ai_generated: false
reviewed: false
---
```

Supported `type` values include: `project`, `knowledge`, `source`, `paper`, `runbook`, `experiment`, `decision`, `incident`, `meeting`, `daily`, `moc`.

When organizing a synced Inbox note:

- Move the note out of `01_Inbox/` into the agreed target.
- Promote `status` from `seed` toward `growing` or the final state.
- Keep the `source` field pointing at the Megatron-Bridge file.
- Mark substantive AI-generated content `ai_generated: true` and `reviewed: false`, with a warning callout until verified.

## Privacy checklist

Before proposing or applying a sync, verify every source doc:

- Authored by the user. `SKILL.md` files and upstream or third-party Markdown are excluded unless the user explicitly names the specific file.
- No secrets, tokens, private endpoints, SSH keys, or personal paths.
- No checkpoints, datasets, full logs, traces, or large generated files.
- Megatron-Bridge is public, so any content synced into AI-Infra was already public-safe.
- Do not publish the private AI-Infra repo URL in public Megatron-Bridge files. Pass the target repo through `AI_INFRA_REPO`.

## Confirmation template

Present a plan similar to this and wait for approval:

```markdown
**同步计划确认**

来源仓库：Maverickhj/Megatron-Bridge@main
目标仓库：AI-Infra 的 `01_Inbox/`（通过 GitHub API 写入，不 clone）

| 来源文档 | 生成 Inbox 笔记 | 建议后续落位 |
| --- | --- | --- |
| docs/debug/xxx.md | Megatron-Bridge - xxx.md | 10_Projects/Megatron-Bridge/Notes/ |

排除：
- docs/debug/qwen35-vl-800m-sft-smoke.md（按约定留在 Megatron-Bridge）

需要：
- AI_INFRA_REPO=<owner>/AI-Infra
- GITHUB_TOKEN=<contents:write on AI-Infra>

确认后我会执行 `python scripts/sync_ai_infra_inbox.py --apply`。
```

Do not run `--apply` until the user explicitly approves this plan.
