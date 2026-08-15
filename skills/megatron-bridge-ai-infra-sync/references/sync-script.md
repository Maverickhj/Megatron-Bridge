# Sync Script Reference

Mechanics of `scripts/sync_ai_infra_inbox.py` and `docs/ai-infra/inbox-manifest.json`.

## Contents

- Commands
- Environment
- Manifest schema
- Generated note anatomy
- Idempotency
- Failure modes
- CI note

## Commands

```bash
python scripts/sync_ai_infra_inbox.py                 # dry run, plan only
python scripts/sync_ai_infra_inbox.py --print-content # dry run + full note preview
python scripts/sync_ai_infra_inbox.py --apply         # write to AI-Infra
```

Run from the Megatron-Bridge repo root. `--source-repo` and `--source-branch` default to the current git remote and `main`.

## Environment

- `AI_INFRA_REPO`: target repository as `owner/name`, for example `owner/AI-Infra`. Required for `--apply`; never hard-code it into public repo files.
- `GITHUB_TOKEN` or `GH_TOKEN`: token with `contents:write` on AI-Infra. Alternatively an authenticated `gh` CLI (`gh auth token`).
- `--target-branch` defaults to `main`.

Example:

```bash
export AI_INFRA_REPO=Maverickhj/AI-Infra
export GITHUB_TOKEN=<token>
python scripts/sync_ai_infra_inbox.py --apply
```

No clone of AI-Infra is needed; the script uses `PUT /repos/{owner}/{repo}/contents/{path}` and, for updates, first reads the existing SHA.

## Manifest schema

```json
{
  "inbox_dir": "01_Inbox",
  "note_prefix": "Megatron-Bridge - ",
  "items": [
    {
      "source": "docs/debug/megatron-lm 链路可观测性 roadmap.md",
      "target": "10_Projects/Megatron-Bridge/Notes/"
    }
  ],
  "excluded": [
    {
      "source": "docs/debug/qwen35-vl-800m-sft-smoke.md",
      "reason": "按约定留在 Megatron-Bridge，不进入 AI-Infra"
    }
  ]
}
```

- `items` is an allowlist; only listed files are synced.
- `target` is the recommended final folder, used only in the `> [!todo]` callout; the file itself always goes to `01_Inbox/`.
- `excluded` is informational and printed in every plan; keep a short `reason`.
- Adding a doc: only user-authored Markdown may be added; `SKILL.md` and upstream docs stay out unless the user explicitly names the file. Insert an `items` entry, run the dry run, and confirm the plan with the user.
- Removing a doc: remove the entry. Removing an already-created Inbox note requires explicit user approval.

## Generated note anatomy

Each synced doc becomes:

```markdown
---
type: source
status: seed
created: YYYY-MM-DD
updated: YYYY-MM-DD
domains: []
aliases: []
source:
  - https://github.com/<source-repo>/blob/<branch>/<source-path>
sync_source: <source-path>
ai_generated: false
reviewed: false
---

> [!todo]
> 自动剪藏自 `<source-repo>`，待整理到 `<target>`。
> 来源：<source-url>
> 同步脚本：`scripts/sync_ai_infra_inbox.py`；如要手工编辑，请先把本笔记移出 `01_Inbox/`。

## 原文元数据

```yaml
<original frontmatter preserved verbatim>
```

## 原文

<original Markdown body>
```

- The note keeps the source doc's `[[wikilinks]]`, which work inside Obsidian.
- If the source body contains relative Markdown links, the script adds a `> [!warning]` about link validation.
- The original frontmatter is preserved as a fenced YAML block so no metadata is lost.

## Idempotency

- New file: created with a `docs(ai-infra): inbox <source>` commit.
- Existing generated note with unchanged content: skipped as `[不变]`.
- Existing generated note with changed content: updated with a `docs(ai-infra): refresh <source>` commit.
- Existing note without the `sync_source: <source>` marker, or one that was manually edited: skipped as `[跳过]` to protect user work.

To re-sync after manual edits, move or rename the Inbox note first, or ask the user whether overwriting is acceptable.

## Failure modes

- "需要 GitHub token": set `GITHUB_TOKEN` or install and log in to `gh`.
- "请通过 AI_INFRA_REPO ... 指定目标仓库": set `AI_INFRA_REPO` or pass `--target-repo`.
- `HTTP 404` on GET: file does not exist yet; the script creates it. 404 elsewhere means the repo path is wrong.
- `HTTP 422` or `409`: usually a missing/outdated `sha` on update, invalid branch, or a permissions problem. Show the response detail to the user.
- "来源文件不存在": fix the manifest path or tell the user the doc was moved.
- Source links 404 after sync: the source files are untracked or not pushed on `--source-branch`. Commit and push first, or re-run with `--source-branch` set to the branch that contains them.
- Several `[跳过]` lines: inspect whether a previous agent or the user edited those Inbox notes manually.

## CI note

Optionally run `--apply` from a GitHub Actions workflow in Megatron-Bridge using a repository secret for the AI-Infra token. Before setting that up, confirm with the user: public-repo workflows must not expose the secret to fork PRs, and scheduled auto-writes reduce human review. The default skill workflow remains manual and confirmation-gated.
