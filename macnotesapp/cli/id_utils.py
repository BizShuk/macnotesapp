"""ID utility functions for macnotesapp CLI.

These functions handle note ID formatting and resolution.
Separated from cli.py to avoid circular imports with attach.py.
"""

import macnotesapp


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


def resolve_note_id(note_id: str, notes_app: "macnotesapp.NotesApp" = None) -> str:
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
    import click

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
        # Folder-scoped search: find note in specific folder across all accounts
        matches = []
        for acc_name in notes_app.accounts:
            account = notes_app.account(acc_name)
            if folder_name in account.folders:
                folder_obj = account.folder_for_name(folder_name)
                folder_notes = folder_obj.notes()
                for note in folder_notes:
                    if note.id.endswith(f"/{partial_id}") or note.id.endswith(partial_id):
                        matches.append(note.id)

        if len(matches) == 0:
            raise click.ClickException(f"No note found matching '{note_id}'")
        elif len(matches) > 1:
            raise click.ClickException(
                f"Multiple notes match '{note_id}': {len(matches)} found. "
                f"Use full ID or more specific FOLDER/short_id."
            )
        return matches[0]
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