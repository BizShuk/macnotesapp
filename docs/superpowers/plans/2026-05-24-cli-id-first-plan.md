# macnotesapp CLI ID-first Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重構 CLI 為 ID-first 架構，所有寫入命令使用 Note ID 操作

**Architecture:** CLI 重構分為三階段：(1) 新增 `get`/`selected`/`attach`/`app` 命令，(2) 重構 `list`/`rename`/`edit`/`delete`/`move` 為 ID-based，(3) 移除舊命令 `cat`/`dump`。輸出格式統一支援 human-readable / JSON / id-only 三種模式。

**Tech Stack:** click (CLI framework), macnotesapp core library, ScriptingBridge/AppleScript

---

## 階段一：新增命令（讀取 + 附屬功能）

### Task 1: 新增 `get` 命令

**Files:**
- Modify: `macnotesapp/cli/cli.py:540-570`（cli_main add_command 區段）

- [ ] **Step 1: 新增 get_note command**

在 cli.py 尾端（約 line 540 前）新增：

```python
@click.command(name="get")
@click.argument("note_id", metavar="ID")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["html", "plaintext", "markdown", "json"]),
    default="markdown",
    help="Output format (default: markdown)",
)
@click.option("--show", "-s", is_flag=True, help="Show note in Notes.app after getting.")
def get_note(note_id, output_format, show):
    """Get note content by ID.

    Example: notes get x-coredata://.../IMAPNote/p87 --format markdown
    """
    notesapp = macnotesapp.NotesApp()
    matching_notes = notesapp.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]

    if output_format == "json":
        import json
        note_data = note.asdict()
        note_data["creation_date"] = note_data["creation_date"].isoformat()
        note_data["modification_date"] = note_data["modification_date"].isoformat()
        print(json.dumps(note_data, indent=2))
    else:
        from .click_rich_echo import console
        from markdownify import markdownify as html2md
        if output_format == "html":
            print(note.body)
        elif output_format == "plaintext":
            print(note.plaintext)
        else:  # markdown
            console.print(Markdown(html2md(note.body)))

    if show:
        note.show()
```

- [ ] **Step 2: 將 get_note 加入 cli_main**

在 `cli_main.add_command(command)` 迴圈中加入：
```python
for command in [accounts, add_note, cat_notes, config, list_notes, dump, help,
                rename_note, delete_note, edit_note, move_note, make_folder, remove_folder,
                get_note]:  # 新增 get_note
    cli_main.add_command(command)
```

- [ ] **Step 3: Commit**
```bash
git add macnotesapp/cli/cli.py
git commit -m "feat: add get command for ID-based note retrieval"
```

---

### Task 2: 新增 `selected` 命令

**Files:**
- Modify: `macnotesapp/cli/cli.py:540-570`

- [ ] **Step 1: 新增 selected command**

在 get_note 之後新增：

```python
@click.command(name="selected")
@click.option("--json", "-j", "json_", is_flag=True, help="Output as JSON.")
@click.option("--id-only", "-i", is_flag=True, help="Output only the note ID.")
def selected_notes(json_, id_only):
    """Get the note currently selected in Notes.app UI.

    Example: notes selected --json
    """
    notesapp = macnotesapp.NotesApp()
    notes = notesapp.selection
    if not notes:
        click.echo("No note selected.", err=True)
        sys.exit(1)

    if id_only:
        for note in notes:
            print(note.id)
    elif json_:
        import json
        notes_list = []
        for note in notes:
            note_data = note.asdict()
            note_data["creation_date"] = note_data["creation_date"].isoformat()
            note_data["modification_date"] = note_data["modification_date"].isoformat()
            notes_list.append(note_data)
        print(json.dumps(notes_list, indent=2))
    else:
        # Default: human-readable, one line per note
        for note in notes:
            print(f"{note.id}\t{note.account}/{note.folder}\t{note.name}")
```

- [ ] **Step 2: 將 selected_notes 加入 cli_main**

- [ ] **Step 3: Commit**
```bash
git add macnotesapp/cli/cli.py
git commit -m "feat: add selected command"
```

---

### Task 3: 新增 `attach` 子命令群

**Files:**
- Modify: `macnotesapp/cli/cli.py:540-570`
- Create: `macnotesapp/cli/commands/attach.py`（新檔案）

- [ ] **Step 1: Create attach.py**

```python
"""Attach subcommand for managing note attachments"""

import click
import json


@click.group(name="attach")
def attach_group():
    """Manage note attachments."""
    pass


@attach_group.command(name="list")
@click.argument("note_id", metavar="ID")
@click.option("--json", "-j", "json_", is_flag=True, help="Output as JSON.")
def attach_list(note_id, json_):
    """List attachments for a note.

    Example: notes attach list x-coredata://.../IMAPNote/p87
    """
    notesapp = macnotesapp.NotesApp()
    matching_notes = notesapp.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]
    attachments = note.attachments

    if json_:
        attachments_data = [
            {
                "id": att.id,
                "name": att.name,
                "modification_date": att.modification_date.isoformat(),
                "content_identifier": att.content_identifier,
                "url": att.URL,
            }
            for att in attachments
        ]
        print(json.dumps(attachments_data, indent=2))
    else:
        # Human-readable output: ATTACHMENT_ID  NAME  MOD_DATE  [URL]
        for att in attachments:
            url_part = f"  {att.URL}" if att.URL else ""
            print(f"{att.id}  {att.name}  {att.modification_date.isoformat()}{url_part}")


@attach_group.command(name="add")
@click.argument("note_id", metavar="ID")
@click.argument("file_path", metavar="FILE", type=click.Path(exists=True))
@click.option("--json", "-j", "json_", is_flag=True, help="Output as JSON.")
def attach_add(note_id, file_path, json_):
    """Add attachment to a note.

    Example: notes attach add x-coredata://.../IMAPNote/p87 /path/to/file.jpg
    """
    notesapp = macnotesapp.NotesApp()
    matching_notes = notesapp.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]
    try:
        attachment = note.add_attachment(file_path)
        if json_:
            print(json.dumps({
                "id": attachment.id,
                "name": attachment.name,
                "modification_date": attachment.modification_date.isoformat(),
            }, indent=2))
        else:
            print(attachment.id)
    except Exception as e:
        click.echo(f"Error adding attachment: {e}", err=True)
        sys.exit(1)


@attach_group.command(name="save")
@click.argument("note_id", metavar="ID")
@click.argument("attachment_id", metavar="ATTACHMENT_ID")
@click.option("--out-dir", "-o", required=True, help="Output directory.", type=click.Path(file_okay=False, dir_okay=True))
def attach_save(note_id, attachment_id, out_dir):
    """Save attachment to a directory.

    Example: notes attach save x-coredata://.../IMAPNote/p87 x-coredata://.../ICAttachment/p5631 --out-dir ./downloads
    """
    notesapp = macnotesapp.NotesApp()
    matching_notes = notesapp.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]

    attachment = None
    for att in note.attachments:
        if att.id == attachment_id:
            attachment = att
            break

    if not attachment:
        click.echo(f"Error: Attachment '{attachment_id}' not found.", err=True)
        sys.exit(1)

    try:
        saved_path = attachment.save(out_dir)
        click.echo(f"Saved to: {saved_path}")
    except Exception as e:
        click.echo(f"Error saving attachment: {e}", err=True)
        sys.exit(1)
```

- [ ] **Step 2: Import attach_group in cli.py and add to cli_main**

在 cli.py 開頭 import 區段（約 line 31 後）新增：
```python
from .commands.attach import attach_group
```

在 add_command 迴圈中新增：
```python
cli_main.add_command(attach_group)
```

- [ ] **Step 3: Commit**
```bash
git add macnotesapp/cli/commands/attach.py macnotesapp/cli/cli.py
git commit -m "feat: add attach subcommand (list, add, save)"
```

---

### Task 4: 新增 `app` 子命令群

**Files:**
- Create: `macnotesapp/cli/commands/app.py`

- [ ] **Step 1: Create app.py**

```python
"""App subcommand for Notes.app control"""

import click
from macnotesapp import __version__


@click.group(name="app")
def app_group():
    """Control Notes.app."""
    pass


@app_group.command(name="activate")
def app_activate():
    """Activate (bring to front) Notes.app.

    Example: notes app activate
    """
    notesapp = macnotesapp.NotesApp()
    notesapp.activate()
    click.echo("Notes.app activated.")


@app_group.command(name="quit")
def app_quit():
    """Quit Notes.app.

    Example: notes app quit
    """
    notesapp = macnotesapp.NotesApp()
    notesapp.quit()
    click.echo("Notes.app quit.")


@app_group.command(name="version")
def app_version():
    """Show Notes.app version.

    Example: notes app version
    """
    notesapp = macnotesapp.NotesApp()
    version = notesapp.version
    click.echo(f"Notes.app version: {version}")
```

- [ ] **Step 2: Import app_group in cli.py and add to cli_main**

```python
from .commands.app import app_group
# ...
cli_main.add_command(app_group)
```

- [ ] **Step 3: Commit**
```bash
git add macnotesapp/cli/commands/app.py macnotesapp/cli/cli.py
git commit -m "feat: add app subcommand (activate, quit, version)"
```

---

## 階段二：重構現有命令（ID-based）

### Task 5: 重構 `list` 命令

**Files:**
- Modify: `macnotesapp/cli/cli.py:204-233`

- [ ] **Step 1: 重寫 list_notes command**

將原本的：
```python
@click.command(name="list")
@click.option("--account", "-a", "account_name", metavar="ACCOUNT", multiple=True, type=str, ...)
@click.argument("text", metavar="TEXT", required=False)
def list_notes(account_name, text):
    """List notes, optionally filtering by account or text."""
```

重構為：
```python
def truncate_id(note_id: str) -> str:
    """Truncate ID for display: .../IMAPNote/p87"""
    if note_id and note_id.startswith("x-coredata://"):
        # Extract entity type and record number
        parts = note_id.split("/")
        if len(parts) >= 3:
            return f".../{parts[-2]}/{parts[-1]}"
    return note_id


@click.command(name="list")
@click.option("--name", "-n", "name_filter", metavar="TEXT", type=str, help="Filter by name containing TEXT")
@click.option("--body", "-b", "body_filter", metavar="TEXT", type=str, help="Filter by body containing TEXT")
@click.option("--text", "-t", "text_filter", metavar="TEXT", type=str, help="Filter by name or body containing TEXT")
@click.option("--account", "-a", "account_name", metavar="ACCOUNT", multiple=True, type=str, help="Filter by account (can repeat)")
@click.option("--folder", "-f", "folder_name", metavar="FOLDER", multiple=True, type=str, help="Filter by folder (can repeat)")
@click.option("--password-protected", "-p", is_flag=True, help="Show only password-protected notes")
@click.option("--json", "-j", "json_", is_flag=True, help="Output as JSON")
@click.option("--id-only", "-i", is_flag=True, help="Output only note IDs (one per line)")
def list_notes(name_filter, body_filter, text_filter, account_name, folder_name, password_protected, json_, id_only):
    """List notes with optional filters.

    Example: notes list --name "週報" --account iCloud
    """
    notesapp = macnotesapp.NotesApp()

    noteslist = notesapp.noteslist(
        name=[name_filter] if name_filter else None,
        body=[body_filter] if body_filter else None,
        text=[text_filter] if text_filter else None,
        accounts=[list(account_name)] if account_name else None,
        password_protected=password_protected if password_protected else None,
    )

    if id_only:
        for nid in noteslist.id:
            print(nid)
        return

    if json_:
        import json
        notes_data = []
        for i in range(len(noteslist)):
            notes_data.append({
                "id": noteslist.id[i],
                "name": noteslist.name[i],
                "account": noteslist.folder[i].split("/")[0] if noteslist.folder[i] else None,
                "folder": noteslist.folder[i].split("/")[-1] if noteslist.folder[i] else None,
                "creation_date": noteslist.creation_date[i].isoformat(),
                "modification_date": noteslist.modification_date[i].isoformat(),
                "password_protected": noteslist.password_protected[i],
            })
        print(json.dumps(notes_data, indent=2))
        return

    # Human-readable output: ID  ACCOUNT/FOLDER  NAME  MOD_DATE  PWD
    console = Console()
    id_width = 25
    folder_width = 20
    name_width = 30
    date_width = 20
    pwd_width = 5
    header = f"{'ID':<{id_width}} {'ACCOUNT/FOLDER':<{folder_width}} {'NAME':<{name_width}} {'MOD_DATE':<{date_width}} {'PWD':<{pwd_width}}"
    print(header)
    for i in range(len(noteslist)):
        note_id = truncate_id(noteslist.id[i])
        folder = noteslist.folder[i] or "---"
        name = noteslist.name[i] or "---"
        mod_date = noteslist.modification_date[i].strftime("%Y-%m-%dT%H:%M") if noteslist.modification_date[i] else "---"
        pwd = "🔒" if noteslist.password_protected[i] else "-"
        # Truncate long names
        if len(name) > name_width - 2:
            name = name[:name_width-2] + ".."
        print(f"{note_id:<{id_width}} {folder:<{folder_width}} {name:<{name_width}} {mod_date:<{date_width}} {pwd}")
```

- [ ] **Step 2: Add Console import at top of file**

確認 from rich.console import Console 在 import 區段。

- [ ] **Step 3: Commit**
```bash
git add macnotesapp/cli/cli.py
git commit -m "refactor: rewrite list command with ID-first output and filters"
```

---

### Task 6: 重構 `rename` 命令（ID-based）

**Files:**
- Modify: `macnotesapp/cli/cli.py:339-363`

- [ ] **Step 1: 重構 rename_note command**

將：
```python
@click.command(name="rename")
@click.argument("old_name", metavar="OLD_NAME")
@click.argument("new_name", metavar="NEW_NAME")
@click.option("--account", "-a", "account_name", metavar="ACCOUNT", type=str, help="Account to search in.")
def rename_note(old_name, new_name, account_name):
```

改為：
```python
@click.command(name="rename")
@click.argument("note_id", metavar="ID")
@click.argument("new_name", metavar="NEW_NAME")
def rename_note(note_id, new_name):
    """Rename a note by ID.

    Example: notes rename x-coredata://.../IMAPNote/p87 "New Title"
    """
    notes_app = macnotesapp.NotesApp()
    matching_notes = notes_app.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]
    old_name = note.name
    note.name = new_name
    click.echo(f"Renamed '{old_name}' -> '{new_name}'")
```

- [ ] **Step 2: Commit**
```bash
git add macnotesapp/cli/cli.py
git commit -m "refactor: rename command uses ID instead of name"
```

---

### Task 7: 重構 `delete` 命令（ID-based）

**Files:**
- Modify: `macnotesapp/cli/cli.py:366-393`

- [ ] **Step 1: 重構 delete_note command**

改為：
```python
@click.command(name="delete")
@click.argument("note_id", metavar="ID")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def delete_note(note_id, yes):
    """Delete a note by ID.

    Example: notes delete x-coredata://.../IMAPNote/p87 --yes
    """
    notes_app = macnotesapp.NotesApp()
    matching_notes = notes_app.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]
    if not yes:
        if not click.confirm(f"Delete '{note.name}'?"):
            click.echo("Aborted.")
            sys.exit(0)
    note.delete()
    click.echo(f"Deleted '{note.name}'")
```

- [ ] **Step 2: Commit**
```bash
git add macnotesapp/cli/cli.py
git commit -m "refactor: delete command uses ID instead of name"
```

---

### Task 8: 重構 `edit` 命令（ID-based）

**Files:**
- Modify: `macnotesapp/cli/cli.py:396-459`

- [ ] **Step 1: 重構 edit_note command**

改為：
```python
@click.command(name="edit")
@click.argument("note_id", metavar="ID")
@click.option("--body", "-b", help="Set body directly without opening editor.")
@click.option("--html", "-h", "use_html", is_flag=True, help="Treat body as HTML.")
@click.option("--markdown", "-m", "use_markdown", is_flag=True, help="Treat body as Markdown.")
def edit_note(note_id, body, use_html, use_markdown):
    """Edit a note's body by ID.

    Example: notes edit x-coredata://.../IMAPNote/p87 --body "New content"
    """
    notes_app = macnotesapp.NotesApp()
    matching_notes = notes_app.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]
    original_name = note.name

    if body:
        if use_markdown:
            body = markdown2.markdown(body, extras=MARKDOWN_EXTRAS)
        elif not use_html:
            body = f"<div>{body}</div>"
        note.body = body
        click.echo(f"Updated '{original_name}'")
    else:
        # Open in editor with markdown
        import tempfile
        config = ConfigSettings()
        settings = config.read()
        editor = settings.get("editor", DEFAULT_EDITOR)
        if editor.startswith("$"):
            editor = os.environ.get(editor[1:], "vim")

        current_md = html2md(note.body)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(current_md)
            temp_path = f.name

        result = os.system(f'{editor} "{temp_path}"')
        if result != 0:
            click.echo(f"Editor exited with error code {result}", err=True)
            os.unlink(temp_path)
            sys.exit(1)

        with open(temp_path, "r") as f:
            new_content = f.read()

        new_html = markdown2.markdown(new_content, extras=MARKDOWN_EXTRAS)
        note.body = new_html
        os.unlink(temp_path)
        click.echo(f"Updated '{note.name}'")
```

- [ ] **Step 2: Commit**
```bash
git add macnotesapp/cli/cli.py
git commit -m "refactor: edit command uses ID instead of name"
```

---

### Task 9: 重構 `move` 命令（ID-based）

**Files:**
- Modify: `macnotesapp/cli/cli.py:462-486`

- [ ] **Step 1: 重構 move_note command**

改為：
```python
@click.command(name="move")
@click.argument("note_id", metavar="ID")
@click.option("--folder", "-f", required=True, help="Destination folder.")
def move_note(note_id, folder):
    """Move a note to a different folder by ID.

    Example: notes move x-coredata://.../IMAPNote/p87 --folder Archive
    """
    notes_app = macnotesapp.NotesApp()
    matching_notes = notes_app.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]
    old_folder = note.folder
    note.move(folder)
    click.echo(f"Moved '{note.name}' from '{old_folder}' to '{folder}'")
```

- [ ] **Step 2: Commit**
```bash
git add macnotesapp/cli/cli.py
git commit -m "refactor: move command uses ID instead of name"
```

---

### Task 10: 修改 `add` 命令輸出（預設輸出 ID）

**Files:**
- Modify: `macnotesapp/cli/cli.py:55-201`

- [ ] **Step 1: 修改 add_note 預設輸出**

在 add_note 函數中，找到：
```python
new_note = account.make_note(name, body, folder_name)
if show:
    new_note.show()
```

改為：
```python
new_note = account.make_note(name, body, folder_name)
# Default: output new note ID to stdout
print(new_note.id)
if show:
    new_note.show()
```

並新增 `--json` option（預設輸出 ID）：
```python
@click.option("--json", "-j", "json_", is_flag=True, help="Output as JSON.")
```
在函數簽名中加入 `json_` 參數。

在 return 前新增：
```python
if json_:
    note_data = new_note.asdict()
    note_data["creation_date"] = note_data["creation_date"].isoformat()
    note_data["modification_date"] = note_data["modification_date"].isoformat()
    print(json.dumps(note_data, indent=2))
```

- [ ] **Step 2: Commit**
```bash
git add macnotesapp/cli/cli.py
git commit -m "feat: add command outputs note ID by default, --json for full data"
```

---

## 階段三：移除舊命令

### Task 11: 移除 `cat` 和 `dump` 命令

**Files:**
- Modify: `macnotesapp/cli/cli.py`

- [ ] **Step 1: 從 add_command 迴圈移除 cat_notes 和 dump**

將：
```python
for command in [accounts, add_note, cat_notes, config, list_notes, dump, help,
                rename_note, delete_note, edit_note, move_note, make_folder, remove_folder,
                get_note, selected_notes, attach_group, app_group]:
```

改為：
```python
for command in [accounts, add_note, config, list_notes,
                rename_note, delete_note, edit_note, move_note, make_folder, remove_folder,
                get_note, selected_notes, attach_group, app_group]:
```

- [ ] **Step 2: 刪除 cat_notes 和 dump 函數**

找到並刪除：
- `@click.command(name="cat")` 整個函數（line 235-269）
- `@click.command(name="dump")` 整個函數（line 324-337）

- [ ] **Step 3: 刪除相關 helper 函數**

`dump_note()` 和 `dump_notes_list()` 這兩個 helper 函數也可以刪除（line 659-689）。

- [ ] **Step 4: Commit**
```bash
git add macnotesapp/cli/cli.py
git commit -m "refactor: remove cat and dump commands (replaced by get/list/selected)"
```

---

### Task 12: 最終測試與驗證

**Files:**
- Modify: `macnotesapp/cli/cli.py`
- Test: `tests/test_applescript_interface.py`

- [ ] **Step 1: 驗證 CLI 結構**

```bash
cd /Users/shuk/projects/tmp/macnotesapp
uv run notes --help
```

檢查輸出包含：
- `get` 命令
- `selected` 命令
- `attach` 子命令群
- `app` 子命令群
- `list` 有 --name, --body, --text, --account, --folder, --password-protected, --json, --id-only

- [ ] **Step 2: 驗證 list 輸出格式**

```bash
uv run notes list --id-only | head -5
```

- [ ] **Step 3: 驗證 get 命令**

```bash
# First get an ID
NOTE_ID=$(uv run notes list --id-only | head -1)
# Then get its content
uv run notes get "$NOTE_ID" --format markdown
```

- [ ] **Step 4: Commit**
```bash
git add macnotesapp/cli/cli.py
git commit -m "test: verify CLI ID-first implementation"
```

---

## 總結

| Task | 說明 | 檔案 |
|------|------|------|
| 1 | 新增 `get` 命令 | cli.py |
| 2 | 新增 `selected` 命令 | cli.py |
| 3 | 新增 `attach` 子命令 | commands/attach.py |
| 4 | 新增 `app` 子命令 | commands/app.py |
| 5 | 重構 `list` 命令 | cli.py |
| 6 | 重構 `rename` 命令 | cli.py |
| 7 | 重構 `delete` 命令 | cli.py |
| 8 | 重構 `edit` 命令 | cli.py |
| 9 | 重構 `move` 命令 | cli.py |
| 10 | 修改 `add` 輸出 | cli.py |
| 11 | 移除 `cat`/`dump` | cli.py |
| 12 | 測試驗證 | cli.py |

**預估總共 ~250 行變更**

---

## 執行選項

**Plan complete and saved to `docs/superpowers/plans/2026-05-24-cli-id-first-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**