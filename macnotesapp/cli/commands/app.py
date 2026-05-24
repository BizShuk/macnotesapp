"""App subcommand for Notes.app control"""

import click
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