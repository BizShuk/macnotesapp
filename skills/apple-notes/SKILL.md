---
name: apple-notes
description: Use when working with Apple Notes (macOS Notes.app) from the command line via the `notes` CLI (macnotesapp / bizshuk fork, ID-first design) — listing, reading, creating, editing, deleting, moving notes, managing folders and attachments, or controlling Notes.app. Triggers on requests like "列出我的筆記", "list my Apple notes", "新增備忘錄", "edit a note", "find note containing X", "delete note by ID", "add attachment", "create folder in Notes".
metadata:
  type: reference
  platforms: [macos]
  prerequisites:
    commands: [notes]
---

# Apple Notes CLI (`notes`)

操作 macOS `Notes.app` 的命令列工具。此 fork (`bizshuk/macnotesapp`) 採 `ID-first` 設計：所有寫入類操作（`get` / `edit` / `delete` / `rename` / `move` / `attach`）一律以 `Note ID` 定位，避免同名筆記造成歧義。

## When to Use

需要透過 terminal 對 `Notes.app` 進行以下操作時：

- 查詢／列出筆記（含模糊比對 name、body、folder、account）
- 讀取筆記內容（取得 plaintext / markdown / html / json）
- 新增、編輯、重命名、刪除筆記
- 在資料夾間搬移筆記
- 建立／刪除資料夾
- 管理附件（add / list / save）
- 操控 `Notes.app` 程式本身（activate / quit / version）
- 與「目前 UI 選取的筆記」互動

不要用於：密碼保護鎖定中的筆記（無法存取）；非頂層的子資料夾（目前不支援）。

## Prerequisites

執行前先確認 CLI 已安裝且可呼叫：

```bash
notes --version
# 若無 `notes` 指令，請用以下任一方式安裝：
#   uv tool install git+https://github.com/bizshuk/macnotesapp.git
#   uvx git+https://github.com/bizshuk/macnotesapp.git
#   brew tap bizshuk/macnotesapp https://github.com/bizshuk/macnotesapp && brew install macnotesapp
```

於 macnotesapp 專案原始碼目錄內開發時，改用 `uv run notes ...`。

## Note ID 三種形式（重要）

| 形式 | 範例 | 用途 |
| --- | --- | --- |
| `Full ID` | `x-coredata://A1B2.../ICNote/p87` | 完整 ID，由 `Notes.app` 內部產生 |
| `Truncated ID` | `.../ICNote/p87` | `notes list` 預設輸出格式（人眼好讀）|
| `Partial ID` | `p87` | 只給尾段；CLI 自動解析為 full ID |

寫入類指令三種形式皆可接受，**最常用 `partial ID`**（例：`notes get p87`）。

## Quick Reference

| 指令 | 用途 | 最小範例 |
| --- | --- | --- |
| `notes list` | 列出／搜尋筆記 | `notes list -t "週報"` |
| `notes get ID` | 讀取筆記內容 | `notes get p87` |
| `notes add NOTE` | 新增筆記 | `notes add "標題\n內文"` |
| `notes edit ID` | 編輯名稱／內文 | `notes edit p87 -b "新內容"` |
| `notes rename ID NEW` | 改標題 | `notes rename p87 "新標題"` |
| `notes move ID` | 搬資料夾 | `notes move p87 -f Archive` |
| `notes delete ID` | 刪除筆記 | `notes delete p87 -y` |
| `notes selected` | 取得目前選取的筆記 | `notes selected -i` |
| `notes mkdir NAME` | 建資料夾 | `notes mkdir Archive` |
| `notes rmdir NAME` | 刪資料夾 | `notes rmdir Archive -y` |
| `notes attach add ID FILE` | 新增附件 | `notes attach add p87 ./img.jpg` |
| `notes attach list ID` | 列出附件 | `notes attach list p87` |
| `notes attach save ID AID -o DIR` | 下載附件 | `notes attach save p87 p5631 -o ./out` |
| `notes accounts` | 列帳號 | `notes accounts -j` |
| `notes app activate\|quit\|version` | 控制 Notes.app | `notes app activate` |
| `notes config` | 修改預設值 | `notes config` |

## 典型工作流 (Workflows)

### 工作流 1：找到筆記 → 讀內容 → 編輯

```bash
# 1) 用關鍵字找筆記，記下回傳的 partial ID（例如 p87）
notes list -t "週報"

# 2) 讀內容（預設 markdown，含 name + body 區隔）
notes get p87

# 3) 直接覆寫內文（非互動）
notes edit p87 -b "## 本週進度\n- 完成 X\n- 進行 Y" -m

# 4) 或改標題
notes edit p87 -n "2026 W21 週報"
```

### 工作流 2：管線 (pipe) 自動化

```bash
# 取得所有含 "TODO" 的筆記 ID，逐一刪除（謹慎使用）
notes list -t "TODO" --id-only | while read id; do
  notes delete "$id" --yes
done
```

`--id-only` 輸出純 ID（每行一個），最適合給 shell loop 串接。

### 工作流 3：給 LLM / 腳本消費

```bash
# 用 JSON 格式取得結構化資料
notes list -t "週報" --json
notes get p87 --format json
notes accounts --json
```

### 工作流 4：對「目前 UI 選取的筆記」操作

```bash
# 取得選取筆記的 ID，丟回給其他指令
ID=$(notes selected --id-only)
notes get "$ID"
```

## Per-Command Details

### `notes list` — 搜尋筆記

```bash
notes list                          # 全部
notes list -n "週報"                # 名稱含 "週報"
notes list -b "TODO"                # 內文含 "TODO"
notes list -t "X"                   # 名稱或內文含 "X"
notes list -a iCloud -f Notes       # 限定 account + folder
notes list -p                       # 只顯示密碼保護的
notes list -t "X" --json            # JSON 輸出
notes list -t "X" --id-only         # 只印 ID（給 pipeline 用）
```

`-a` 與 `-f` 皆可重複使用以涵蓋多個帳號／資料夾。

### `notes get` — 讀取筆記

```bash
notes get p87                       # 預設 markdown，含 name + body
notes get p87 -f plaintext          # 純文字
notes get p87 -f html
notes get p87 -f json
notes get p87 --name-only           # 只要標題
notes get p87 --body-only           # 只要內文
notes get p87 -s                    # 讀完順便在 Notes.app 開啟
```

格式：`html` / `plaintext` / `markdown`（預設）/ `json`。

### `notes add` — 新增筆記

```bash
# 單行 = 只有標題
notes add "我的標題"

# 多行 = 第一行作為標題，其餘為內文
notes add $'標題\n內文第一行\n內文第二行'

# 從 stdin
cat file.md | notes add -m

# 從檔案
notes add -F ./draft.md -m

# 從 URL（自動清理為可讀版本）
notes add -u https://example.com/article

# 用 $EDITOR 編輯後再存
notes add -e

# 指定帳號／資料夾
notes add "標題" -a iCloud -f Inbox

# 新增後在 Notes.app 顯示
notes add "標題\n內文" -s

# 內文格式：-m markdown / -h html / -p plaintext（預設）
```

預設輸出新筆記的 `ID`；加 `-j` 可得完整 JSON。

### `notes edit` — 編輯（非互動為主）

```bash
notes edit p87 -b "新內文"           # 只改內文
notes edit p87 -n "新標題"           # 只改標題
notes edit p87 -n "新標題" -b "新內文" -m
notes edit p87 -e                    # 用編輯器互動編輯
```

`-m` / `-h` 控制 body 解讀格式（markdown / html），不加則視為 plaintext。

### `notes rename` — 只改標題

```bash
notes rename p87 "新標題"
```

### `notes move` — 搬到別的資料夾

```bash
notes move p87 -f Archive            # -f 為必填
```

### `notes delete` — 刪除

```bash
notes delete p87                     # 會跳確認
notes delete p87 -y                  # 跳過確認，直接刪
```

### `notes selected` — 目前 UI 選取的筆記

```bash
notes selected                       # 名稱 + ID
notes selected --id-only             # 只印 ID
notes selected --json
```

### `notes mkdir` / `notes rmdir` — 資料夾操作

```bash
notes mkdir "Archive"                # 預設帳號下建
notes mkdir "Archive" -a iCloud      # 指定帳號

notes rmdir "Archive"                # 跳確認
notes rmdir "Archive" -y -a iCloud
```

### `notes attach` — 附件

```bash
notes attach add p87 ./photo.jpg         # 新增附件到筆記
notes attach add p87 ./photo.jpg --json

notes attach list p87                    # 列出附件（含 attachment ID）
notes attach list p87 --json

notes attach save p87 p5631 -o ./out     # 下載指定附件
```

`save` 需要兩個 ID：先 note ID、再 attachment ID（從 `list` 取得），`-o` 為必填。

### `notes accounts` — 帳號

```bash
notes accounts                       # 名稱 + 預設資料夾
notes accounts -j                    # JSON
```

### `notes app` — 控制 Notes.app

```bash
notes app activate                   # 帶到前景
notes app quit                       # 退出
notes app version                    # 顯示 Notes.app 版本
```

### `notes config` — 預設值

```bash
notes config                         # 互動式設定預設 account、editor、預設格式等
```

## Output Formats

| 格式 | 觸發 | 適用場景 |
| --- | --- | --- |
| `Default` | 不加 flag | 人讀，tab 分隔 |
| `JSON` | `--json` / `-j` 或 `-f json` | 給 LLM、腳本消費 |
| `--id-only` | `-i` | shell pipeline 串接 |

`get` 用 `--format json`；其他多數指令用 `--json` / `-j`。

## Exit Codes

| Code | 意義 |
| --- | --- |
| `0` | 成功 |
| `1` | 錯誤（找不到、參數無效等） |
| `130` | 使用者中斷（Ctrl+C） |

寫腳本時可用 `$?` 判斷。

## Common Mistakes

| 錯誤 | 修正 |
| --- | --- |
| 用筆記「名稱」當參數呼叫 `edit` / `delete` | 寫入類指令一律吃 `Note ID`，先 `notes list -t "..."` 取 ID |
| `notes move p87`（缺 `-f`）| `-f, --folder` 是必填，補上目的資料夾 |
| 中文／含空白標題沒有 quote | 用雙引號包起來：`notes add "週報 W21"` |
| 期待 `notes edit` 開編輯器但只給 `-b`/`-n` | 非互動模式只覆寫；要互動加 `-e` |
| 用了 `--markdown` 但 body 是純文字混 `#` 符號 | 不需要 markdown 解析時別加 `-m`，預設 plaintext 即可 |
| 想刪附件 | 目前 CLI 不支援，需在 `Notes.app` UI 操作 |
| 想存取子資料夾筆記 | 目前 CLI 僅支援頂層資料夾 |
| 在密碼保護筆記上呼叫 `get` | 鎖定中無法讀取；需先在 `Notes.app` UI 解鎖 |
| 用 truncated ID（`.../ICNote/p87`）忘記引號 | shell 會解讀 `/`，務必整段加雙引號，或直接用 `p87` |

## Tips for Composing with Other Tools

- 串 `jq` 解析：`notes list -t "X" --json | jq '.[].id'`
- 批次匯出：`notes list --id-only | while read id; do notes get "$id" -f markdown > "$id.md"; done`
- 與 `selected` 配合：在 `Notes.app` 點選一則筆記後，從 terminal 用 `notes selected -i` 抓 ID 直接操作

## See Also

- 上游：[`RhetTbull/macnotesapp`](https://github.com/RhetTbull/macnotesapp)
- 此 fork：[`bizshuk/macnotesapp`](https://github.com/bizshuk/macnotesapp)
- 文件站：[https://RhetTbull.github.io/macnotesapp/](https://RhetTbull.github.io/macnotesapp/)
- 專案完整 CLI 參考：[README.cli.md](../../README.cli.md)
