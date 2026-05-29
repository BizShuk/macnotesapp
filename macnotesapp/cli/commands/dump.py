"""dump command for macnotesapp - export notes to Markdown with attachments"""

import base64
import hashlib
import pathlib
import re
from urllib.parse import urlparse

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


def _unify_body_link_text(body_md: str, url_to_linktext: dict) -> str:
    """Replace link text in body markdown with attachment name for matching URLs.

    Handles three cases:
    - [text](url) → replace text with attachment name if in map
    - [](url) → replace empty text with attachment name
    - <https://...> → convert bare URL to [domain](url)
    Skips image embeds ![alt](url).
    """
    def replace_link(match):
        text = match.group(1)
        url = match.group(2)
        if url in url_to_linktext:
            return f"[{url_to_linktext[url]}]({url})"
        return match.group(0)

    def replace_bare_url(match):
        url = match.group(1)
        if url in url_to_linktext:
            return f"[{url_to_linktext[url]}]({url})"
        return f"[{_url_domain(url)}]({url})"

    # Pass 1: replace [text](url) and [](url) with attachment name
    pattern = r'\[([^\]]*)\]\((https?://[^)]+)\)'
    body_md = re.sub(pattern, replace_link, body_md)

    # Pass 2: convert bare <https://...> URLs to [domain](url)
    body_md = re.sub(r'<(https?://[^>]+)>', replace_bare_url, body_md)

    return body_md


def _url_domain(url: str) -> str:
    """Extract clean domain name from URL for use as link text."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    # Remove leading www.
    return domain.lstrip("www.")


def _add_trailing_spaces(text: str) -> str:
    """Add two trailing spaces to each non-empty line for proper markdown line breaks."""
    lines = text.splitlines()
    if not lines:
        return ""
    return "".join(f"{line}  \n" for line in lines if line.strip())


_IMAGE_MIME_TO_EXT = {
    "png": "png", "jpeg": "jpg", "gif": "gif", "webp": "webp", "bmp": "bmp"
}


def _convert_tt_blocks_to_pre(html: str) -> str:
    """Convert consecutive <div><tt>...</tt></div> blocks to <pre> blocks.

    Apple Notes uses <tt> (teletype) for monostyled/code blocks.
    Markdownify doesn't handle <tt> as code blocks, so we pre-convert
    consecutive <tt> blocks to <pre> which markdownify handles correctly.
    """
    # Replace <br> within tt blocks with newlines for proper line breaks
    html = re.sub(r'<br\s*/?>', '\n', html)

    # Find all <div><tt>...</tt></div> blocks
    tt_pattern = r'<div><tt>(.*?)</tt></div>'
    matches = list(re.finditer(tt_pattern, html, re.DOTALL))

    if not matches:
        return html

    # Group consecutive matches (with only whitespace/newlines between)
    groups = []
    current_group = [matches[0]]

    for i in range(1, len(matches)):
        prev_end = matches[i - 1].end()
        curr_start = matches[i].start()
        between = html[prev_end:curr_start]
        if between.strip() == '' or between.strip() == '\n':
            current_group.append(matches[i])
        else:
            groups.append(current_group)
            current_group = [matches[i]]
    groups.append(current_group)

    # Replace each group with a <pre> block
    result = html
    offset = 0
    for group in groups:
        contents = []
        for m in group:
            content = m.group(1)
            # Decode common HTML entities
            content = content.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&')
            contents.append(content.strip())

        combined = '\n'.join(contents)
        replacement = f'<pre>{combined}</pre>'

        first_match = group[0]
        last_match = group[-1]
        start = first_match.start() + offset
        end = last_match.end() + offset

        result = result[:start] + replacement + result[end:]
        offset += len(replacement) - (end - start)

    return result


def _extract_body_images(html: str, attachments_dir: pathlib.Path) -> tuple[str, list[str]]:
    """Extract base64 images from HTML, save to attachments/, replace src with local path.

    Returns:
        (modified_html, list of saved filenames)
    """
    pattern = r'<img([^>]*?)src="data:image/([^;]+);base64,([^"]+)"([^>]*?)(/?>)'
    saved = []

    def replace(match):
        attrs_before = match.group(1)
        mime = match.group(2)
        b64_data = match.group(3)
        attrs_after = match.group(4)
        closing = match.group(5)

        try:
            image_data = base64.b64decode(b64_data)
        except Exception:
            return match.group(0)  # keep original on decode failure

        data_hash = hashlib.sha256(image_data).hexdigest()[:16]
        ext = _IMAGE_MIME_TO_EXT.get(mime.lower(), "png")
        filename = f"body_{data_hash}.{ext}"
        filepath = attachments_dir / filename

        attachments_dir.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(image_data)
        saved.append(filename)

        return f'<img{attrs_before}src="attachments/{filename}"{attrs_after}{closing}>'

    modified = re.sub(pattern, replace, html)
    return modified, saved


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

    # Extract and save base64 body images first
    body_with_local_paths, body_images = _extract_body_images(
        note.body, out_dir / "attachments"
    )
    # Convert <tt> (monostyled) blocks to <pre> for proper fenced code block output
    body_with_pre = _convert_tt_blocks_to_pre(body_with_local_paths)
    body_md = html2md(body_with_pre)

    # Build URL → link_text map from URL attachments (for body link text unification)
    url_to_linktext = {}
    for att in note.attachments:
        att_url = att.URL
        if att_url and att_url.startswith("http") and not _is_image_filename(att_url):
            url_to_linktext[att_url] = att.name if att.name else _url_domain(att_url)

    # Replace body link text with attachment name (except image embeds)
    body_md = _unify_body_link_text(body_md, url_to_linktext)

    # Build attachment section
    attachment_lines = []
    saved_attachments = list(body_images)

    for att in note.attachments:
        att_url = att.URL
        is_url_attachment = att_url and att_url.startswith("http")

        if is_url_attachment:
            # URL attachment — embed as image if URL ends with image extension
            link_text = att.name if att.name else _url_domain(att_url)
            if _is_image_filename(att_url):
                attachment_lines.append(f"![{link_text}]({att_url})")
            else:
                attachment_lines.append(f"[{link_text}]({att_url})")
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

    # Write .md file (each line ends with double space for proper markdown line breaks)
    lines = [f"# {note.name}  \n", _add_trailing_spaces(body_md)]
    if attachment_lines:
        lines.append("  \n---\n  \n# 附件  \n")
        lines.extend(f"{line}  \n" for line in attachment_lines)

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