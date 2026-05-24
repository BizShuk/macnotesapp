"""App subcommand for Notes.app control"""

import click
from applescript import ScriptError

import macnotesapp
from macnotesapp import __version__ as cli_version


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
    try:
        notesapp.activate()
        click.echo("Notes.app activated.")
    except ScriptError as e:
        click.echo(f"Error activating Notes.app: {e}", err=True)
        raise click.Abort() from e


@app_group.command(name="quit")
def app_quit():
    """Quit Notes.app.

    Example: notes app quit
    """
    notesapp = macnotesapp.NotesApp()
    try:
        notesapp.quit()
        click.echo("Notes.app quit.")
    except ScriptError as e:
        click.echo(f"Error quitting Notes.app: {e}", err=True)
        raise click.Abort() from e


@app_group.command(name="version")
def app_version():
    """Show Notes.app version.

    Example: notes app version
    """
    notesapp = macnotesapp.NotesApp()
    version = notesapp.version
    click.echo(f"Notes.app version: {version}")