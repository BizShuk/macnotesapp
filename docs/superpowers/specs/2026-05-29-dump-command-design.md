# dump 命令設計規格

## 概述

新增 `dump` 命令，可將 Apple Notes 筆記及其附件完整匯出成 Markdown 檔案，支援三種模式：單篇、資料夾、全部。

---

## 輸出格式

### Markdown 檔案命名

```
{FOLDER}_{note-title}.md
```

範例：
- `Notes_週報.md`
- `Archive_專案文件.md`

標題中若有 `/` 或 `\` 等路徑敏感字元，替換成 `_`。

### 附件標記（連結格式）

```markdown
body 內容...

---

# 附件
[photo.jpg](attachments/photo.jpg)
[pasted-image.png](attachments/pasted-image.png)
```

注意：**不使用 `![]()` 嵌入語法**，而是 `[filename](attachments/filename)` 連結語法。

### Output 目錄結構

```
./dump/
├── Notes_週報.md
├── Notes_待辦事項.md
├── Archive_專案文件.md
└── attachments/
    ├── photo-abc123.jpg
    ├── pasted-image-456.png
    └── document.pdf
```

- `attachments/` 目錄只在有附件時才會建立
- `.md` 檔與 `attachments/` 都建立在 `--out` 指定目錄下

---

## 附件儲存命名

```
attachments/{note_short_id}_{original_name}
```

例如：note ID 為 `x-coredata://.../IMAPNote/p87`，附件名稱 `photo.jpg`
→ 儲存為 `attachments/p87_photo.jpg`

---

## 三種模式

### 模式 1：單篇筆記

```bash
notes dump Notes/p87 --out ./dump/
```

- 解析 `Notes/p87`（使用現有 `resolve_note_id()`）
- 產出單一 `.md` 檔
- 附件儲存於 `--out/attachments/`

### 模式 2：資料夾

```bash
notes dump --folder Notes --out ./dump/
```

- 列舉指定資料夾內所有筆記
- 每篇筆記產出獨立 `.md` 檔
- 所有附件集中於 `--out/attachments/`

### 模式 3：全部

```bash
notes dump --all --out ./dump/
```

- 遍歷所有帳號、所有資料夾
- 每篇筆記產出獨立 `.md` 檔
- 所有附件集中於 `--out/attachments/`

---

## 錯誤處理

| 情境 | 處理方式 |
|------|----------|
| 密碼保護的筆記 | 跳過，顯示警告訊息 |
| 附件儲存失敗 | 顯示錯誤，該 `.md` 仍產出但附件標記指向失敗檔案 |
| 筆記無附件 | 只產生 `.md`，不建立 `attachments/` 目錄 |
| 輸出目錄已存在 | 在該目錄內新增/覆寫（不刪除既有檔案） |
| 輸出目錄建立失敗 | 顯示錯誤並 exit 1 |

---

## 命令列 API

```bash
notes dump [NOTE_ID] [flags]

Positionals:
  NOTE_ID    Note ID in FOLDER/short_id format (e.g. Notes/p87)

Flags:
  --folder   FOLDER    Dump all notes in FOLDER
  --all                  Dump all notes from all accounts
  --out-dir, -o  DIR    Output directory (required)
  --markdown, -m        Force body as markdown (default: convert HTML to markdown)
  --help, -h            Show help
```

`NOTE_ID`、`--folder`、`--all` 三者互斥，只能選一種模式。

---

## 實作位置

```
macnotesapp/cli/commands/dump.py   # 新增
macnotesapp/cli/cli.py            # 新增 dump_group 註冊
```

依附現有：
- `macnotesapp.NotesApp`、`Note`、`Attachment` 實體類別
- `macnotesapp.cli.id_utils.resolve_note_id()`
- `macnotesapp.cli.readable.get_readable_html()`（HTML → Markdown）
- `markdown2`（用於 `--markdown` 模式）
- `markdownify`（用於 HTML → Markdown）

---

## 實作檢查點

- [x] 設計規格（本文）
- [ ] `dump.py` 單篇模式（`NOTE_ID` + `--out-dir`）
- [ ] `dump.py` 資料夾模式（`--folder`）
- [ ] `dump.py` 全部模式（`--all`）
- [ ] 附件下載與儲存
- [ ] Markdown 檔案產出（body + 附件區塊）
- [ ] 密碼保護筆記跳過邏輯
- [ ] CLI 註冊（`cli.py` import + `@click.group`）
- [ ] 文件更新（`apple-notes` skill 更新範例）
