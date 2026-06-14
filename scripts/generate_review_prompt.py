#!/usr/bin/env python3
"""Generate a reusable ChatGPT memory-review prompt and email it."""

from __future__ import annotations

import os
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
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465


class PromptError(RuntimeError):
    """Raised when prompt generation or delivery cannot complete."""


@dataclass(frozen=True)
class Note:
    path: Path
    last_modified: datetime
    content: str


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


def render_recent_sources(notes: list[Note]) -> tuple[str, int]:
    blocks: list[str] = []
    truncated_count = 0

    for index, note in enumerate(notes, start=1):
        modified = note.last_modified.astimezone(timezone(timedelta(hours=8)))
        excerpt, truncated = excerpt_note(note.content)
        if truncated:
            truncated_count += 1

        blocks.append(
            "\n".join(
                [
                    f"### {index}. {note.path.as_posix()}",
                    "",
                    f"- GitHub URL: {github_blob_url(note.path)}",
                    f"- Raw URL: {github_raw_url(note.path)}",
                    f"- Last modified: {modified:%Y-%m-%d %H:%M:%S %z}",
                    "",
                    "Excerpt:",
                    "",
                    blockquote(excerpt, truncated),
                ]
            )
        )

    return "\n\n".join(blocks), truncated_count


def build_prompt(review_date: str, window_days: int, notes: list[Note]) -> str:
    recent_sources, truncated_count = render_recent_sources(notes)

    return f"""# Memory Review Prompt {review_date}

Act as my memory review coach. This is not passive summarization. Help me retrieve ideas actively, connect concepts, notice fading but important topics, generate curiosity, and identify notes worth turning into long-term knowledge.

## Context

- Date range used: last {window_days} day(s)
- Note root: `AI工作区域/`
- Source file count: {len(notes)}
- Excerpt limit: {EXCERPT_CHAR_LIMIT} characters per file
- Truncated source excerpts: {truncated_count}

## Instructions

Use the recent note sources below. Produce exactly this structure:

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

## Recent Note Sources

Use the links and excerpts below as compact source context. If a question requires more detail, inspect the GitHub URL or Raw URL for the source file.

{recent_sources}
"""


def write_prompt(prompt: str, review_date: str) -> Path:
    PROMPT_ROOT.mkdir(parents=True, exist_ok=True)
    path = PROMPT_ROOT / f"{review_date}-review-prompt.md"
    path.write_text(prompt.rstrip() + "\n", encoding="utf-8")
    log(f"Wrote prompt file: {path} ({len(prompt)} characters).")
    return path


def commit_and_push(path: Path, review_date: str) -> None:
    log("Committing prompt file if it changed.")
    run_git(["config", "user.name", "memory-prompt-bot"])
    run_git(["config", "user.email", "memory-prompt-bot@users.noreply.github.com"])
    run_git(["add", path.as_posix()])

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


def render_email_body(prompt_path: Path, review_date: str, window_days: int, notes: list[Note]) -> str:
    prompt_link = github_file_url(prompt_path)
    listed_notes = notes[:EMAIL_SOURCE_LIMIT]
    source_lines = [f"- {note.path.as_posix()}" for note in listed_notes]
    remaining = len(notes) - len(listed_notes)
    if remaining > 0:
        source_lines.append(f"- ...and {remaining} more files")

    return "\n".join(
        [
            f"Memory Review Prompt {review_date}",
            "",
            f"Date range used: last {window_days} day(s)",
            f"Prompt file: {prompt_link}",
            "",
            "Source files:",
            *source_lines,
            "",
            "Open the prompt file, copy it into ChatGPT, and continue interactive review.",
        ]
    )


def send_email(prompt_path: Path, review_date: str, window_days: int, notes: list[Note]) -> None:
    qq_email = require_env("QQ_EMAIL")
    auth_code = require_env("QQ_SMTP_AUTH_CODE")
    subject = f"Memory Review Prompt {review_date}"
    body = render_email_body(prompt_path, review_date, window_days, notes)
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
        prompt = build_prompt(review_date, window_days, notes)
        prompt_path = write_prompt(prompt, review_date)
        commit_and_push(prompt_path, review_date)
        send_email(prompt_path, review_date, window_days, notes)
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
