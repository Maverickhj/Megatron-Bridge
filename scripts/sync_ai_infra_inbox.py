#!/usr/bin/env python3
"""Sync curated Megatron-Bridge docs into the AI-Infra Obsidian vault Inbox.

The script reads the allowlist in ``docs/ai-infra/inbox-manifest.json`` and
pushes each selected Markdown file into ``AI-Infra/01_Inbox/`` through the
GitHub Contents API. The AI-Infra repository never needs to be cloned.

Requirements:

- A GitHub token with ``contents:write`` on the AI-Infra repository, either
  exported as ``GITHUB_TOKEN`` or available through an authenticated ``gh``
  CLI (``gh auth token``).
- The target repository in ``AI_INFRA_REPO`` (for example
  ``AI_INFRA_REPO=owner/AI-Infra``).

Usage:

    python scripts/sync_ai_infra_inbox.py --print-content
    python scripts/sync_ai_infra_inbox.py --apply
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_RELATIVE_LINK = re.compile(r"\]\((?!#|(?:https?://|mailto:|//))[^)]*\)")
_SYNC_SCRIPT = "scripts/sync_ai_infra_inbox.py"


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return the raw YAML frontmatter and the body of a Markdown file."""
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 5 :].lstrip("\n")


def build_inbox_note(
    source_repo: str,
    source_branch: str,
    source_path: str,
    target: str,
    note_prefix: str,
    text: str,
) -> tuple[str, str]:
    """Build the Inbox note name and content for one source document."""
    frontmatter, body = split_frontmatter(text)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    quoted_path = urllib.parse.quote(source_path, safe="/")
    source_url = f"https://github.com/{source_repo}/blob/{source_branch}/{quoted_path}"
    note_name = f"{note_prefix}{Path(source_path).name}"

    lines = [
        "---",
        "type: source",
        "status: seed",
        f"created: {today}",
        f"updated: {today}",
        "domains: []",
        "aliases: []",
        "source:",
        f"  - {source_url}",
        f"sync_source: {source_path}",
        "ai_generated: false",
        "reviewed: false",
        "---",
        "",
        "> [!todo]",
        f"> 自动剪藏自 `{source_repo}`，待整理到 `{target}`。",
        f"> 来源：{source_url}",
        f"> 同步脚本：`{_SYNC_SCRIPT}`；如要手工编辑，请先把本笔记移出 `01_Inbox/`。",
        "",
    ]
    if _RELATIVE_LINK.search(body):
        lines += ["> [!warning]", "> 原文包含相对链接，整理时请核对链接是否仍然有效。", ""]
    if frontmatter:
        lines += ["## 原文元数据", "", "```yaml", frontmatter.strip(), "```", ""]
    lines += ["## 原文", "", body.rstrip(), ""]
    return note_name, "\n".join(lines)


def resolve_source_repo(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=True,
            cwd=root,
        )
        url = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        url = ""
    match = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?$", url)
    return match.group(1) if match else "Maverickhj/Megatron-Bridge"


def resolve_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        result = None
    if result and result.stdout.strip():
        return result.stdout.strip()
    raise SystemExit(
        "需要 GitHub token：设置 GITHUB_TOKEN 环境变量，或安装并登录 gh CLI。"
        "token 需要对 AI-Infra 仓库具有 contents:write 权限。"
    )


def contents_url(repo: str, path: str, branch: str | None = None) -> str:
    quoted_path = urllib.parse.quote(path, safe="/")
    url = f"https://api.github.com/repos/{repo}/contents/{quoted_path}"
    if branch:
        url += f"?ref={urllib.parse.quote_plus(branch)}"
    return url


def api_request(token: str, method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "megatron-bridge-ai-infra-sync")
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"GitHub API {method} {url} 失败：HTTP {exc.code}\n{detail[:800]}") from exc


def get_existing(token: str, repo: str, path: str, branch: str) -> tuple[str | None, str | None]:
    entry = api_request(token, "GET", contents_url(repo, path, branch))
    if not entry:
        return None, None
    content = base64.b64decode(entry.get("content", "")).decode("utf-8")
    return entry.get("sha"), content


def put_file(
    token: str,
    repo: str,
    path: str,
    branch: str,
    message: str,
    content: str,
    sha: str | None,
) -> Any:
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    return api_request(token, "PUT", contents_url(repo, path), payload)


def load_manifest(root: Path, manifest_path: str) -> dict[str, Any]:
    path = Path(manifest_path)
    if not path.is_absolute():
        path = root / path
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: 无效 JSON：{exc}") from exc
    if not isinstance(manifest.get("items"), list) or not manifest["items"]:
        raise SystemExit(f"{path}: 清单中缺少 items")
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default="docs/ai-infra/inbox-manifest.json",
        help="同步清单路径（默认 docs/ai-infra/inbox-manifest.json）",
    )
    parser.add_argument("--source-repo", help="来源仓库，默认从 git remote 推断")
    parser.add_argument("--source-branch", default="main")
    parser.add_argument("--target-repo", help="目标仓库，默认读 AI_INFRA_REPO 环境变量")
    parser.add_argument("--target-branch", default="main")
    parser.add_argument("--apply", action="store_true", help="实际写入 AI-Infra；默认只做 dry-run")
    parser.add_argument("--print-content", action="store_true", help="dry-run 时打印生成笔记的完整内容")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    manifest = load_manifest(root, args.manifest)
    inbox_dir = str(manifest["inbox_dir"]).rstrip("/")
    note_prefix = str(manifest["note_prefix"])
    source_repo = args.source_repo or resolve_source_repo(root)
    target_repo = args.target_repo or os.environ.get("AI_INFRA_REPO")

    tasks = []
    for item in manifest["items"]:
        source_path = item["source"]
        source_file = root / source_path
        if not source_file.is_file():
            raise SystemExit(f"来源文件不存在：{source_file}")
        target = item.get("target", "10_Projects/Megatron-Bridge/Notes/")
        note_name, note_content = build_inbox_note(
            source_repo,
            args.source_branch,
            source_path,
            target,
            note_prefix,
            source_file.read_text(encoding="utf-8"),
        )
        tasks.append(
            {
                "source": source_path,
                "target": target,
                "path": f"{inbox_dir}/{note_name}",
                "content": note_content,
            }
        )

    print(f"来源仓库：{source_repo}@{args.source_branch}")
    print(f"目标仓库：{target_repo or '<未设置>'}@{args.target_branch}")
    print(f"Inbox 目录：{inbox_dir}")
    print()

    for excluded in manifest.get("excluded", []):
        reason = excluded.get("reason", "")
        print(f"[排除] {excluded['source']}" + (f" —— {reason}" if reason else ""))
    if manifest.get("excluded"):
        print()

    if args.apply:
        if not target_repo:
            raise SystemExit("请通过 AI_INFRA_REPO 或 --target-repo 指定目标仓库")
        token = resolve_token()

    created = updated = unchanged = skipped = 0
    for task in tasks:
        if not args.apply:
            print(f"[dry-run] {task['source']} -> {task['path']}")
            print(f"          建议整理到：{task['target']}")
            if args.print_content:
                print("-" * 72)
                print(task["content"])
            continue

        sha, existing = get_existing(token, target_repo, task["path"], args.target_branch)
        if existing is None:
            response = put_file(
                token,
                target_repo,
                task["path"],
                args.target_branch,
                f"docs(ai-infra): inbox {task['source']}",
                task["content"],
                None,
            )
            print(f"[创建] {task['path']}（commit {response.get('commit', {}).get('sha', '?')[:8]}）")
            created += 1
        elif f"sync_source: {task['source']}" not in existing:
            print(f"[跳过] {task['path']}：不是本脚本生成的笔记，或已被手工修改，避免覆盖")
            skipped += 1
        elif existing == task["content"]:
            print(f"[不变] {task['path']}")
            unchanged += 1
        else:
            response = put_file(
                token,
                target_repo,
                task["path"],
                args.target_branch,
                f"docs(ai-infra): refresh {task['source']}",
                task["content"],
                sha,
            )
            print(f"[更新] {task['path']}（commit {response.get('commit', {}).get('sha', '?')[:8]}）")
            updated += 1

    if args.apply:
        print()
        print(f"完成：创建 {created}，更新 {updated}，不变 {unchanged}，跳过 {skipped}")
        print("在 AI-Infra 本地仓库执行 git pull 即可在 Obsidian 中看到 Inbox 笔记。")
    else:
        print()
        print(f"共 {len(tasks)} 篇待同步。确认无误后执行：python scripts/sync_ai_infra_inbox.py --apply")


if __name__ == "__main__":
    main()
