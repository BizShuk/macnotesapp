# macnotesapp — 術語表 (Terminology)

本檔是領域名詞、狀態值與縮寫的單一定義來源。`notes` CLI、Python API 與文件使用同一組正名。

## 識別字 (Identifiers)

本 fork 的核心設計是 `ID-first`：所有寫入操作以 Note ID 定位，不以名稱定位，
因為名稱在 Notes.app 中可重複，以名稱寫入必然有歧義。

| 術語 (Term) | 英文 (English) | 定義 (Definition) | 範例 (Example) |
| --- | --- | --- | --- |
| 筆記識別字 | Note ID | 筆記的唯一識別字，Core Data URI 形式 | `x-coredata://.../ICNote/p87` |
| 截短識別字 | Truncated ID | 顯示用的縮寫形式，`list` 輸出使用它 | `.../ICNote/p87` |
| 部分識別字 | Partial ID | 使用者只輸入尾段，CLI 自動解析回完整 ID | `p87` |
| 識別字解析 | ID Resolution | 把部分或截短識別字還原成完整 ID 的過程 | `id_utils.py` |

## 領域模型 (Domain Model)

| 術語 (Term) | 英文 (English) | 定義 (Definition) | 出處 (Source) |
| --- | --- | --- | --- |
| 筆記應用 | Notes App | Apple Notes.app 的程式化入口 | `notesapp.py` |
| 帳號 | Account | Notes.app 中的一個帳號，例如 iCloud、On My Mac | `notesapp.py` |
| 資料夾 | Folder | 帳號下的筆記分組 | `notesapp.py` |
| 筆記 | Note | 一則筆記；`名稱 (name)` 與 `內文 (body)` 是分開的兩個欄位 | `notesapp.py` |
| 名稱 | Name | 筆記標題。`notes edit --name` 只改標題不動內文 | `cli/commands/` |
| 內文 | Body | 筆記本體 HTML。`notes edit --body` 只改內文不動標題 | `cli/commands/` |

## 存取機制 (Access Mechanism)

| 術語 (Term) | 英文 (English) | 定義 (Definition) | 出處 (Source) |
| --- | --- | --- | --- |
| AppleScript 橋接 | AppleScript Bridge | 驅動 Notes.app 的實際機制 | `macnotesapp_applescript.py` |
| 嵌入腳本 | Embedded Script | AppleScript 原始碼的 Python 字串常數版本 | `macnotesapp.applescript` → `macnotesapp_applescript.py` |
| 富文字剝除 | Rich Markup Stripping | 把筆記 HTML 轉為純文字或 Markdown 的處理 | `docs/strip_rich_markup.py` |

> `維護規則`：`.applescript` 是人工編輯的原始碼，`_applescript.py` 是嵌入版本。
> 改了前者必須同步後者。

## 輸出格式 (Output Formats)

| 格式 (Format) | 使用情境 (Use Case) |
| --- | --- |
| 預設 | 給人閱讀，tab 分隔 |
| `--json` | LLM workflow 與腳本 |
| `--id-only` | shell pipeline，只輸出識別字 |
| `--format markdown` | `notes get` 的可讀輸出，名稱與內文明確分隔 |

## 結束碼 (Exit Codes)

| 值 | 意義 |
| --- | --- |
| `0` | 成功 |
| `1` | 錯誤（找不到、參數無效等） |
| `130` | 使用者中斷 (Ctrl+C) |

## 專案定位 (Fork Context)

本 repo 是 `RhetTbull/macnotesapp` 的修改版，差異在 ID-first CLI 重新設計。
上游行為與本 fork 行為不一致時，以本 repo 文件為準；
引用上游文件時必須標明是上游行為。
