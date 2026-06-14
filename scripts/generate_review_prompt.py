#!/usr/bin/env python3
"""Generate a reusable ChatGPT memory-review prompt and email it."""

from __future__ import annotations

import os
import re
import smtplib
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Iterable


NOTE_ROOT = Path("AI工作区域")
PROMPT_ROOT = Path("review-prompts")
WINDOW_DAYS = (7, 14, 30)
EXCERPT_CHAR_LIMIT = 500
EMAIL_SOURCE_LIMIT = 5
PROMPT_TARGET_CHARS = 30_000
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
HUMAN_PREFIXES = (
    "我",
    "user",
    "human",
    "q",
    "question",
    "prompt",
    "提问",
    "用户",
    "访客",
    "me",
)
AI_PREFIXES = (
    "ai",
    "assistant",
    "chatgpt",
    "claude",
    "grok",
    "copilot",
    "codex",
    "answer",
    "回答",
    "回复",
    "bot",
)


class PromptError(RuntimeError):
    """Raised when prompt generation or delivery cannot complete."""


@dataclass(frozen=True)
class Note:
    path: Path
    last_modified: datetime
    content: str


@dataclass(frozen=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True)
class SourceInfo:
    note: Note
    file_size: int
    first_heading: str | None
    human_messages: list[str]
    ai_message_count: int


def log(message: str) -> None:
    print(f"[generate-review-prompt] {message}", flush=True)


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
        raise PromptError(f"Missing required environment variable: {name}")
    return value


def shanghai_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


def git_last_modified(path: Path) -> datetime | None:
    # Fresh checkout mtimes are not useful; use git history to detect recent notes.
    result = run_git(
        ["log", "-1", "--format=%ct", "--", path.as_posix()],
        check=False,
    )
    if result.returncode != 0:
        log(f"Could not inspect git history for {path}: {result.stderr.strip()}")
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


def read_note(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def collect_recent_notes(now_utc: datetime) -> tuple[int, list[Note]]:
    candidates: list[Note] = []
    for path in iter_note_paths():
        modified = git_last_modified(path)
        if modified is None:
            continue

        content = read_note(path)
        if content:
            candidates.append(Note(path=path, last_modified=modified, content=content))

    log(f"Found {len(candidates)} tracked non-empty Markdown note(s).")
    for days in WINDOW_DAYS:
        cutoff = now_utc - timedelta(days=days)
        notes = [note for note in candidates if note.last_modified >= cutoff]
        if notes:
            notes = sorted(notes, key=lambda note: (note.last_modified, note.path))
            log(f"Using {len(notes)} note(s) modified in the last {days} days.")
            return days, notes

    raise PromptError("No tracked non-empty Markdown notes were modified in 30 days.")


def normalize_prefix(prefix: str) -> str:
    return prefix.strip().casefold()


def detect_role(line: str) -> tuple[str | None, str | None]:
    stripped = line.strip()
    if not stripped:
        return None, None

    match = re.match(r"^([A-Za-z]+|[\u4e00-\u9fff]{1,4})\s*[:：]\s*(.*)$", stripped)
    if not match:
        return None, None

    prefix = normalize_prefix(match.group(1))
    remainder = match.group(2)
    if prefix in HUMAN_PREFIXES:
        return "human", remainder
    if prefix in AI_PREFIXES:
        return "ai", remainder
    return None, None


def extract_messages(content: str) -> list[Message]:
    messages: list[Message] = []
    current_role: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_role, current_lines
        if current_role is not None:
            text = "\n".join(current_lines).strip()
            if text:
                messages.append(Message(current_role, text))
        current_role = None
        current_lines = []

    for line in content.splitlines():
        role, remainder = detect_role(line)
        if role is not None:
            flush()
            current_role = role
            current_lines = [remainder] if remainder else []
            continue

        if current_role is not None:
            current_lines.append(line)

    flush()
    return messages


def first_heading(content: str) -> str | None:
    for line in content.splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return None


def build_source_infos(notes: list[Note]) -> list[SourceInfo]:
    infos: list[SourceInfo] = []
    for note in notes:
        messages = extract_messages(note.content)
        human_messages = [message.content for message in messages if message.role == "human"]
        ai_message_count = sum(1 for message in messages if message.role == "ai")
        infos.append(
            SourceInfo(
                note=note,
                file_size=file_size(note.path),
                first_heading=first_heading(note.content),
                human_messages=human_messages,
                ai_message_count=ai_message_count,
            )
        )
    return infos


def github_blob_url(path: Path) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "liukai2019/weeklyNotesAboutTech")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    branch = os.environ.get("GITHUB_REF_NAME", "master")
    return f"{server_url}/{repo}/blob/{branch}/{path.as_posix()}"


def github_raw_url(path: Path) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "liukai2019/weeklyNotesAboutTech")
    branch = os.environ.get("GITHUB_REF_NAME", "master")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path.as_posix()}"


def excerpt_note(content: str) -> tuple[str, bool]:
    compact = content.strip()
    if len(compact) <= EXCERPT_CHAR_LIMIT:
        return compact, False

    return compact[:EXCERPT_CHAR_LIMIT].rstrip(), True


def blockquote(text: str, truncated: bool) -> str:
    lines = text.splitlines() or [""]
    if truncated:
        lines.append("[truncated]")
    return "\n".join(f"> {line}" if line else ">" for line in lines)


def format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    return f"{num_bytes / 1024:.1f} KB"


def render_recent_sources(infos: list[SourceInfo], include_excerpts: bool) -> tuple[str, int]:
    blocks: list[str] = []
    truncated_count = 0

    for index, info in enumerate(infos, start=1):
        note = info.note
        modified = note.last_modified.astimezone(timezone(timedelta(hours=8)))
        excerpt_block = "> [excerpt omitted due to prompt budget]"
        if include_excerpts:
            excerpt, truncated = excerpt_note(note.content)
            if truncated:
                truncated_count += 1
            excerpt_block = blockquote(excerpt, truncated)

        blocks.append(
            "\n".join(
                [
                    f"### {index}. {note.path.as_posix()}",
                    "",
                    f"- GitHub URL: {github_blob_url(note.path)}",
                    f"- Raw URL: {github_raw_url(note.path)}",
                    f"- Last modified: {modified:%Y-%m-%d %H:%M:%S %z}",
                    f"- File size: {format_size(info.file_size)}",
                    f"- First heading: {info.first_heading or 'None detected'}",
                    "- Conversation stats:",
                    f"  - Human messages: {len(info.human_messages)}",
                    f"  - AI messages: {info.ai_message_count}",
                    "",
                    "Excerpt:",
                    "",
                    excerpt_block,
                ]
            )
        )

    return "\n\n".join(blocks), truncated_count


def render_human_messages(infos: list[SourceInfo]) -> str:
    blocks: list[str] = []
    for info in infos:
        if not info.human_messages:
            continue
        lines = [f"### {info.note.path.as_posix()}"]
        for index, message in enumerate(info.human_messages, start=1):
            lines.extend(["", f"#### Human Message {index}", "", message])
        blocks.append("\n".join(lines))

    if not blocks:
        return "No explicit human messages were detected from known prefixes."
    return "\n\n".join(blocks)


def prompt_header(review_date: str, window_days: int, infos: list[SourceInfo], truncated_count: int) -> str:
    total_human_messages = sum(len(info.human_messages) for info in infos)
    total_ai_messages = sum(info.ai_message_count for info in infos)
    files_with_human_messages = sum(1 for info in infos if info.human_messages)

    return f"""# Memory Review Prompt {review_date}

Act as my memory review coach. This is not passive summarization. Help me retrieve ideas actively, connect concepts, notice fading but important topics, generate curiosity, and identify notes worth turning into long-term knowledge.

## Context

- Date range used: last {window_days} day(s)
- Note root: `AI工作区域/`
- Source file count: {len(infos)}
- Files with human messages: {files_with_human_messages}
- Total human messages: {total_human_messages}
- Total AI messages: {total_ai_messages}
- Excerpt limit: {EXCERPT_CHAR_LIMIT} characters per file
- Truncated source excerpts: {truncated_count}

## Instructions

Use the detected human messages and recent note sources below. Human messages are highest priority and are included in full when detected. Produce exactly this structure:

## 1. Active Recall Questions

Generate 5-10 retrieval-based questions. Require reasoning, tradeoffs, causality, or implementation details. Avoid trivial factual questions.

## 2. Concept Connections

Identify meaningful links between different notes or themes, and explain why each matters.

## 3. Forgotten But Important

Identify topics related to long-term interests that have not appeared recently or deserve renewed attention. Interests may include eBPF, Networking, OpenSpec, AI automation, GitHub Actions, iOS Shortcut, Grammar Club, English writing, Career development, and Health and fitness.

## 4. Exploration Candidates

Generate 3-5 curiosity-oriented follow-up questions.

## 5. Long-Term Knowledge Candidates

Identify notes that should become permanent notes. For each candidate provide title, reason, and suggested destination. Possible destinations: Knowledge Systems/, AI Automation/, English Writing/, Career Development/, Software Engineering/, Networking/, Health/.

## 6. Brief Summary

Maximum 10 bullet points. Summary is the lowest-priority output.
"""


def build_prompt(review_date: str, window_days: int, notes: list[Note]) -> tuple[str, list[SourceInfo]]:
    infos = build_source_infos(notes)
    recent_sources, truncated_count = render_recent_sources(infos, include_excerpts=True)
    human_messages = render_human_messages(infos)
    prompt = f"""{prompt_header(review_date, window_days, infos, truncated_count)}

## Detected Human Messages

{human_messages}

## Recent Note Sources

Use the links and excerpts below as compact source context. If a question requires more detail, inspect the GitHub URL or Raw URL for the source file.

{recent_sources}
"""

    if len(prompt) <= PROMPT_TARGET_CHARS:
        return prompt, infos

    log(
        "Prompt exceeded target size with excerpts; preserving all human messages "
        "and omitting general excerpts."
    )
    recent_sources, truncated_count = render_recent_sources(infos, include_excerpts=False)
    prompt = f"""{prompt_header(review_date, window_days, infos, truncated_count)}

## Prompt Size Note

The prompt exceeded the target size because all detected human messages are preserved. General source excerpts were omitted, but source metadata and links remain.

## Detected Human Messages

{human_messages}

## Recent Note Sources

Use the links below as compact source context. If a question requires more detail, inspect the GitHub URL or Raw URL for the source file.

{recent_sources}
"""
    return prompt, infos


def write_prompt(prompt: str, review_date: str) -> tuple[Path, Path]:
    PROMPT_ROOT.mkdir(parents=True, exist_ok=True)
    path = PROMPT_ROOT / f"{review_date}-review-prompt.md"
    latest_path = PROMPT_ROOT / "latest.md"
    content = prompt.rstrip() + "\n"
    path.write_text(content, encoding="utf-8")
    latest_path.write_text(content, encoding="utf-8")
    log(f"Wrote prompt file: {path} ({len(prompt)} characters).")
    log(f"Wrote latest prompt file: {latest_path}.")
    return path, latest_path


def commit_and_push(paths: list[Path], review_date: str) -> None:
    log("Committing prompt file if it changed.")
    run_git(["config", "user.name", "memory-prompt-bot"])
    run_git(["config", "user.email", "memory-prompt-bot@users.noreply.github.com"])
    run_git(["add", *[path.as_posix() for path in paths]])

    unchanged = run_git(["diff", "--cached", "--quiet"], check=False).returncode == 0
    if unchanged:
        log("Prompt file is unchanged; skipping commit.")
        return

    run_git(["commit", "-m", f"Generate review prompt {review_date}"])
    run_git(["pull", "--rebase", "origin", "master"])
    run_git(["push", "origin", "HEAD:master"])
    log("Pushed prompt commit.")


def github_file_url(path: Path) -> str:
    return github_blob_url(path)


def raw_github_file_url(path: Path) -> str:
    return github_raw_url(path)


def render_email_body(
    prompt_path: Path,
    latest_path: Path,
    review_date: str,
    window_days: int,
    infos: list[SourceInfo],
) -> str:
    prompt_link = github_file_url(prompt_path)
    latest_link = github_file_url(latest_path)
    listed_infos = infos[:EMAIL_SOURCE_LIMIT]
    source_lines = [f"- {info.note.path.as_posix()}" for info in listed_infos]
    remaining = len(infos) - len(listed_infos)
    if remaining > 0:
        source_lines.append(f"- ...and {remaining} more files")
    files_with_human_messages = sum(1 for info in infos if info.human_messages)
    total_human_messages = sum(len(info.human_messages) for info in infos)

    return "\n".join(
        [
            f"Memory Review Prompt {review_date}",
            "",
            f"Date range used: last {window_days} day(s)",
            f"Prompt file: {prompt_link}",
            f"Latest prompt: {latest_link}",
            f"Source file count: {len(infos)}",
            f"Files with human messages: {files_with_human_messages}",
            f"Total human messages: {total_human_messages}",
            "",
            "Source files:",
            *source_lines,
            "",
            "Open latest.md, copy it into ChatGPT, and continue interactive review.",
        ]
    )


def send_email(
    prompt_path: Path,
    latest_path: Path,
    review_date: str,
    window_days: int,
    infos: list[SourceInfo],
) -> None:
    qq_email = require_env("QQ_EMAIL")
    auth_code = require_env("QQ_SMTP_AUTH_CODE")
    subject = f"Memory Review Prompt {review_date}"
    body = render_email_body(prompt_path, latest_path, review_date, window_days, infos)
    log(f"Email body size: {len(body)} characters.")

    message = MIMEText(body, "plain", "utf-8")
    message["From"] = qq_email
    message["To"] = qq_email
    message["Subject"] = subject

    log("Sending QQ email notification.")
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=60) as smtp:
            smtp.login(qq_email, auth_code)
            smtp.sendmail(qq_email, [qq_email], message.as_string())
    except smtplib.SMTPException as exc:
        raise PromptError(f"Failed to send QQ email through SMTP: {exc}") from exc
    except OSError as exc:
        raise PromptError(f"Failed to connect to QQ SMTP server: {exc}") from exc

    log("QQ email notification sent.")


def main() -> int:
    try:
        review_date = shanghai_now().strftime("%Y-%m-%d")
        window_days, notes = collect_recent_notes(datetime.now(timezone.utc))
        prompt, infos = build_prompt(review_date, window_days, notes)
        total_human_messages = sum(len(info.human_messages) for info in infos)
        if total_human_messages:
            log(f"Detected {total_human_messages} human message(s); preserving all in full.")
        else:
            log("No explicit human messages were detected from known prefixes.")
        prompt_path, latest_path = write_prompt(prompt, review_date)
        commit_and_push([prompt_path, latest_path], review_date)
        send_email(prompt_path, latest_path, review_date, window_days, infos)
        return 0
    except PromptError as exc:
        log(f"ERROR: {exc}")
        return 1
    except subprocess.CalledProcessError as exc:
        log(f"ERROR: git command failed: {' '.join(exc.cmd)}")
        if exc.stdout:
            log(f"stdout: {exc.stdout.strip()}")
        if exc.stderr:
            log(f"stderr: {exc.stderr.strip()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
