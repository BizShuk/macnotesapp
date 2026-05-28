# Folder-Scoped Note ID Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change note IDs from ambiguous `.../IMAPNote/p87` to self-documenting `Notes/p87` format that includes folder name, eliminating duplicates from smart folders.

**Architecture:** Use `FOLDER/short_id` as the display ID format. `FOLDER` is the folder name from `container`. `short_id` is the note ID suffix (e.g., `p87`). Resolution searches within the specified folder for backward compatibility.

**Tech Stack:** Python, ScriptingBridge, AppleScript

---

## File Structure

```
macnotesapp/
├── cli.py                    # ID formatting and resolution
│   ├── format_display_id()    # NEW: format FOLDER/short_id
│   ├── resolve_note_id()      # MODIFY: handle new format + folder-scoped search
│   ├── list_notes()           # MODIFY: use format_display_id
│   ├── selected_notes()       # MODIFY: use format_display_id
│   ├── truncate_id()          # MODIFY: parse FOLDER/short_id
│   └── get_note()             # MODIFY: display uses format_display_id
└── notesapp.py                # Folder-scoped note lookup
    ├── Account.notes()        # NO CHANGE (filter by id only)
    ├── Account.folder()       # ADD: returns Folder object for folder-scoped search
    └── Folder.notes()         # ADD: returns notes in folder

tests/
└── (manual interactive tests)
```

---

## Task 1: Add `format_display_id()` function

**Files:**
- Modify: `macnotesapp/cli.py:215-221`

- [ ] **Step 1: Read current truncate_id implementation**

```python
# Current truncate_id at cli.py:215-221
def truncate_id(note_id: str) -> str:
    """Truncate ID for display: .../IMAPNote/p87"""
    if note_id and note_id.startswith("x-coredata://"):
        parts = note_id.split("/")
        if len(parts) >= 3:
            return f".../{parts[-2]}/{parts[-1]}"
    return note_id
```

- [ ] **Step 2: Add format_display_id function after truncate_id**

```python
def format_display_id(note_id: str, folder: str = "") -> str:
    """Format note ID for display as FOLDER/short_id.

    Args:
        note_id: Full x-coredata:// note ID
        folder: Folder name from container (e.g., 'Notes', 'Arch')

    Returns:
        Display ID in format 'FOLDER/short_id' (e.g., 'Notes/p87')
        If folder is empty, falls back to truncate_id behavior.
    """
    if not note_id:
        return note_id

    # Extract short_id (last part after last slash)
    if note_id.startswith("x-coredata://"):
        parts = note_id.split("/")
        short_id = parts[-1] if parts else note_id
    else:
        short_id = note_id

    # Combine with folder if available
    if folder:
        return f"{folder}/{short_id}"
    else:
        # Fallback to old truncate behavior
        if note_id.startswith("x-coredata://"):
            parts = note_id.split("/")
            if len(parts) >= 3:
                return f".../{parts[-2]}/{parts[-1]}"
        return note_id
```

- [ ] **Step 3: Update truncate_id to parse FOLDER/short_id format**

```python
def truncate_id(note_id: str) -> str:
    """Parse note ID for display.

    Handles two formats:
    - FOLDER/short_id (e.g., 'Notes/p87') - returns as-is
    - x-coredata://.../IMAPNote/p87 - truncates to .../IMAPNote/p87
    """
    if not note_id:
        return note_id

    # If already in FOLDER/short_id format, return as-is
    if "/" in note_id and not note_id.startswith("x-coredata://"):
        return note_id

    # Truncate x-coredata URLs
    if note_id.startswith("x-coredata://"):
        parts = note_id.split("/")
        if len(parts) >= 3:
            return f".../{parts[-2]}/{parts[-1]}"
    return note_id
```

- [ ] **Step 4: Commit**

```bash
git add macnotesapp/cli.py
git commit -m "feat: add format_display_id and update truncate_id to handle FOLDER/short_id"
```

---

## Task 2: Add folder-scoped search to Account

**Files:**
- Modify: `macnotesapp/notesapp.py:440-447`

- [ ] **Step 1: Read Account._folder_for_name implementation**

```python
# Current implementation at notesapp.py:440-447
def _folder_for_name(self, folder: str) -> ScriptingBridge.SBObject:
    """Return ScriptingBridge folder object for folder"""
    if folder_objs := self._account.folders().filteredArrayUsingPredicate_(
        AppKit.NSPredicate.predicateWithFormat_("name == %@", folder)
    ):
        return folder_objs[0]
    else:
        raise ValueError(f"Could not find folder {folder}")
```

- [ ] **Step 2: Modify Account._folder_for_name to be public (_folder_for_name → folder_for_name)**

```python
def folder_for_name(self, folder: str) -> "Folder":
    """Return Folder object for folder with name folder.

    Args:
        folder: Name of folder to retrieve

    Returns:
        Folder object

    Raises:
        ValueError: if folder not found
    """
    folder_obj = self._folder_for_name(folder)
    return Folder(folder_obj)
```

- [ ] **Step 3: Add Folder.notes() method**

```python
# Add after Folder.__init__ (around line 852)
def notes(self) -> list["Note"]:
    """Return list of Note objects for all notes in this folder.

    Returns:
        list of Note objects in this folder
    """
    return [Note(note) for note in self._folder.notes()]
```

- [ ] **Step 4: Run test to verify Folder class works**

```bash
uv run python3 -c "
from macnotesapp import NotesApp
notes = NotesApp()
account = notes.account()
print('Folders:', account.folders)
folder = account.folder_for_name(account.default_folder)
print('Default folder:', folder.name)
notes_in_folder = folder.notes()
print('Notes in default folder:', len(notes_in_folder))
"
```

- [ ] **Step 5: Commit**

```bash
git add macnotesapp/notesapp.py
git commit -m "feat: add Folder.notes() and public folder_for_name method"
```

---

## Task 3: Update resolve_note_id for folder-scoped search

**Files:**
- Modify: `macnotesapp/cli.py:224-259`

- [ ] **Step 1: Read current resolve_note_id implementation**

```python
# Current resolve_note_id at cli.py:224-259
def resolve_note_id(note_id: str) -> str:
    """Resolve partial note ID to full ID.

    If note_id is already a full x-coredata:// ID, return as-is.
    If note_id is partial (e.g., 'p87' or 'IMAPNote/p87'), search all notes
    and return the full ID if exactly one match is found.

    Args:
        note_id: Full or partial note ID

    Returns:
        Full note ID

    Raises:
        click.ClickException if no match or multiple matches found
    """
    # If it's already a full ID, return as-is
    if note_id.startswith("x-coredata://"):
        return note_id

    # Otherwise, search for notes ending with the partial ID
    notes_app = macnotesapp.NotesApp()
    all_notes = notes_app.notes()

    # Find notes where the ID ends with the given partial
    matches = []
    for note in all_notes:
        if note.id.endswith(f"/{note_id}") or note.id.endswith(note_id):
            matches.append(note.id)

    if len(matches) == 0:
        raise click.ClickException(f"No note found matching '{note_id}'")
    elif len(matches) > 1:
        raise click.ClickException(f"Multiple notes match '{note_id}': {len(matches)} found. Use full ID.")

    return matches[0]
```

- [ ] **Step 2: Rewrite resolve_note_id to handle FOLDER/short_id format**

```python
def resolve_note_id(note_id: str, notes_app: "NotesApp" = None) -> str:
    """Resolve note ID to full x-coredata:// ID.

    Handles three formats:
    - x-coredata://.../IMAPNote/p87 - return as-is
    - FOLDER/short_id (e.g., 'Notes/p87') - search within folder
    - short_id (e.g., 'p87') - search all notes (backward compat)

    Args:
        note_id: Full ID, FOLDER/short_id, or partial ID
        notes_app: NotesApp instance (optional, creates one if None)

    Returns:
        Full x-coredata:// note ID

    Raises:
        click.ClickException if no match or multiple matches found
    """
    # If it's already a full ID, return as-is
    if note_id.startswith("x-coredata://"):
        return note_id

    # Parse FOLDER/short_id format
    folder_name = None
    partial_id = note_id

    if "/" in note_id and not note_id.startswith("x-coredata://"):
        parts = note_id.rsplit("/", 1)
        folder_name, partial_id = parts[0], parts[1]

    # Initialize NotesApp if not provided
    if notes_app is None:
        notes_app = macnotesapp.NotesApp()

    # Search strategy: folder-scoped or global
    if folder_name:
        # Folder-scoped search: find note in specific folder
        account_name = None
        # Find which account contains this folder
        for acc_name in notes_app.accounts:
            account = notes_app.account(acc_name)
            if folder_name in account.folders:
                account_name = acc_name
                break

        if not account_name:
            raise click.ClickException(f"Folder '{folder_name}' not found in any account")

        account = notes_app.account(account_name)
        folder_obj = account.folder_for_name(folder_name)
        folder_notes = folder_obj.notes()

        matches = [note.id for note in folder_notes
                   if note.id.endswith(f"/{partial_id}") or note.id.endswith(partial_id)]
    else:
        # Global search (backward compat for plain 'p87')
        all_notes = notes_app.notes()
        matches = [note.id for note in all_notes
                   if note.id.endswith(f"/{partial_id}") or note.id.endswith(partial_id)]

    if len(matches) == 0:
        raise click.ClickException(f"No note found matching '{note_id}'")
    elif len(matches) > 1:
        raise click.ClickException(
            f"Multiple notes match '{note_id}': {len(matches)} found. "
            f"Use full ID or FOLDER/short_id format."
        )

    return matches[0]
```

- [ ] **Step 3: Test resolve_note_id manually**

```bash
uv run python3 -c "
from macnotesapp.cli import resolve_note_id
print('Testing resolve_note_id...')

# Test 1: Full ID passthrough
full_id = 'x-coredata://.../IMAPNote/p87'
result = resolve_note_id(full_id)
print(f'Full ID: {full_id} -> {result}')

# Test 2: FOLDER/short_id format (will need actual notes)
try:
    result = resolve_note_id('Notes/p87')
    print(f'FOLDER/short_id: Notes/p87 -> {result}')
except Exception as e:
    print(f'FOLDER/short_id error: {e}')
"

# Then test with actual notes
uv run notes list --id-only | head -5
uv run notes get Notes/p87 2>&1 || echo "Expected to fail if no such note"
```

- [ ] **Step 4: Commit**

```bash
git add macnotesapp/cli.py
git commit -m "feat: update resolve_note_id for FOLDER/short_id format with folder-scoped search"
```

---

## Task 4: Update list command to use folder-qualified display IDs

**Files:**
- Modify: `macnotesapp/cli.py:262-338`

- [ ] **Step 1: Read current list_notes implementation (lines 262-338)]

Focus on the id_only section (lines 286-288) and human-readable output (lines 323-338).

- [ ] **Step 2: Update id_only section to use format_display_id**

```python
    if id_only:
        for i in range(len(noteslist)):
            note_id = noteslist.id[i]
            folder = noteslist.container[i] or ""
            folder_parts = folder.split("/")
            folder_name = folder_parts[-1] if folder_parts else ""
            display_id = format_display_id(note_id, folder_name)
            print(display_id)
        return
```

- [ ] **Step 3: Update human-readable section**

```python
    for i in range(len(noteslist)):
        note_id = noteslist.id[i]
        folder = noteslist.folder[i] or ""
        folder_parts = folder.split("/")
        folder_name = folder_parts[-1] if len(folder_parts) > 1 else folder

        # Use format_display_id for consistent ID display
        display_id = format_display_id(note_id, folder_name)
        name = noteslist.name[i] or "---"
        mod_date = noteslist.modification_date[i].strftime("%Y-%m-%dT%H:%M") if noteslist.modification_date[i] else "---"
        pwd = "🔒" if noteslist.password_protected[i] else "-"

        # folder_display now just shows account/folder_name without duplicating ID info
        account = folder_parts[0] if folder_parts else ""
        folder_display = f"{account}/{folder_name}" if account else folder_name

        # Truncate long names
        if len(name) > name_width - 2:
            name = name[:name_width-2] + ".."

        print(f"{display_id:<{id_width}} {folder_display:<{folder_width}} {name:<{name_width}} {mod_date:<{date_width}} {pwd}")
```

- [ ] **Step 4: Update JSON output to use format_display_id**

```python
    if json_:
        import json
        notes_data = []
        for i in range(len(noteslist)):
            folder = noteslist.folder[i] or ""
            folder_parts = folder.split("/")
            account = folder_parts[0] if folder_parts else ""
            folder_name_only = folder_parts[-1] if len(folder_parts) > 1 else ""

            # Format ID as FOLDER/short_id
            note_id = noteslist.id[i]
            display_id = format_display_id(note_id, folder_name_only)

            notes_data.append({
                "id": display_id,  # Changed from noteslist.id[i]
                "name": noteslist.name[i],
                "account": account,
                "folder": folder_name_only,
                "creation_date": noteslist.creation_date[i].isoformat() if noteslist.creation_date[i] else None,
                "modification_date": noteslist.modification_date[i].isoformat() if noteslist.modification_date[i] else None,
                "password_protected": noteslist.password_protected[i],
            })
        print(json.dumps(notes_data, indent=2))
        return
```

- [ ] **Step 5: Test list command**

```bash
uv run notes list --id-only | head -5
uv run notes list | head -5
uv run notes list --json | head -10
```

- [ ] **Step 6: Commit**

```bash
git add macnotesapp/cli.py
git commit -m "feat: list command uses FOLDER/short_id format for display"
```

---

## Task 5: Update selected command to use FOLDER/short_id

**Files:**
- Modify: `macnotesapp/cli.py:660-689`

- [ ] **Step 1: Update selected_notes id_only section**

```python
    if id_only:
        for note in notes:
            display_id = format_display_id(note.id, note.folder)
            print(display_id)
    elif json_:
        import json
        notes_list = []
        for note in notes:
            folder_parts = note.folder.split("/")
            folder_name = folder_parts[-1] if folder_parts else note.folder
            note_data = note.asdict()
            note_data["id"] = format_display_id(note.id, folder_name)  # Use formatted ID
            note_data["creation_date"] = note_data["creation_date"].isoformat()
            note_data["modification_date"] = note_data["modification_date"].isoformat()
            notes_list.append(note_data)
        print(json.dumps(notes_list, indent=2))
    else:
        # Default: human-readable, one line per note
        for note in notes:
            folder_parts = note.folder.split("/")
            folder_name = folder_parts[-1] if folder_parts else note.folder
            display_id = format_display_id(note.id, folder_name)
            print(f"{display_id}\t{note.account}/{folder_name}\t{note.name}")
```

- [ ] **Step 2: Test selected command**

```bash
# Select a note in Notes.app first, then:
uv run notes selected --id-only
uv run notes selected --json
```

- [ ] **Step 3: Commit**

```bash
git add macnotesapp/cli.py
git commit -m "feat: selected command uses FOLDER/short_id format"
```

---

## Task 6: Update get command display

**Files:**
- Modify: `macnotesapp/cli.py:596-657`

- [ ] **Step 1: Read get_note implementation**

- [ ] **Step 2: Update JSON output to use format_display_id**

```python
    if output_format == "json":
        folder_parts = note.folder.split("/")
        folder_name = folder_parts[-1] if folder_parts else note.folder
        note_data = note.asdict()
        note_data["id"] = format_display_id(note.id, folder_name)  # Use formatted ID
        note_data["creation_date"] = note_data["creation_date"].isoformat()
        note_data["modification_date"] = note_data["modification_date"].isoformat()
        print(json.dumps(note_data, indent=2))
    else:
        # Output format: show FOLDER/short_id in header comment
        if output_format == "html":
            folder_parts = note.folder.split("/")
            folder_name = folder_parts[-1] if folder_parts else note.folder
            print(f"<!-- ID: {format_display_id(note.id, folder_name)} -->\n{note.body}")
        elif output_format == "plaintext":
            print(f"=== NAME: {note.name} ===\nID: {format_display_id(note.id, note.folder)}\n{note.plaintext}")
        else:  # markdown
            print(f"# {note.name}\n\nID: {format_display_id(note.id, note.folder)}\n\n{html2md(note.body)}")
```

- [ ] **Step 3: Test get command**

```bash
uv run notes list --id-only | head -1
# Use that ID to test get
uv run notes get "Notes/p87" --format markdown
uv run notes get "Notes/p87" --json
```

- [ ] **Step 4: Commit**

```bash
git add macnotesapp/cli.py
git commit -m "feat: get command displays FOLDER/short_id format"
```

---

## Task 7: Integration test with all commands

- [ ] **Step 1: Test full workflow**

```bash
# 1. List notes to see the new format
uv run notes list --id-only | head -5

# 2. Get a specific note
NOTE_ID=$(uv run notes list --id-only | head -1)
echo "Testing with: $NOTE_ID"
uv run notes get "$NOTE_ID"

# 3. Test resolve with new format
uv run notes get Notes/p87

# 4. Test backward compat with just short_id
uv run notes get p87

# 5. Test rename
uv run notes rename "$NOTE_ID" "Test Rename"

# 6. Restore name
uv run notes rename "$NOTE_ID" "Test Note"
```

- [ ] **Step 2: Update README if needed**

If CLI help output mentions `x-coredata://` format, update to reflect new `FOLDER/short_id` format.

```bash
uv run cog -r README.md
```

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: implement FOLDER/short_id note ID format"
```

---

## Self-Review Checklist

- [ ] All `format_display_id` calls pass `folder` parameter
- [ ] `resolve_note_id` handles three formats: full x-coredata://, FOLDER/short_id, short_id
- [ ] No `x-coredata://` strings in user-facing output
- [ ] All commands use `format_display_id` for display (list, selected, get)
- [ ] Backward compatibility: `notes get p87` still works
- [ ] Type consistency: `note.folder` returns full path, `folder_name` is extracted as last component