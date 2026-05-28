"""dump command for macnotesapp - export notes to Markdown with attachments"""

import os
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


@click.group(name="dump")
def dump_group():
    """Dump notes to Markdown with attachments.

    Example: notes dump note Notes/p87 --out-dir ./output
    """
    pass


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

    _dump_note(note, out_path)
    folder_part = _safe_filename(note.folder or "Unknown")
    title = _safe_filename(note.name or "untitled")
    click.echo(f"Dumped '{note.name}' -> {out_path / (folder_part + '_' + title + '.md')}")