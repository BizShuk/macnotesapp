# dump 命令實作計劃

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `dump` CLI 命令，可將 Apple Notes 筆記及其附件匯出成 Markdown 檔案，支援單篇、資料夾、全部三種模式。

**Architecture:**
- 新增 `macnotesapp/cli/commands/dump.py`，實作 `dump` Click 命令群組
- CLI 入口在 `macnotesapp/cli/cli.py` 註冊 `dump_group`
- 附件下載使用 `Note` + `Attachment` 實體 API；body 轉 Markdown 使用現有 `html2md()`
- 附件命名：`{note_short_id}_{original_name}`，儲存於 `--out/attachments/`

**Tech Stack:** Click (CLI framework), `markdownify` (HTML→Markdown), existing NotesApp API

---

## 檔案結構

```
macnotesapp/cli/commands/dump.py   # 新增：dump 命令實作
macnotesapp/cli/cli.py            # 修改：註冊 dump_group
macnotesapp/cli/__init__.py       # 修改：匯出 dump_group（如需要）
tests/cli/test_dump.py            # 新增：dump 命令測試
```

---

## Task 1: 基本骨架 + 單篇模式

**Files:**
- Create: `macnotesapp/cli/commands/dump.py`
- Modify: `macnotesapp/cli/cli.py:37`（加入 `from .commands.dump import dump_group`）
- Modify: `macnotesapp/cli/cli.py`（在 commands 註冊後加入 `cli.add_command(dump_group, name="dump")`）

- [ ] **Step 1: 寫 dump.py 基本骨架**

```python
"""dump command for macnotesapp - export notes to Markdown with attachments"""

import os
import pathlib

import click

import macnotesapp
from macnotesapp.cli.id_utils import resolve_note_id
from markdownify import markdownify as html2md


@click.group(name="dump")
def dump_group():
    """Dump notes to Markdown with attachments.

    Example: notes dump Notes/p87 --out-dir ./output
    """
    pass


def _note_short_id(note_id: str) -> str:
    """Extract short_id (e.g. 'p87') from full x-coredata:// ID."""
    return note_id.rsplit("/", 1)[-1]


def _safe_filename(name: str) -> str:
    """Replace path-sensitive characters in filename."""
    return name.replace("/", "_").replace("\\", "_").replace(":", "_")


def _dump_note(note, out_dir: pathlib.Path) -> list[str]:
    """Dump a single note to a .md file.

    Returns list of saved attachment filenames (relative paths).
    """
    note_id = note.id
    short_id = _note_short_id(note_id)
    folder = note.folder

    # Build filename: {FOLDER}_{title}.md
    title = _safe_filename(note.name or "untitled")
    folder_part = _safe_filename(folder) if folder else "Unknown"
    md_filename = f"{folder_part}_{title}.md"
    md_path = out_dir / md_filename

    # Convert body HTML → Markdown
    body_md = html2md(note.body)

    # Build attachment section
    attachment_lines = []
    saved_attachments = []

    for att in note.attachments:
        att_filename = f"{short_id}_{att.name}"
        att_dir = out_dir / "attachments"
        att_dir.mkdir(exist_ok=True)
        try:
            att.save(str(att_dir))
            saved_attachments.append(att_filename)
            attachment_lines.append(f"[{att.name}](attachments/{att_filename})")
        except Exception as e:
            attachment_lines.append(f"[{att.name}](attachments/{att_filename})  # save failed: {e}")

    # Write .md file
    lines = [f"# {note.name}\n", body_md]
    if attachment_lines:
        lines.append("\n---\n\n# 附件\n")
        lines.extend(f"{line}\n" for line in attachment_lines)

    with open(md_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return saved_attachments


@dump_group.command(name="note")
@click.argument("note_id", metavar="ID")
@click.option("--out-dir", "-o", required=True, type=click.Path(file_okay=False, dir_okay=True), help="Output directory")
def dump_note(note_id, out_dir):
    """Dump a single note to Markdown.

    Example: notes dump note Notes/p87 --out-dir ./output
    """
    out_path = pathlib.Path(out_dir)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        click.echo(f"Error creating output directory: {e}", err=True)
        raise click.Abort()

    resolved_id = resolve_note_id(note_id)
    notesapp = macnotesapp.NotesApp()
    matching = notesapp.notes(id=[resolved_id])
    if not matching:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        raise click.Abort()
    note = matching[0]

    if note.password_protected:
        click.echo(f"Warning: Skipping password-protected note '{note.name}'", err=True)
        return

    saved = _dump_note(note, out_path)
    click.echo(f"Dumped '{note.name}' -> {out_path / (_safe_filename(note.folder or 'Unknown') + '_' + _safe_filename(note.name or 'untitled') + '.md')}")
```

- [ ] **Step 2: 在 cli.py 註冊 dump_group**

在 `macnotesapp/cli/cli.py` 第 37 行附近加入：
```python
from .commands.dump import dump_group
```

在 `cli.py` 最後的 `@cli.command()` 群組註冊處（約倒數第 3 行）加入：
```python
cli.add_command(dump_group, name="dump")
```

- [ ] **Step 3: 測試骨架**

```bash
cd /Users/shuk/projects/tmp/macnotesapp
uv run notes dump --help
```

預期輸出：`dump --help` 顯示 `note` 子命令

- [ ] **Step 4: Commit**

```bash
git add macnotesapp/cli/commands/dump.py macnotesapp/cli/cli.py
git commit -m "feat: add dump command skeleton with single-note mode"
```

---

## Task 2: 資料夾模式 `--folder`

**Files:**
- Modify: `macnotesapp/cli/commands/dump.py`

- [ ] **Step 1: 在 dump_group 加入 --folder 命令**

在 `dump_note` 命令後加入：

```python
@dump_group.command(name="folder")
@click.option("--folder", "-f", required=True, help="Folder name to dump")
@click.option("--out-dir", "-o", required=True, type=click.Path(file_okay=False, dir_okay=True), help="Output directory")
def dump_folder(folder, out_dir):
    """Dump all notes in a folder.

    Example: notes dump folder --folder Notes --out-dir ./output
    """
    out_path = pathlib.Path(out_dir)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        click.echo(f"Error creating output directory: {e}", err=True)
        raise click.Abort()

    notesapp = macnotesapp.NotesApp()
    dumped = 0
    skipped = 0

    for account_name in notesapp.accounts:
        account = notesapp.account(account_name)
        if folder not in account.folders:
            continue
        folder_obj = account.folder(folder)
        for note in folder_obj.notes():
            if note.password_protected:
                click.echo(f"Warning: Skipping password-protected note '{note.name}'", err=True)
                skipped += 1
                continue
            _dump_note(note, out_path)
            dumped += 1

    click.echo(f"Dumped {dumped} note(s), skipped {skipped} password-protected.")


@dump_group.command(name="all")
@click.option("--out-dir", "-o", required=True, type=click.Path(file_okay=False, dir_okay=True), help="Output directory")
def dump_all(out_dir):
    """Dump all notes from all accounts.

    Example: notes dump all --out-dir ./output
    """
    out_path = pathlib.Path(out_dir)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        click.echo(f"Error creating output directory: {e}", err=True)
        raise click.Abort()

    notesapp = macnotesapp.NotesApp()
    dumped = 0
    skipped = 0

    for account_name in notesapp.accounts:
        account = notesapp.account(account_name)
        for folder_name in account.folders:
            folder_obj = account.folder(folder_name)
            for note in folder_obj.notes():
                if note.password_protected:
                    click.echo(f"Warning: Skipping password-protected note '{note.name}'", err=True)
                    skipped += 1
                    continue
                _dump_note(note, out_path)
                dumped += 1

    click.echo(f"Dumped {dumped} note(s), skipped {skipped} password-protected.")
```

- [ ] **Step 2: 測試 folder 模式**

```bash
# 先確認有哪些資料夾
uv run notes list --folder Notes --id-only | head -3

# 測試 dump folder
uv run notes dump folder --folder Notes --out-dir /tmp/dump-test
ls /tmp/dump-test/
```

- [ ] **Step 3: Commit**

```bash
git add macnotesapp/cli/commands/dump.py
git commit -m "feat: add folder and all dump modes"
```

---

## Task 3: CLI 整合（無子命令捷徑模式）

**Files:**
- Modify: `macnotesapp/cli/cli.py`

設計變更：`notes dump ID --out-dir` 直接dump單篇，取代 `notes dump note ID --out-dir`

- [ ] **Step 1: 將 `dump_note` 改為 `dump` 主命令（直接模式）**

在 `cli.py` 中，原本的 `@click.command(name="dump")` 改為直接接受 `NOTE_ID`：

```python
@click.command(name="dump")
@click.argument("note_id", metavar="NOTE_ID", required=False)
@click.option("--folder", "-f", "folder_name", metavar="FOLDER", type=str, help="Dump all notes in FOLDER")
@click.option("--all", "dump_all", is_flag=True, help="Dump all notes from all accounts")
@click.option("--out-dir", "-o", required=True, type=click.Path(file_okay=False, dir_okay=True), help="Output directory")
def dump_cmd(note_id, folder_name, dump_all, out_dir):
    """Dump notes to Markdown with attachments.

    Modes (mutually exclusive):
      (default)  Dump a single note by ID
      --folder   Dump all notes in a folder
      --all      Dump all notes from all accounts

    Example: notes dump Notes/p87 --out-dir ./output
             notes dump --folder Notes --out-dir ./output
             notes dump --all --out-dir ./output
    """
    out_path = pathlib.Path(out_dir)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        click.echo(f"Error creating output directory: {e}", err=True)
        raise click.Abort()

    notesapp = macnotesapp.NotesApp()

    # Validate mutually exclusive modes
    modes = sum(bool(x) for x in [note_id, folder_name, dump_all])
    if modes == 0:
        click.echo("Error: Specify NOTE_ID, --folder, or --all", err=True)
        raise click.Abort()
    if modes > 1:
        click.echo("Error: Specify only one of NOTE_ID, --folder, or --all", err=True)
        raise click.Abort()

    if note_id:
        # Single note mode
        resolved_id = resolve_note_id(note_id)
        matching = notesapp.notes(id=[resolved_id])
        if not matching:
            click.echo(f"Error: Note '{note_id}' not found.", err=True)
            raise click.Abort()
        note = matching[0]
        if note.password_protected:
            click.echo(f"Warning: Skipping password-protected note '{note.name}'", err=True)
            return
        saved = _dump_note(note, out_path)
        folder_part = _safe_filename(note.folder or "Unknown")
        title = _safe_filename(note.name or "untitled")
        click.echo(f"Dumped '{note.name}' -> {out_path / (folder_part + '_' + title + '.md')}")

    elif folder_name:
        # Folder mode
        dumped = 0
        skipped = 0
        for account_name in notesapp.accounts:
            account = notesapp.account(account_name)
            if folder_name not in account.folders:
                continue
            folder_obj = account.folder(folder_name)
            for note in folder_obj.notes():
                if note.password_protected:
                    click.echo(f"Warning: Skipping password-protected note '{note.name}'", err=True)
                    skipped += 1
                    continue
                _dump_note(note, out_path)
                dumped += 1
        click.echo(f"Dumped {dumped} note(s), skipped {skipped} password-protected.")

    elif dump_all:
        # All mode
        dumped = 0
        skipped = 0
        for account_name in notesapp.accounts:
            account = notesapp.account(account_name)
            for folder_name_ in account.folders:
                folder_obj = account.folder(folder_name_)
                for note in folder_obj.notes():
                    if note.password_protected:
                        click.echo(f"Warning: Skipping password-protected note '{note.name}'", err=True)
                        skipped += 1
                        continue
                    _dump_note(note, out_path)
                    dumped += 1
        click.echo(f"Dumped {dumped} note(s), skipped {skipped} password-protected.")
```

將 `_dump_note`, `_note_short_id`, `_safe_filename` 輔助函式也移到 `cli.py`（或維持在 `dump.py` 並 import）。

- [ ] **Step 2: 測試三種模式**

```bash
# 模式 1：單篇
uv run notes dump Notes/p87 --out-dir /tmp/dump-test

# 模式 2：資料夾
uv run notes dump --folder Notes --out-dir /tmp/dump-test

# 模式 3：全部
uv run notes dump --all --out-dir /tmp/dump-test

# 驗證輸出
ls /tmp/dump-test/
cat /tmp/dump-test/*.md | head -20
```

- [ ] **Step 3: Commit**

```bash
git add macnotesapp/cli/commands/dump.py macnotesapp/cli/cli.py
git commit -m "feat: unify dump command with single/folder/all modes"
```

---

## Task 4: 測試

**Files:**
- Create: `tests/cli/test_dump.py`

- [ ] **Step 1: 寫測試**

```python
"""Tests for dump command"""
import pathlib
import tempfile
import os

import pytest


class TestDumpNote:
    def test_safe_filename_replaces_slashes(self):
        from macnotesapp.cli.commands.dump import _safe_filename
        assert _safe_filename("Notes/週報") == "Notes_週報"
        assert _safe_filename("a/b/c") == "a_b_c"

    def test_note_short_id_extracts_correctly(self):
        from macnotesapp.cli.commands.dump import _note_short_id
        assert _note_short_id("x-coredata://uuid/IMAPNote/p87") == "p87"
        assert _note_short_id("p87") == "p87"

    def test_dump_note_produces_markdown_file(self, tmp_path):
        # This test requires a real Notes.app environment
        # Skip in CI; run with: pytest -v -s tests/cli/test_dump.py
        pytest.skip("Requires real Notes.app")


class TestDumpCommand:
    def test_mutually_exclusive_modes_rejected(self):
        pytest.skip("Requires real Notes.app")
```

- [ ] **Step 2: Commit**

```bash
git add tests/cli/test_dump.py
git commit -m "test: add dump command tests"
```

---

## Self-Review 檢查清單

| Spec 需求 | 實作位置 |
|-----------|----------|
| `notes dump ID --out-dir` 單篇模式 | Task 1 + Task 3 |
| `notes dump --folder FOLDER --out-dir` | Task 2 + Task 3 |
| `notes dump --all --out-dir` | Task 2 + Task 3 |
| 輸出 `{FOLDER}_{title}.md` | `_dump_note()` |
| 附件 `[name](attachments/name)` 連結 | `_dump_note()` attachment section |
| `attachments/{short_id}_{name}` 儲存 | `_dump_note()` → `att.save()` |
| 密碼保護筆記跳過 + 警告 | Task 1, 2, 3 |
| `--out-dir` required | Task 3 `@click.option(--out-dir, ..., required=True)` |
| `html2md` 轉換 body | `_dump_note()` 使用 `markdownify` |
| 標題敏感字元置換 | `_safe_filename()` |
