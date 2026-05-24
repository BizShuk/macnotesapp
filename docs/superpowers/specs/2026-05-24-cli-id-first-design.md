# macnotesapp CLI ID-first 重構設計

**日期：** 2026-05-24  
**版本：** 0.9.0（重構）

---

## 概述

將 CLI 從 name-based 操作改為 ID-first 操作。所有寫入命令必須使用 Note ID 指定目標筆記，徹底移除名稱歧義。

---

## 設計原則

```
1. ID 是唯一身分        — 所有寫入操作必須給 ID
2. list 提供 ID         — 探索階段用，輸出永遠包含 ID
3. 不依名稱猜筆記       — 同名歧義一律報錯
4. JSON 全面支援        — LLM workflow 一等公民
5. 子命令分組           — 相關操作用 sub command（attach/app）
6. 簡單退出碼           — 0 成功 / 1 失敗 / 130 中斷
```

---

## 命令地圖

```
notes
├── 探索（取得 ID）
│   ├── list                ← 列出/搜尋（永遠顯示 ID）
│   └── selected            ← 目前 UI 選取的筆記
│
├── 讀取（需 ID）
│   └── get ID
│
├── 寫入（需 ID）
│   ├── add                 ← 建立新筆記（輸出新 ID）
│   ├── edit ID
│   ├── rename ID NEW_NAME
│   ├── move ID --folder DEST
│   └── delete ID
│
├── 附件（需 ID）
│   └── attach
│       ├── list ID
│       ├── add ID FILE
│       └── save ID ATTACHMENT_ID --out-dir DIR
│
├── 資料夾
│   ├── mkdir FOLDER
│   └── rmdir FOLDER
│
├── 帳戶
│   └── accounts
│
├── Notes.app 控制
│   └── app
│       ├── activate
│       ├── quit
│       └── version
│
└── 設定
    └── config
```

---

## 詳細命令規格

### 探索類

#### `notes list [OPTIONS]`

| Option | 說明 |
|--------|------|
| `--name TEXT` | title 包含 |
| `--body TEXT` | body 包含 |
| `--text TEXT` | name 或 body 包含 |
| `--account ACC` | 限定帳戶（可重複） |
| `--folder FOLDER` | 限定資料夾（可重複） |
| `--password-protected` | 只顯示加密筆記（布林開關） |
| `--json` | JSON 輸出 |
| `--id-only` | 只輸出 ID（每行一個，給 pipeline） |

**預設輸出（tab 分隔）：**
```
ID              ACCOUNT/FOLDER    NAME            MOD_DATE         PWD
.../IMAPNote/p87  iCloud/Notes     會議紀錄         2026-05-24T10:30  -
.../IMAPNote/p91  iCloud/Work      密碼筆記         2026-05-23T15:20  🔒
```

**`--json` 輸出：**
```json
[
  {
    "id": ".../IMAPNote/p87",
    "name": "會議紀錄",
    "account": "iCloud",
    "folder": "Notes",
    "creation_date": "2026-01-15T10:30:00",
    "modification_date": "2026-05-24T10:30:00",
    "password_protected": false
  }
]
```

**`--id-only` 輸出：**
```
.../IMAPNote/p87
.../IMAPNote/p91
```

#### `notes selected [OPTIONS]`

| Option | 說明 |
|--------|------|
| `--json` | JSON 輸出 |
| `--id-only` | 只輸出 ID |

---

### 讀取類

#### `notes get ID [OPTIONS]`

依 ID 取得筆記內容。**必須給 ID，不接受名稱。**

| Option | 說明 |
|--------|------|
| `--format FMT` | `html` \| `plaintext` \| `markdown` \| `json`，預設 markdown |
| `--show` | 讀取後在 Notes.app 中顯示 |

---

### 寫入類

#### `notes add [OPTIONS] [NOTE]`

建立新筆記。**唯一不需要 ID 的寫入命令；預設輸出新 ID 於 stdout 第一行。**

| Option | 說明 |
|--------|------|
| `--file FILE` | 從檔案讀內容 |
| `--url URL` | 從 URL 抓取可讀內容 |
| `--html` | body 為 HTML |
| `--markdown` | body 為 Markdown |
| `--plaintext` | body 為純文字（預設） |
| `--edit` | 建立前開啟編輯器 |
| `--account ACC` | 目標帳戶（預設由 config） |
| `--folder FOLDER` | 目標資料夾（預設由 config） |
| `--show` | 建立後在 UI 顯示 |
| `--json` | 改用 JSON 格式輸出新筆記資訊 |

**預設輸出（單行 ID）：**
```
x-coredata://19B82A76-B3FE-4427-9C5E-5107C1E3CA57/IMAPNote/p87
```

#### `notes edit ID [OPTIONS]`

| Option | 說明 |
|--------|------|
| `--body TEXT` | 直接設定 body（不開編輯器） |
| `--html` | body 為 HTML |
| `--markdown` | body 為 Markdown |

無 `--body` 時開啟編輯器，預載目前內容轉成 Markdown。

#### `notes rename ID NEW_NAME`

重命名筆記。

#### `notes move ID --folder DEST`

移動到指定資料夾。

#### `notes delete ID [--yes]`

刪除筆記。`--yes` 跳過確認。

---

### 附件類

#### `notes attach list ID [--json]`

列出筆記的所有附件。

**預設輸出：**
```
ATTACHMENT_ID  NAME  MODIFICATION_DATE  [URL]
```

#### `notes attach add ID FILE_PATH [--json]`

加附件到指定筆記。預設輸出新附件 ID。

#### `notes attach save ID ATTACHMENT_ID --out-dir DIR`

匯出附件到磁碟。

---

### 資料夾類

```
notes mkdir FOLDER [--account ACC]
notes rmdir FOLDER [--account ACC] [--yes]
```

---

### 帳戶與 App 控制

```
notes accounts [--json]
notes app activate
notes app quit
notes app version
notes config
```

---

## ID 格式

**顯示格式（截斷）：** `.../IMAPNote/p87`（UUID 省略，只顯示 entity type + record number）

**完整格式（内部使用）：** `x-coredata://<AccountUUID>/IMAPNote/p87`

ID 在整個 Notes.app 唯一（UUID 內嵌帳戶資訊）。

---

## 輸出格式統一規範

### 預設（人類可讀，tab 分隔）

```
ID              ACCOUNT/FOLDER    NAME            MOD_DATE         PWD
.../IMAPNote/p87  iCloud/Notes     會議紀錄         2026-05-24T10:30  -
.../IMAPNote/p91  iCloud/Work      密碼筆記         2026-05-23T15:20  🔒
```

### `--json` 輸出（給 LLM/腳本）

```json
[
  {
    "id": ".../IMAPNote/p87",
    "name": "會議紀錄",
    "account": "iCloud",
    "folder": "Notes",
    "creation_date": "2026-01-15T10:30:00",
    "modification_date": "2026-05-24T10:30:00",
    "password_protected": false
  }
]
```

### `--id-only` 輸出（給 shell pipeline）

```
.../IMAPNote/p87
.../IMAPNote/p91
```

---

## 退出碼

| Exit Code | 意義 |
|-----------|------|
| 0 | 成功 |
| 1 | 失敗（找不到、參數錯誤、Notes.app 通訊失敗等所有錯誤情境） |
| 130 | 使用者中斷（Ctrl+C，由 shell 慣例決定） |

---

## 移除的命令

| 舊命令 | 替代方式 |
|--------|---------|
| `notes cat NAME` | `notes list --name NAME` → `notes get ID` |
| `notes dump` | `notes list --json` |
| `notes dump --selected` | `notes selected --json` |
| `notes find` | 合併入 `notes list` |

---

## 命令簽名變更彙整

| 命令 | 原簽名 | 新簽名 |
|------|--------|--------|
| `cat` | `cat NAME` | 移除，用 `get ID` |
| `dump` | `dump [--selected] [--no-body]` | 移除，用 `list --json` |
| `list` | `list [TEXT]` | `list [--name --body --text --account --folder --password-protected --json --id-only]` |
| `get` | （新增） | `get ID [--format --show]` |
| `selected` | （新增） | `selected [--json --id-only]` |
| `rename` | `rename OLD NEW [--account]` | `rename ID NEW_NAME` |
| `delete` | `delete NAME [--yes --account]` | `delete ID [--yes]` |
| `edit` | `edit NAME [--body --html --markdown --account]` | `edit ID [--body --html --markdown]` |
| `move` | `move NAME --folder [--account]` | `move ID --folder` |
| `add` | `add [NOTE] [...]` | `add [NOTE] [... --json --show]`，預設輸出新 ID |
| `attach` | （新增） | `attach {list, add, save} ID ...` |
| `app` | （新增） | `app {activate, quit, version}` |
| `accounts` | `accounts [--json]` | 不變 |
| `mkdir/rmdir` | 不變 | 不變 |
| `config` | 不變 | 不變 |

---

## 典型工作流範例

### 工作流 A：人類找出某筆記並編輯

```bash
notes list --text "週報"
# 看輸出挑出目標 ID
notes edit .../IMAPNote/p87 --markdown --body "新內容"
```

### 工作流 B：LLM 自動化更新

```bash
# 1. 找筆記
NOTE_ID=$(notes list --name "週報 2026 Q2" --id-only | head -1)

# 2. 讀內容
notes get "$NOTE_ID" --format markdown > /tmp/note.md

# 3. LLM 加工 /tmp/note.md

# 4. 寫回
notes edit "$NOTE_ID" --markdown --body "$(cat /tmp/note.md)"
```

### 工作流 C：批次匯出附件

```bash
notes list --account iCloud --id-only | while read id; do
  notes attach list "$id" --json | jq -r '.[].id' | while read aid; do
    notes attach save "$id" "$aid" --out-dir ./backup
  done
done
```

### 工作流 D：建立新筆記並追蹤其 ID

```bash
NEW_ID=$(notes add --markdown "新筆記")
notes attach add "$NEW_ID" /path/to/photo.jpg
```

---

## 評估資訊

| 項目 | 數值 |
|------|------|
| 新增命令數 | 6 個（`get`, `selected`, `attach×3`, `app×3` 合 1 群） |
| 修改命令數 | 6 個（`list`, `rename`, `edit`, `delete`, `move`, `add`） |
| 移除命令數 | 2 個（`cat`, `dump`） |
| 預估程式碼增量 | ~250 行 |
| 預估工時 | `1-1.5 天` |

---

## 鎖定的設計決策

| 編號 | 議題 | 決策 |
|------|------|------|
| 1 | 命令分組 | 子命令群（attach、app） |
| 2 | list vs find | 合併為 list，移除 find |
| 3 | `get` 預設格式 | markdown |
| 4 | `add` 輸出 | 預設輸出新 ID（單行）；可加 `--json` 取完整資訊 |
| 5 | 退出碼 | 0 / 1（130 保留給 Ctrl+C） |
| 6 | `--password-protected` | 布林開關（只篩選 true） |
| 7 | ID 顯示格式 | 截斷 `.../IMAPNote/p87` |
| 8 | 密碼保護顯示 | 單獨 PWD column，`🔒` 表示 |