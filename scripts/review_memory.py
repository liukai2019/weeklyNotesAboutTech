#!/usr/bin/env python3
"""Generate active-recall memory reviews from recent captured notes."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


NOTE_ROOT = Path("AI工作区域")
REVIEW_ROOT = Path("reviews")
WINDOW_DAYS = (7, 14, 30)
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
MAX_NOTE_CHARS = 60_000


class ReviewError(RuntimeError):
    """Raised when the workflow cannot generate a useful review."""


@dataclass(frozen=True)
class Note:
    path: Path
    last_modified: datetime
    content: str


def log(message: str) -> None:
    print(f"[review-memory] {message}", flush=True)


def run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ReviewError(f"Missing required environment variable: {name}")
    return value


def git_last_modified(path: Path) -> datetime | None:
    # File system mtimes in a fresh checkout are not meaningful; git history is.
    result = run_git(
        ["log", "-1", "--format=%ct", "--", path.as_posix()],
        check=False,
    )
    if result.returncode != 0:
        log(f"Could not read git history for {path}: {result.stderr.strip()}")
        return None

    stamp = result.stdout.strip()
    if not stamp:
        return None
    return datetime.fromtimestamp(int(stamp), tz=timezone.utc)


def iter_note_paths() -> Iterable[Path]:
    if not NOTE_ROOT.exists():
        return []
    return sorted(
        path
        for path in NOTE_ROOT.rglob("*.md")
        if path.is_file() and ".git" not in path.parts
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def collect_recent_notes(now: datetime) -> tuple[int, list[Note]]:
    candidates: list[Note] = []
    for path in iter_note_paths():
        modified = git_last_modified(path)
        if modified is None:
            continue

        content = read_text(path)
        if not content:
            continue
        candidates.append(Note(path=path, last_modified=modified, content=content))

    log(f"Found {len(candidates)} tracked Markdown notes under {NOTE_ROOT}.")
    # Prefer a tight recall window, but expand when the week was quiet.
    for days in WINDOW_DAYS:
        cutoff = now - timedelta(days=days)
        notes = [note for note in candidates if note.last_modified >= cutoff]
        if notes:
            log(f"Using {len(notes)} note(s) modified in the last {days} days.")
            return days, sorted(notes, key=lambda note: (note.last_modified, note.path))

    raise ReviewError(
        "No tracked, non-empty Markdown notes were modified in the last 30 days."
    )


def build_prompt(window_days: int, notes: list[Note]) -> str:
    note_blocks: list[str] = []
    used_chars = 0

    for note in notes:
        # Keep the prompt bounded so the workflow remains predictable as notes grow.
        header = (
            f"\n\n---\n"
            f"Path: {note.path.as_posix()}\n"
            f"Last modified: {note.last_modified.isoformat()}\n\n"
        )
        remaining = MAX_NOTE_CHARS - used_chars - len(header)
        if remaining <= 0:
            break

        content = note.content
        if len(content) > remaining:
            content = content[:remaining] + "\n\n[Truncated due to prompt budget.]"
        note_blocks.append(header + content)
        used_chars += len(header) + len(content)

    return f"""你正在帮助用户建立记忆复习系统，而不是简单地汇总笔记。

请利用用户最近的笔记强化记忆、触发主动回忆、连接不同日期的想法、识别值得长期保留的知识，并激发进一步探索。摘要是优先级最低的部分。

材料优先级（最高原则）：
- 人类用户的原话、提问、犹豫、直觉和未完成想法是最重要的第一手材料。即使它们朴素、拙劣、零散或尚未成熟，也要把它们视为珍贵的思考节点。
- 笔记中以“我：”“用户：”“Human:”等标识的内容，应优先于 ChatGPT、DeepSeek、Assistant 等 AI 的回复。
- AI 回复只能作为辅助材料：用于解释背景、发现关联或提出追问，不能因表达更完整、更流畅而覆盖、改写或取代用户自己的思路。
- 必须区分哪些观点来自用户、哪些来自 AI；不要把 AI 的结论误归为用户的观点。
- 主动回忆、概念连接、长期知识候选和探索问题，都应尽量从用户原话中的问题意识、困惑、判断和兴趣出发。
- 当用户原话与 AI 回复存在张力时，优先保留用户的真实问题与意图，并把这种张力作为值得继续思考的线索。

语言要求：
- 默认使用简体中文，面向中文母语、能够理解英文的读者。
- 英文原句、专业术语、代码、产品名和专有名词可以保留英文。
- 首次出现不常见的英文术语时，用简短中文解释；不要为了中文化而生硬翻译。
- 主动回忆问题和分析说明应以中文为主。

复习窗口：最近 {window_days} 天

严格按以下标题返回 Markdown：

## 1. 主动回忆问题 (Active Recall Questions)
生成 5-10 个需要主动提取记忆的问题，避免琐碎的事实性问题。优先围绕用户亲自提出的问题、判断、困惑和未完成思路。

## 2. 概念连接 (Concept Connections)
找出不同日期记录的想法之间有意义的联系，并解释这些联系为什么重要。明确指出连接源自哪些用户思考节点。

## 3. 被遗忘但重要的主题 (Forgotten But Important)
识别属于长期兴趣、但近期没有出现的主题。可考虑 eBPF、OpenSpec、Grammar Club、English Writing、Career Development、AI automation、memory systems 和 software engineering，并说明值得重温的原因。

## 4. 探索候选问题 (Exploration Candidates)
生成 3-5 个能够激发好奇心的后续问题，优先延伸用户尚未完成或仍有张力的思考。

## 5. 长期知识候选 (Long-Term Knowledge Candidates)
找出适合沉淀为永久笔记的用户思考节点。每项给出：用户原始想法或问题、建议标题、入选理由、建议目录。目录可使用 Knowledge Systems/、AI Automation/、English Writing/、Career Development/、Software Engineering/、Networking/。

## 6. 简要摘要 (Brief Summary)
最多 10 个简短要点，以中文为主。这一节将直接用于邮件正文，并应优先呈现用户自己的关注点。

最近的笔记：
{''.join(note_blocks)}
"""


def post_json(url: str, token: str | None, payload: dict, timeout: int = 120) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json" if "api.github.com" in url else "application/json",
        "Content-Type": "application/json",
        "User-Agent": "weekly-notes-memory-review",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ReviewError(f"POST {url} failed with HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ReviewError(f"POST {url} failed: {exc}") from exc


def get_json(url: str, token: str, timeout: int = 60) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "weekly-notes-memory-review",
    }
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ReviewError(f"GET {url} failed with HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ReviewError(f"GET {url} failed: {exc}") from exc


def call_deepseek(prompt: str) -> str:
    api_key = require_env("DEEPSEEK_API_KEY")
    log("Calling DeepSeek API.")
    response = post_json(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        api_key,
        {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你生成以主动回忆、概念连接、长期学习和好奇心为重点的记忆复习。"
                        "人类用户的原话和未完成思考是最高优先级，AI 回复只能作为辅助材料。"
                        "默认使用简体中文，并在有助于准确表达时保留英文术语和原文。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        },
    )

    try:
        return response["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ReviewError(f"Unexpected DeepSeek response shape: {response}") from exc


def today_shanghai() -> str:
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")


def write_review(content: str, review_date: str) -> Path:
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    review_path = REVIEW_ROOT / f"{review_date}-review.md"
    review_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    log(f"Wrote review to {review_path}.")
    return review_path


def commit_and_push(review_path: Path, review_date: str) -> bool:
    log("Committing review if it changed.")
    run_git(["config", "user.name", "memory-review-bot"])
    run_git(["config", "user.email", "memory-review-bot@users.noreply.github.com"])
    run_git(["add", review_path.as_posix()])

    diff_result = run_git(["diff", "--cached", "--quiet"], check=False)
    if diff_result.returncode == 0:
        log("No review changes to commit.")
        return False

    run_git(["commit", "-m", f"Generate memory review {review_date}"])
    run_git(["pull", "--rebase", "origin", "master"])
    run_git(["push", "origin", "HEAD:master"])
    log("Pushed review commit.")
    return True


def extract_section(markdown: str, section_number: int) -> str:
    pattern = re.compile(
        rf"^## {section_number}\. .*$([\s\S]*?)(?=^## \d+\. |\Z)",
        re.MULTILINE,
    )
    match = pattern.search(markdown)
    return match.group(1).strip() if match else ""


def top_list_items(section: str, limit: int) -> list[str]:
    items: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if re.match(r"^([-*]|\d+[.)])\s+", stripped):
            items.append(re.sub(r"^([-*]|\d+[.)])\s+", "", stripped))
        if len(items) >= limit:
            break
    return items


def issue_exists(repo: str, title: str, token: str) -> bool:
    # Idempotency: rerunning the workflow should not create duplicate reminders.
    query = urllib.parse.quote(f'repo:{repo} in:title "{title}"')
    url = f"https://api.github.com/search/issues?q={query}"
    result = get_json(url, token)
    return any(item.get("title") == title for item in result.get("items", []))


def create_issue(review_path: Path, review_date: str, markdown: str) -> None:
    token = require_env("GITHUB_TOKEN")
    repo = require_env("GITHUB_REPOSITORY")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    branch = os.environ.get("GITHUB_REF_NAME", "master")
    title = f"Memory Review {review_date}"

    if issue_exists(repo, title, token):
        log(f"Issue already exists for {review_date}; skipping duplicate notification.")
        return

    recall_items = top_list_items(extract_section(markdown, 1), 3)
    exploration_items = top_list_items(extract_section(markdown, 4), 1)
    review_url = f"{server_url}/{repo}/blob/{branch}/{urllib.parse.quote(review_path.as_posix())}"

    body_lines = [
        f"Review: [{review_path.as_posix()}]({review_url})",
        "",
        "Top recall questions:",
        *(f"- {item}" for item in recall_items or ["Review the generated file."]),
        "",
        "Top exploration question:",
        f"- {(exploration_items or ['Review the generated file.'])[0]}",
    ]

    post_json(
        f"https://api.github.com/repos/{repo}/issues",
        token,
        {"title": title, "body": "\n".join(body_lines)},
        timeout=60,
    )
    log(f"Created GitHub issue: {title}")


def main() -> int:
    try:
        now = datetime.now(timezone.utc)
        review_date = today_shanghai()
        window_days, notes = collect_recent_notes(now)
        prompt = build_prompt(window_days, notes)
        review = call_deepseek(prompt)
        review_path = write_review(review, review_date)
        commit_and_push(review_path, review_date)
        create_issue(review_path, review_date, review)
        return 0
    except ReviewError as exc:
        log(f"ERROR: {exc}")
        return 1
    except subprocess.CalledProcessError as exc:
        log(f"ERROR: git command failed: {' '.join(exc.cmd)}")
        log(f"stdout: {exc.stdout.strip()}")
        log(f"stderr: {exc.stderr.strip()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
