# Extract Base64 Images from Note Body in Dump

## Context

When dumping notes to Markdown, the note HTML body may contain `<img src="data:image/png;base64,...">` tags with embedded images. Currently `markdownify` converts these to `![](data:image/png;base64,...)` which are useless as they can't be rendered as local files.

**Goal:** Extract base64 images from the HTML body before markdown conversion, save them to `attachments/`, and replace the data URIs with local paths so the resulting Markdown contains `![alt](attachments/filename)` which renders as local images.

---

## Implementation

### Changes: `macnotesapp/cli/commands/dump.py`

**Add helper function `_extract_body_images`:**

```python
import base64
import hashlib
import re

def _extract_body_images(html: str, attachments_dir: pathlib.Path) -> tuple[str, list[str]]:
    """Extract base64 images from HTML, save to attachments/, replace src with local path.

    Returns:
        (modified_html, list of saved filenames)
    """
    pattern = r'<img([^>]+)src="data:image/([^;]+);base64,([^"]+)"([^>]*)(/?>)'
    saved = []

    def replace(match):
        attrs_before = match.group(1)  # alt text etc
        mime = match.group(2)          # png, jpeg, gif, etc
        b64_data = match.group(3)
        attrs_after = match.group(4)
        closing = match.group(5)

        # Build alt text from alt attribute if present
        alt_match = re.search(r'alt="([^"]*)"', attrs_before + attrs_after)
        alt = alt_match.group(1) if alt_match else ""

        try:
            image_data = base64.b64decode(b64_data)
        except Exception:
            return match.group(0)  # keep original if decode fails

        # Unique filename from hash of data (dedupes identical images)
        data_hash = hashlib.sha256(image_data).hexdigest()[:16]
        ext = mime if mime in ("png", "jpeg", "gif", "webp", "bmp") else "png"
        filename = f"body_{data_hash}.{ext}"
        filepath = attachments_dir / filename

        attachments_dir.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(image_data)
        saved.append(filename)

        return f'<img{attrs_before}src="attachments/{filename}"{attrs_after}{closing}>'

    modified = re.sub(pattern, replace, html)
    return modified, saved
```

**Modify `_dump_note`:**

In `_dump_note`, before `body_md = html2md(note.body)`:

```python
# Extract and save base64 body images first
body_with_local_paths, body_images = _extract_body_images(
    note.body, out_dir / "attachments"
)
body_md = html2md(body_with_local_paths)
saved_attachments.extend(body_images)
```

The `body_images` list (e.g. `["body_abc123.png", "body_def456.jpg"]`) should be prepended to the attachment lines section with `![filename](attachments/filename)` format.

---

## Key Design Decisions

- **Deduplication by hash:** SHA256(data)[:16] ensures identical images across body/attachments are only saved once
- **Filename prefix `body_`:** Distinguishes body-extracted images from attachment-extracted ones
- **Error handling:** If base64 decode fails, keep original data URI (no regression)
- **Overwrite safety:** `exist_ok=True` on mkdir, SHA256 hash ensures same data → same filename
- **Not in `html2md` output loop:** Body images handled separately from Note.attachments to avoid double-processing

---

## Verification

```bash
rm -rf /tmp/test3
uv run notes dump Notes/p635 -o /tmp/test3
cat /tmp/test3/Notes_Temp\ Note.md | grep -E "^!\[" | head -10
# Should see ![body_hash.png] in the body, not data:image
ls /tmp/test3/attachments/ | grep "^body_"
# Should list saved body image files
```
