"""Entry point for macnotesapp CLI"""

import json
import os
import pathlib
import sys
from typing import Dict, Iterable

import click
import markdown2
import questionary
from applescript import ScriptError
from markdownify import markdownify as html2md
from rich.console import Console
from rich.markdown import Markdown

import macnotesapp
from macnotesapp import __version__
from macnotesapp import NotesList

from .cli_config import (
    CONFIG_FILE,
    DEFAULT_EDITOR,
    DEFAULT_FORMAT,
    FORMAT_HTML,
    FORMAT_MARKDOWN,
    FORMAT_OPTIONS,
    FORMAT_PLAINTEXT,
    ConfigSettings,
)
from .cli_help import RichHelpCommand, help
from .cli_param_types import URLType
from .readable import get_readable_html
from .commands.attach import attach_group
from .commands.app import app_group

# extra features to support for Markdown to HTML conversion with markdown2
MARKDOWN_EXTRAS = ["fenced-code-blocks", "footnotes", "tables"]


@click.command(name="accounts")
@click.option(
    "--json", "-j", "json_", is_flag=True, help="Print output in JSON format."
)
def accounts(json_):
    """Print information about Notes accounts."""
    account_data = get_account_data()
    if json_:
        print(json.dumps(account_data))
    else:
        for account in account_data:
            print(f"{account}:")
            for k, v in account_data[account].items():
                print(f"  {k}: {v}")


@click.command(name="add", cls=RichHelpCommand)
@click.option("--show", "-s", is_flag=True, help="Show note in Notes after adding.")
@click.option("--json", "-j", "json_", is_flag=True, help="Output full note data as JSON.")
@click.option("--file", "-F", required=False, type=click.File())
@click.option("--url", "-u", required=False, type=URLType())
@click.option("--html", "-h", is_flag=True, help="Use HTML for body of note.")
@click.option("--markdown", "-m", is_flag=True, help="Use Markdown for body of note.")
@click.option(
    "--plaintext",
    "-p",
    is_flag=True,
    help="Use plaintext for body of note (default unless changed in `notes config`).",
)
@click.option(
    "--edit", "-e", is_flag=True, help="Edit note text before adding in default editor."
)
@click.option(
    "--account",
    "-a",
    "account_name",
    metavar="ACCOUNT",
    type=str,
    help="Add note to account ACCOUNT.",
)
@click.option(
    "--folder",
    "-f",
    "folder_name",
    metavar="FOLDER",
    type=str,
    help="Add note to folder FOLDER.",
)
@click.argument("note", metavar="NOTE", required=False, default="")
def add_note(
    show, json_, file, url, html, markdown, plaintext, edit, account_name, folder_name, note
):
    """Add new note.

    There are multiple ways to add a new note:

    [i]Add a new note from standard input (STDIN)[/]:

    [b]notes add[/]

    [b]cat file.txt | notes add[/]

    [b]notes add < file.txt[/]

    [i]Add a new note by passing string on command line[/]:

    [b]notes add NOTE[/]

    [i]Add a new note by opening default editor (defined in $EDITOR or via `notes config`)[/]:

    [b]notes add --edit[/]

    [b]notes add -e[/]

    [i]Add a new note from URL (downloads URL, creates a cleaned readable version to store in new Note):

    [b]notes add --url URL

    [b]notes add -u URL

    If NOTE is a single line, adds new note with name NOTE and no body.
    If NOTE is more than one line, adds new note where name is first line of NOTE and body is remainder.

    Body of note must be plain text unless [i]--html/-h[/] or [i]--markdown/-m[/] flag is set
    in which case body should be HTML or Markdown, respectively.
    If [i]--edit/-e[/] flag is set, note will be opened in default editor before being added.
    If [i]--show/-s[/] flag is set, note will be shown in Notes.app after being added.
    By default, prints the note ID to stdout. Use [i]--json/-j[/] to print full note data as JSON.

    Account and top level folder may be specified with [i]--account/-a[/] and [i]--folder/-f[/], respectively.
    If not provided, default account and folder are used.
    """

    if sum([html, markdown, plaintext]) > 1:
        click.echo(
            "Only one of --html, --markdown, and --plaintext can be specified.",
            err=True,
        )
        raise click.Abort()

    if file and url:
        click.echo("Only one of --file, --url can be specified.", err=True)
        raise click.Abort()

    config = ConfigSettings()
    format_ = config.format
    if html:
        format_ = FORMAT_HTML
    elif markdown:
        format_ = FORMAT_MARKDOWN
    elif plaintext:
        format_ = FORMAT_PLAINTEXT

    folder_name = folder_name or config.folder
    account_name = account_name or config.account
    editor = config.editor

    if file:
        note_text = file.read()
    elif url:
        try:
            name, body = get_readable_html(url)
            note_text = f"{name}\n{body}"
        except Exception as e:
            click.echo(f"Error downloading url '{url}': {e}.", err=True)
            raise click.Abort() from e
    elif note == "-" or (not note and not edit):
        note_text = sys.stdin.read()
    else:
        note_text = note

    if edit:
        ext = (
            ".html"
            if format_ == FORMAT_HTML
            else ".md"
            if format_ == FORMAT_MARKDOWN
            else ".txt"
        )
        note_text = click.edit(note_text, editor=editor, extension=ext)

    if not note_text:
        click.echo("No note text.", err=True)
        raise click.Abort()

    note_text = note_text.strip()
    note_parts = note_text.partition("\n")
    name, body = note_parts[0], note_parts[2]

    if format_ == FORMAT_MARKDOWN:
        # convert Markdown to HTML
        body = markdown2.markdown(body, extras=MARKDOWN_EXTRAS)
    elif format_ != FORMAT_HTML:
        # convert plain text to HTML
        body = "".join(f"<div>{line or '<br>'}</div>\n" for line in body.split("\n"))

    notes = macnotesapp.NotesApp()
    try:
        account = notes.account(account_name)
        new_note = account.make_note(name, body, folder_name)
        if json_:
            note_data = new_note.asdict()
            note_data["creation_date"] = note_data["creation_date"].isoformat()
            note_data["modification_date"] = note_data["modification_date"].isoformat()
            print(json.dumps(note_data, indent=2))
        else:
            print(new_note.id)
        if show:
            new_note.show()
    except ScriptError as e:
        click.echo(f"Error adding note: {e}", err=True)
        raise click.Abort() from e


def truncate_id(note_id: str) -> str:
    """Truncate ID for display: .../IMAPNote/p87"""
    if note_id and note_id.startswith("x-coredata://"):
        parts = note_id.split("/")
        if len(parts) >= 3:
            return f".../{parts[-2]}/{parts[-1]}"
    return note_id


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
            # Extract account from folder path
            folder = noteslist.folder[i] or ""
            folder_parts = folder.split("/")
            account = folder_parts[0] if folder_parts else ""
            folder_name_only = folder_parts[-1] if len(folder_parts) > 1 else ""

            notes_data.append({
                "id": noteslist.id[i],
                "name": noteslist.name[i],
                "account": account,
                "folder": folder_name_only,
                "creation_date": noteslist.creation_date[i].isoformat() if noteslist.creation_date[i] else None,
                "modification_date": noteslist.modification_date[i].isoformat() if noteslist.modification_date[i] else None,
                "password_protected": noteslist.password_protected[i],
            })
        print(json.dumps(notes_data, indent=2))
        return

    # Human-readable output
    console = Console()
    id_width = 25
    folder_width = 18
    name_width = 28
    date_width = 18
    pwd_width = 5
    header = f"{'ID':<{id_width}} {'ACCOUNT/FOLDER':<{folder_width}} {'NAME':<{name_width}} {'MOD_DATE':<{date_width}} {'PWD':<{pwd_width}}"
    print(header)

    for i in range(len(noteslist)):
        note_id = truncate_id(noteslist.id[i])
        folder = noteslist.folder[i] or ""
        folder_parts = folder.split("/")
        account = folder_parts[0] if folder_parts else ""
        folder_name_only = folder_parts[-1] if len(folder_parts) > 1 else folder
        folder_display = f"{account}/{folder_name_only}" if account else folder_name_only
        name = noteslist.name[i] or "---"
        mod_date = noteslist.modification_date[i].strftime("%Y-%m-%dT%H:%M") if noteslist.modification_date[i] else "---"
        pwd = "🔒" if noteslist.password_protected[i] else "-"

        # Truncate long names
        if len(name) > name_width - 2:
            name = name[:name_width-2] + ".."

        print(f"{note_id:<{id_width}} {folder_display:<{folder_width}} {name:<{name_width}} {mod_date:<{date_width}} {pwd}")


@click.command(name="config")
def config():
    """Configure default settings for account, editor, etc."""
    notes = macnotesapp.NotesApp()
    config = ConfigSettings()
    settings = config.read()

    # account
    accounts = notes.accounts
    account = settings.get("account")
    account = account if account and account in accounts else notes.default_account
    settings["account"] = questionary.select(
        "Select default account for new notes added with `notes add`: ",
        choices=accounts,
        default=account,
    ).ask()

    # folder
    account = notes.account(settings["account"])
    folders = account.folders
    folder = settings.get("folder")
    folder = folder if folder and folder in folders else account.default_folder
    settings["folder"] = questionary.select(
        "Select default folder for new notes: ", choices=folders, default=folder
    ).ask()

    # format
    format_ = settings.get("format")
    format_ = format_ if format_ and format_ in FORMAT_OPTIONS else DEFAULT_FORMAT
    settings["format"] = questionary.select(
        "Select default format for new notes: ", choices=FORMAT_OPTIONS, default=format_
    ).ask()

    # editor
    def validate_editor(env_or_path: str) -> bool:
        """Validate that env or path is valid for editor"""
        if not env_or_path.startswith("$"):
            return pathlib.Path(env_or_path).is_file()
        path = os.environ.get(env_or_path[1:])
        return bool(path and pathlib.Path(path).is_file())

    editor = settings.get("editor")
    editor = editor if editor and validate_editor(editor) else DEFAULT_EDITOR
    settings["editor"] = questionary.text(
        "Enter an environment variable (starting with '$') or full path to use for default editor: ",
        default=editor,
        validate=validate_editor,
    ).ask()
    config.write(settings)
    click.echo(f"Settings saved to {CONFIG_FILE}")


@click.command(name="rename")
@click.argument("note_id", metavar="ID")
@click.argument("new_name", metavar="NEW_NAME")
def rename_note(note_id, new_name):
    """Rename a note by ID.

    Example: notes rename x-coredata://.../IMAPNote/p87 "New Title"
    Example: notes rename p87 "New Title"
    """
    note_id = resolve_note_id(note_id)
    notes_app = macnotesapp.NotesApp()
    matching_notes = notes_app.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]
    old_name = note.name
    note.name = new_name
    click.echo(f"Renamed '{old_name}' -> '{new_name}'")


@click.command(name="delete")
@click.argument("note_id", metavar="ID")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def delete_note(note_id, yes):
    """Delete a note by ID.

    Example: notes delete x-coredata://.../IMAPNote/p87 --yes
    Example: notes delete p87 --yes
    """
    note_id = resolve_note_id(note_id)
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


@click.command(name="edit")
@click.argument("note_id", metavar="ID")
@click.option("--body", "-b", help="Set body content directly (non-interactive).")
@click.option("--name", "-n", help="Set note name only.")
@click.option("--html", "-h", "use_html", is_flag=True, help="Treat body as HTML.")
@click.option("--markdown", "-m", "use_markdown", is_flag=True, help="Treat body as Markdown.")
@click.option("--edit", "-e", "interactive", is_flag=True, help="Open in editor (interactive mode).")
def edit_note(note_id, body, name, use_html, use_markdown, interactive):
    """Edit a note's name and/or body by ID.

    Default (non-interactive): use --body and/or --name to set content directly.
    With --edit: opens editor with current content (both name and body).

    Examples:
      notes edit x-coredata://.../IMAPNote/p87 --body "New content"
      notes edit p87 --name "New Title"
      notes edit p87 --name "New Title" --body "New body"
      notes edit p87 --edit
    """
    note_id = resolve_note_id(note_id)
    notes_app = macnotesapp.NotesApp()
    matching_notes = notes_app.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]
    original_name = note.name

    if body:
        # Non-interactive mode: use provided body
        if use_markdown:
            body = markdown2.markdown(body, extras=MARKDOWN_EXTRAS)
        elif not use_html:
            body = f"<div>{body}</div>"
        note.body = body

    if name:
        note.name = name

    if body or name:
        click.echo(f"Updated '{note.name}'")
    elif interactive:
        # Interactive mode: open editor with current content
        import tempfile
        config = ConfigSettings()
        settings = config.read()
        editor = settings.get("editor", DEFAULT_EDITOR)
        if editor.startswith("$"):
            editor = os.environ.get(editor[1:], "vim")

        # Include name in editor header
        current_md = f"# {note.name}\n\n{html2md(note.body)}"
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

        # Parse name from first line if it's a header
        lines = new_content.split("\n", 1)
        if lines[0].startswith("# "):
            note.name = lines[0][2:].strip()
            body_content = lines[1] if len(lines) > 1 else ""
        else:
            body_content = new_content

        new_html = markdown2.markdown(body_content, extras=MARKDOWN_EXTRAS)
        note.body = new_html
        os.unlink(temp_path)
        click.echo(f"Updated '{note.name}'")
    else:
        # No body and not interactive - show error
        click.echo("Error: No content provided. Use --body TEXT, --name TEXT, or --edit for interactive mode.", err=True)
        sys.exit(1)


@click.command(name="move")
@click.argument("note_id", metavar="ID")
@click.option("--folder", "-f", required=True, help="Destination folder.")
def move_note(note_id, folder):
    """Move a note to a different folder by ID.

    Example: notes move x-coredata://.../IMAPNote/p87 --folder Archive
    Example: notes move p87 --folder Archive
    """
    note_id = resolve_note_id(note_id)
    notes_app = macnotesapp.NotesApp()
    matching_notes = notes_app.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]
    old_folder = note.folder
    note.move(folder)
    click.echo(f"Moved '{note.name}' from '{old_folder}' to '{folder}'")


@click.command(name="mkdir")
@click.argument("folder_name", metavar="FOLDER_NAME")
@click.option(
    "--account",
    "-a",
    "account_name",
    metavar="ACCOUNT",
    type=str,
    help="Account to create folder in.",
)
def make_folder(folder_name, account_name):
    """Create a new folder.

    Example: notes mkdir "Archive"
    """
    notes_app = macnotesapp.NotesApp()
    account_name = account_name or notes_app.default_account
    account = notes_app.account(account_name)
    account.make_folder(folder_name)
    click.echo(f"Created folder '{folder_name}' in {account_name}")


@click.command(name="rmdir")
@click.argument("folder_name", metavar="FOLDER_NAME")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.option(
    "--account",
    "-a",
    "account_name",
    metavar="ACCOUNT",
    type=str,
    help="Account to delete folder from.",
)
def remove_folder(folder_name, yes, account_name):
    """Delete a folder.

    Example: notes rmdir "Old Folder"
    """
    notes_app = macnotesapp.NotesApp()
    account_name = account_name or notes_app.default_account
    account = notes_app.account(account_name)
    if folder_name not in account.folders:
        click.echo(f"Error: Folder '{folder_name}' not found in {account_name}.", err=True)
        sys.exit(1)
    if not yes:
        if not click.confirm(f"Delete folder '{folder_name}' and all its notes?"):
            click.echo("Aborted.")
            sys.exit(0)
    account.delete_folder(folder_name)
    click.echo(f"Deleted folder '{folder_name}' from {account_name}")


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
@click.option("--name-only", is_flag=True, help="Output only the note name.")
@click.option("--body-only", is_flag=True, help="Output only the note body.")
def get_note(note_id, output_format, show, name_only, body_only):
    """Get note content by ID.

    Default: outputs both name and body clearly separated.
    Use --name-only or --body-only to output only one field.

    Example: notes get p87 --format markdown
    Example: notes get p87 --name-only
    Example: notes get p87 --body-only
    """
    note_id = resolve_note_id(note_id)
    notesapp = macnotesapp.NotesApp()
    matching_notes = notesapp.notes(id=[note_id])
    if not matching_notes:
        click.echo(f"Error: Note '{note_id}' not found.", err=True)
        sys.exit(1)
    note = matching_notes[0]

    # Handle --name-only and --body-only first
    if name_only:
        print(note.name)
        return
    if body_only:
        if output_format == "html":
            print(note.body)
        elif output_format == "plaintext":
            print(note.plaintext)
        else:  # markdown
            print(html2md(note.body))
        return

    # Default: output both name and body clearly separated
    if output_format == "json":
        note_data = note.asdict()
        note_data["creation_date"] = note_data["creation_date"].isoformat()
        note_data["modification_date"] = note_data["modification_date"].isoformat()
        print(json.dumps(note_data, indent=2))
    else:
        # Output format: clear separation of name and body
        console = Console()
        if output_format == "html":
            print(f"<!-- NAME: {note.name} -->\n{note.body}")
        elif output_format == "plaintext":
            print(f"=== NAME: {note.name} ===\n{note.plaintext}")
        else:  # markdown
            print(f"# {note.name}\n\n{html2md(note.body)}")

    if show:
        note.show()


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


# Click CLI object & context settings
class CLI_Obj:
    def __init__(self, debug=False, group=None):
        self.debug = debug
        self.group = group


CTX_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CTX_SETTINGS)
@click.option(
    "--debug",
    required=False,
    is_flag=True,
    help="Enable debug output",
    hidden=True,
)
@click.version_option(__version__, "--version", "-v")
@click.pass_context
def cli_main(ctx, debug):
    """notes: work with Apple Notes on the command line."""
    ctx.obj = CLI_Obj(group=cli_main)


# add the commands to the main group
for command in [accounts, add_note, config, list_notes,
                rename_note, delete_note, edit_note, move_note, make_folder, remove_folder,
                get_note, selected_notes, attach_group, app_group]:
    cli_main.add_command(command)


def get_account_data() -> Dict:
    """Get dict of account data for Notes accounts"""
    notes = macnotesapp.NotesApp()
    accounts = notes.accounts
    account_data = {}
    for account_name in accounts:
        account = notes.account(account_name)
        account_data[account_name] = {
            "id": account.id,
            "name": account_name,
            "notes_count": len(account),
            "default_folder": account.default_folder,
        }
    return account_data


