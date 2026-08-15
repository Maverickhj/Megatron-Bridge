---
name: megatron-bridge-ai-infra-sync
description: Sync curated, user-authored Megatron-Bridge docs into the private AI-Infra Obsidian vault Inbox through the GitHub Contents API without cloning AI-Infra. Use when the user asks to sync, stage, or organize their own Megatron-Bridge design docs, experiments, debug notes, or learning material into AI-Infra, or to maintain docs/ai-infra/inbox-manifest.json. Never include SKILL.md or upstream/other-authored Markdown unless the user explicitly names them. Always present the sync plan and get explicit user confirmation before writing to AI-Infra.
---

# Megatron-Bridge to AI-Infra Sync

## Overview

Stage selected Markdown docs from the current Megatron-Bridge repo into the AI-Infra vault's `01_Inbox/`. The Megatron-Bridge repo stays the single editing source; AI-Infra receives curated Inbox notes only, with no clone of AI-Infra and no bidirectional sync.

Core assets live in the repo, not in this skill:

- Sync script: `scripts/sync_ai_infra_inbox.py`
- Sync allowlist: `docs/ai-infra/inbox-manifest.json`
- Workflow notes: `docs/ai-infra/README.md`

## Workflow

1. **Locate the repo assets.** Confirm the current directory is the Megatron-Bridge repo. If the script or manifest is missing, tell the user and stop rather than guessing paths.
2. **Review candidates and the manifest.** Read `docs/ai-infra/inbox-manifest.json` and the candidate docs. Keep only Markdown authored by the user, and only docs the user considers valuable. `SKILL.md` files and upstream or third-party docs are excluded by default and need an explicit per-file user request to be included. Add, remove, or reorder entries only when the user asks. Excluded docs, such as smoke tests, stay in the manifest's `excluded` list with a reason.
3. **Build the sync plan.** Check `git status --short` and `git branch --show-current` first. The generated `source` links point at the sync branch, so untracked or unpushed source docs would 404 after the sync. Note this in the plan, or use `--source-branch` when applying. Then run `python scripts/sync_ai_infra_inbox.py` and, when the user wants detail, `python scripts/sync_ai_infra_inbox.py --print-content`. The dry run produces the exact plan: source paths, target Inbox names, recommended placement, and excluded files.
4. **Confirm the plan with the user before any write.** Present a compact summary and wait for explicit approval:
   - Sources to sync and recommended AI-Infra placement.
   - Generated Inbox note names.
   - Excluded files and reasons.
   - Required environment: `AI_INFRA_REPO` and `GITHUB_TOKEN` with `contents:write` on AI-Infra.
   - Any privacy or scope concerns found in step 2.
   Never run `--apply` without this approval. Use the template in `references/ai-infra-vault.md`.
5. **Apply after approval.** Set the environment variables and run `python scripts/sync_ai_infra_inbox.py --apply`. Report created, updated, unchanged, and skipped counts, including commit SHAs when available.
6. **Finish with next steps.** Remind the user to run `git pull` in the AI-Infra vault and to later move each note from `01_Inbox/` to its target folder. Do not organize AI-Infra notes beyond what the user requested.

## Rules

- Sync only files listed in the manifest; never mirror whole directories or auto-sync everything.
- Sync only user-authored Markdown. Never stage `SKILL.md` files or upstream/other-authored docs unless the user explicitly names that specific file for an exception.
- Only public-safe content leaves Megatron-Bridge. Exclude secrets, tokens, private paths, logs, checkpoints, and large generated files.
- Megatron-Bridge is the editing source. Never edit the generated Inbox notes directly; fix the source doc in Megatron-Bridge and re-run the sync. The script skips manually modified Inbox notes to avoid overwriting user edits.
- Verify the source docs exist on the target branch of the source repo before applying; otherwise the generated `source` URLs will 404.
- Keep a single task within AI-Infra's small-change limit (around five files) unless the user explicitly approves a larger scope.
- Preserve Obsidian conventions: keep `[[wikilinks]]`, keep the original frontmatter in a `## 原文元数据` fenced block, and leave organization to later. See `references/ai-infra-vault.md`.
- Do not expose the private AI-Infra repo URL in public Megatron-Bridge files; pass the target repo through `AI_INFRA_REPO`.

## Resources

- `references/ai-infra-vault.md`: AI-Infra placement, frontmatter, privacy checklist, and the confirmation message template.
- `references/sync-script.md`: CLI usage, manifest schema, idempotency behavior, and common failure modes.
