# MacNotesApp

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->

[![All Contributors](https://img.shields.io/badge/all_contributors-4-orange.svg?style=flat-square)](#contributors-)

<!-- ALL-CONTRIBUTORS-BADGE:END -->

> **Fork Note:** This is a modified version of the original [RhetTbull/macnotesapp](https://github.com/RhetTbull/macnotesapp) with ID-first CLI redesign. pushed to [bizshuk/macnotesapp](https://github.com/bizshuk/macnotesapp)

Work with Apple MacOS Notes.app from the command line. Also includes python interface for scripting Notes.app from your own python code.

## Installation

The recommended way to install `macnotesapp` is via the [uv](https://github.com/astral-sh/uv) python package manager tool.

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Upgrade if needed: `uv self update`

### Install from GitHub

```bash
uv tool install git+https://github.com/bizshuk/macnotesapp.git
```

Run without installing: `uvx git+https://github.com/bizshuk/macnotesapp.git`

### Install from local clone

```bash
git clone https://github.com/bizshuk/macnotesapp.git
cd macnotesapp
uv sync
uv run notes --help
```

### Install via Homebrew (Apple Silicon)

```bash
brew tap bizshuk/macnotesapp https://github.com/bizshuk/macnotesapp
brew update
brew install macnotesapp
```

**Note**: Currently tested on MacOS 10.15.7/Catalina and 13.1/Ventura.

## ID-First CLI Design

This fork implements **ID-first architecture** — all write operations use Note ID instead of name to avoid ambiguity.

### Key Concepts

- **Note ID**: Unique identifier like `x-coredata://.../ICNote/p87`
- **Truncated ID**: Display format `.../ICNote/p87` (displayed by `list`)
- **Partial ID**: You can use just `p87` — CLI auto-resolves to full ID

### Typical Workflow

```bash
# 1. Find note ID
notes list --text "週報"

# 2. Get content (shows name + body clearly separated)
notes get p87 --format markdown

# 3. Update content
notes edit p87 --body "新內容"

# 4. Or update name only
notes edit p87 --name "新標題"
```

### Output Formats

| Format | Use Case |
| --- | --- |
| Default | Human-readable, tab-separated |
| --json | LLM workflows, scripting |
| --id-only | Shell pipelines |

### Exit Codes

- `0` — Success
- `1` — Error (not found, invalid args, etc.)
- `130` — User interrupted (Ctrl+C)

## Documentation

Full documentation available at [https://RhetTbull.github.io/macnotesapp/](https://RhetTbull.github.io/macnotesapp/)

## Command Line Usage

<!-- [[[cog
import cog
from macnotesapp.cli import cli_main
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli_main, ["--help"])
help = result.output.replace("Usage: cli-main", "Usage: notes")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: notes [OPTIONS] COMMAND [ARGS]...

  notes: work with Apple Notes on the command line.

Options:
  -v, --version  Show the version and exit.
  -h, --help     Show this message and exit.

Commands:
  accounts  Print information about Notes accounts.
  add       Add new note.
  app       Control Notes.app.
  attach    Manage note attachments.
  config    Configure default settings for account, editor, etc.
  delete    Delete a note by ID.
  edit      Edit a note's name and/or body by ID.
  get       Get note content by ID.
  list      List notes with optional filters.
  mkdir     Create a new folder.
  move      Move a note to a different folder by ID.
  rename    Rename a note by ID.
  rmdir     Delete a folder.
  selected  Get the note currently selected in Notes.app UI.

```
<!-- [[[end]]] -->

For full command reference, see [README.cli.md](./README.cli.md).

## Python Usage

<!-- [[[cog
import cog
with open("examples/example.py") as f:
    example = f.read()
cog.out(
    "```python\n{}\n```".format(example)
)
]]] -->
```python
"""Example code for working with macnotesapp"""

from macnotesapp import NotesApp

# NotesApp() provides interface to Notes.app
notesapp = NotesApp()

# Get list of notes (Note objects for each note)
notes = notesapp.notes()
note = notes[0]
print(
    note.id,
    note.account,
    note.folder,
    note.name,
    note.body,
    note.plaintext,
    note.password_protected,
)

print(note.asdict())

# Get list of notes for one or more specific accounts
notes = notesapp.notes(accounts=["iCloud"])

# Create a new note in default folder of default account
new_note = notesapp.make_note(
    name="New Note", body="This is a new note created with #macnotesapp"
)

# Create a new note in a specific folder of a specific account
account = notesapp.account("iCloud")
account.make_note(
    "My New Note", "This is a new note created with #macnotesapp", folder="Notes"
)

# If working with many notes, it is far more efficient to use the NotesList object
# Find all notes with "#macnotesapp" in the body
noteslist = notesapp.noteslist(body=["#macnotesapp"])

print(f"There are {len(noteslist)} notes with #macnotesapp in the body")

# List of names of notes in noteslist
note_names = noteslist.name
print(note_names)

```
<!-- [[[end]]] -->

## See Also

- [apple-notes-parser](https://github.com/RhetTbull/apple-notes-parser): Reads data directly from the Apple Notes database. Read-only but is faster than using the AppleScript API. Supports tags and folders.
- [mcp-apple-notes-py](https://github.com/mcolyer/mcp-apple-notes-py): MCP server that uses macnotesapp and apple-notes-parser; provides LLMs access to your notes.

## Known Issues and Limitations

- Password protected notes are not supported; unlocked password-protected notes can be accessed but locked notes cannot
- Notes containing tags (#tagname) can be read but the tags will be stripped from the body of the note
- Tags cannot be added to notes and will show up as plaintext if added manually with macnotesapp
- Currently, only notes in top-level folders are accessible to `macnotesapp` (#4)
- Attachments are fully supported via `notes attach` command

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/chadmando"><img src="https://avatars.githubusercontent.com/u/20407042?v=4?s=100" width="100px;" alt="chadmando"/><br /><sub><b>chadmando</b></sub></a><br /><a href="#userTesting-chadmando" title="User Testing">📓</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/JonathanDoughty"><img src="https://avatars.githubusercontent.com/u/1918593?v=4?s=100" width="100px;" alt="JonathanDoughty"/><br /><sub><b>JonathanDoughty</b></sub></a><br /><a href="https://github.com/RhetTbull/macnotesapp/issues?q=author%3AJonathanDoughty" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://skife.org/"><img src="https://avatars.githubusercontent.com/u/1291?v=4?s=100" width="100px;" alt="Brian McCallister"/><br /><sub><b>Brian McCallister</b></sub></a><br /><a href="https://github.com/RhetTbull/macnotesapp/commits?author=brianm" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://twitter.com/furman"><img src="https://avatars.githubusercontent.com/u/468007?v=4?s=100" width="100px;" alt="Andrew Furman"/><br /><sub><b>Andrew Furman</b></sub></a><br /><a href="https://github.com/RhetTbull/macnotesapp/commits?author=andrewfurman" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
