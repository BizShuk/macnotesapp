"""dump command for macnotesapp - export notes to Markdown with attachments"""

import pathlib

import click

import macnotesapp
from macnotesapp.cli.id_utils import resolve_note_id
from markdownify import markdownify as html2md


def _note_short_id(note_id: str) -> str:
    """Extract short_id (e.g. 'p87') from full x-coredata:// ID or FOLDER/short_id."""
    return note_id.rsplit("/", 1)[-1]


def _safe_filename(name: str) -> str:
    """Replace path-sensitive characters in filename."""
    return name.replace("/", "_").replace("\\", "_").replace(":", "_")


_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic", ".heif"}


def _is_image_filename(name: str) -> bool:
    """Return True if filename looks like an image based on extension."""
    return any(name.lower().endswith(ext) for ext in _IMAGE_EXTENSIONS)


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

    # Convert body HTML → Markdown using markdownify
    body_md = html2md(note.body)

    # Build attachment section
    attachment_lines = []
    saved_attachments = []

    for att in note.attachments:
        att_url = att.URL
        is_url_attachment = att_url and att_url.startswith("http")

        if is_url_attachment:
            # URL attachment — embed as image if URL ends with image extension
            if _is_image_filename(att_url):
                attachment_lines.append(f"![{att.name}]({att_url})")
            else:
                attachment_lines.append(f"[{att.name}]({att_url})")
        else:
            # File attachment — save to attachments/ and reference locally
            att_filename = f"{short_id}_{att.name}"
            att_dir = out_dir / "attachments"
            att_dir.mkdir(exist_ok=True)
            try:
                att.save(str(att_dir))
                saved_attachments.append(att_filename)
                if _is_image_filename(att.name):
                    attachment_lines.append(f"![{att.name}](attachments/{att_filename})")
                else:
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


def _ensure_out_dir(out_dir: str) -> pathlib.Path:
    """Create and return output directory path."""
    out_path = pathlib.Path(out_dir)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        click.echo(f"Error creating output directory: {e}", err=True)
        raise click.Abort()
    return out_path


@click.command(name="dump")
@click.argument("note_id", metavar="ID", required=False)
@click.option("--folder", "-f", "folder_name", metavar="FOLDER", type=str, help="Dump all notes in folder (searches all accounts)")
@click.option("--all", "dump_all", is_flag=True, help="Dump all notes from all accounts and folders")
@click.option("--out-dir", "-o", required=True, type=click.Path(file_okay=False, dir_okay=True), help="Output directory")
def dump_cmd(note_id, folder_name, dump_all, out_dir):
    """Dump notes to Markdown with attachments.

    Modes (mutually exclusive):
      notes dump ID --out-dir ./output       Dump single note by ID
      notes dump --folder FOLDER --out-dir ./output    Dump all notes in folder
      notes dump --all --out-dir ./output    Dump all notes from all accounts

    Examples:
      notes dump Notes/p87 --out-dir ./output
      notes dump --folder Archive --out-dir ./output
      notes dump --all --out-dir ./output
    """
    out_path = _ensure_out_dir(out_dir)

    # Validate mutually exclusive options
    modes = sum(bool(x) for x in [note_id, folder_name, dump_all])
    if modes != 1:
        click.echo("Error: specify exactly one of: NOTE_ID, --folder FOLDER, or --all", err=True)
        raise click.Abort()

    notesapp = macnotesapp.NotesApp()

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

        _dump_note(note, out_path)
        folder_part = _safe_filename(note.folder or "Unknown")
        title = _safe_filename(note.name or "untitled")
        click.echo(f"Dumped '{note.name}' -> {out_path / (folder_part + '_' + title + '.md')}")

    elif folder_name:
        # Folder mode
        accounts = notesapp.accounts
        found = False
        for account_name in accounts:
            account = notesapp.account(account_name)
            if folder_name not in account.folders:
                continue
            found = True
            folder_obj = account.folder(folder_name)
            for note in folder_obj.notes():
                if note.password_protected:
                    click.echo(f"Warning: Skipping password-protected note '{note.name}'", err=True)
                    continue
                _dump_note(note, out_path)
                click.echo(f"Dumped '{note.name}' ({account_name}/{folder_name})")

        if not found:
            click.echo(f"Error: Folder '{folder_name}' not found in any account.", err=True)
            raise click.Abort()

    elif dump_all:
        # All mode
        accounts = notesapp.accounts
        for account_name in accounts:
            account = notesapp.account(account_name)
            for folder_name in account.folders:
                folder_obj = account.folder(folder_name)
                for note in folder_obj.notes():
                    if note.password_protected:
                        click.echo(f"Warning: Skipping password-protected note '{note.name}'", err=True)
                        continue
                    _dump_note(note, out_path)
                    click.echo(f"Dumped '{note.name}' ({account_name}/{folder_name})")