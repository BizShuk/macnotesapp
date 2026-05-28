"""Attach subcommand for managing note attachments"""

import os
import sys

import click
import json

import macnotesapp


@click.group(name="attach")
def attach_group():
    """Manage note attachments."""
    pass


@attach_group.command(name="list")
@click.argument("note_id", metavar="ID")
@click.option("--json", "-j", "json_", is_flag=True, help="Output as JSON.")
def attach_list(note_id, json_):
    """List attachments for a note.

    Example: notes attach list Notes/p87
    """
    from macnotesapp.cli.id_utils import resolve_note_id
    notesapp = macnotesapp.NotesApp()
    note_id = resolve_note_id(note_id)
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

    Example: notes attach add Notes/p87 /path/to/file.jpg
    """
    from macnotesapp.cli.id_utils import resolve_note_id
    notesapp = macnotesapp.NotesApp()
    note_id = resolve_note_id(note_id)
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

    Example: notes attach save Notes/p87 x-coredata://.../ICAttachment/p5631 --out-dir ./downloads
    """
    from macnotesapp.cli.id_utils import resolve_note_id
    notesapp = macnotesapp.NotesApp()
    note_id = resolve_note_id(note_id)
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
        os.makedirs(out_dir, exist_ok=True)
        saved_path = attachment.save(out_dir)
        click.echo(f"Saved to: {saved_path}")
    except Exception as e:
        click.echo(f"Error saving attachment: {e}", err=True)
        sys.exit(1)
