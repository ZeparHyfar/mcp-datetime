# mcp-datetime

[![PyPI](https://img.shields.io/pypi/v/mcp-datetime.svg)](https://pypi.org/project/mcp-datetime/)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/downloads/)
[![MCP SDK](https://img.shields.io/badge/mcp-2.x-green.svg)](https://github.com/modelcontextprotocol/python-sdk)
[![test](https://github.com/ZeparHyfar/mcp-datetime/actions/workflows/test.yml/badge.svg)](https://github.com/ZeparHyfar/mcp-datetime/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[English](README.md) | 日本語

Claude Desktop Application用のMCPサーバーとして実装された日時フォーマットサービスです。様々な形式での日時文字列生成をサポートしています。

> **注意**: 普段の利用はmacOSです。自動テストはLinuxとWindowsでも実行しています。

## 前提条件

mcp-datetimeを使用する前に、以下のツールがインストールされていることを確認してください：

- [uv](https://docs.astral.sh/uv/)（`uvx` を含みます）。必要に応じてuvxが適切なPython（3.10以降）を取得します。

## 特徴

- ✨ 各種の日時フォーマットをサポート
- 🇯🇵 日本語対応（和暦・日本語の曜日を含む）
- 🧩 macOS・Linux・Windowsで同じ結果になる自由な書式
- 📁 ファイル名生成に最適化された形式
- 🌏 IANAのタイムゾーンを指定可能（`Asia/Tokyo`、`UTC`、`America/New_York` など）
- 🔧 Claude Desktop Appとのシームレスな連携

## MCPサーバーコンポーネント

### ツール

このサーバーは4つのツールを実装しています：

- `get_datetime`: 現在の日時を様々な形式で取得
  - `format`（必須）: 形式名（[サポートされている形式](#サポートされている形式)を参照）、または `%` を含む自由な書式（[自由な書式](#自由な書式)を参照）
  - `timezone`（省略可）: `Asia/Tokyo`、`UTC`、`America/New_York` などのIANAタイムゾーン名。省略した場合は実行しているマシンのタイムゾーンを使います
  - 指定された形式でフォーマットされた日時文字列を返します
- `convert_time`: 時刻・日時をタイムゾーン間で変換
  - `time`（必須）、`target_timezone`（必須）、`source_timezone`（省略可、省略時はローカル）、`format`（省略可、省略時は `datetime`）
  - 変換元と変換先のタイムゾーン・UTCとの差・曜日と、時差を返します。夏時間の切り替えで存在しない時刻や2回ある時刻になる場合は注意書きを付けます
- `shift_datetime`: 日時の加算・減算（過去はマイナスで指定）
  - `years`、`months`、`weeks`、`days`、`hours`、`minutes`、`seconds`、省略可の `base`（省略時は現在）、`timezone`、`format`
  - 月・年の加算で月末を超える場合は月末にそろえます（2024-01-31 + 1か月 = 2024-02-29）。日単位は時刻を保ち、時間単位は経過時間として計算します
- `get_datetime_info`: 日時の詳細と、別の日時との差
  - 省略可の `datetime`（省略時は現在）、`reference`（省略時は現在）、`timezone`
  - ISO形式の日時、タイムゾーン、UTCとの差、夏時間かどうか、Unix時刻、曜日（英語・日本語）、和暦、年の何日目、ISO週番号、四半期、うるう年かどうか、その月の日数、基準との日数・秒数の差（例: 「15日後」）を返します

これらのツールの日時の入力には、`2024-12-10`、`2024-12-10 14:30`、`2024-12-10T14:30:00+09:00`、`2024/12/10`、`2024年12月10日 14時30分`、`令和6年12月10日` や `R6.12.10` などの和暦、`14:30`（今日の時刻）が使えます。

## Claude Codeでの使用方法

```bash
claude mcp add mcp-datetime -- uvx mcp-datetime
```

## Claude Desktop Appでの使用方法

設定ファイルに以下を追加してください：

設定ファイルの場所（macOS）:
`~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mcp-datetime": {
      "command": "uvx",
      "args": ["mcp-datetime"]
    }
  }
}
```

## 最新版への更新

uvxはキャッシュ済みの版を再利用するため、新しい版が公開された後も古い版を起動し続けることがあります。最新版に切り替えるには、次のコマンドでキャッシュを一度削除してから、Claude CodeまたはClaude Desktopを再起動してください。

```bash
uv cache clean mcp-datetime
```

次回の起動時に最新版がダウンロードされます。起動のたびに最新版を確認したい場合は、上記のコマンドや設定の `mcp-datetime` を `mcp-datetime@latest` に置き換えてください。

## インストールについて

ソースコードの確認や開発目的など、パッケージを直接インストールする必要がある場合は、以下の方法でインストールできます：

- PyPIからインストール

  ```bash
  pip install mcp-datetime
  ```

- GitHubのソースコードからインストール

  ```bash
  git clone https://github.com/ZeparHyfar/mcp-datetime.git
  cd mcp-datetime
  pip install -e .
  ```

- 手動でインストールした場合の`claude_desktop_config.json`の例

  ```json
  {
    "mcpServers": {
      "mcp-datetime": {
        "command": "/path/to/your/python",
        "args": ["-m", "mcp_datetime"]
      }
    }
  }
  ```

  "/path/to/your/python"はパッケージをインストールしたPythonインタプリタのパスに置き換えてください
  > （例："/usr/local/bin/python3" や "/Users/username/.pyenv/versions/3.13.0/bin/python3"）

- テストの実行

  ```bash
  uv run --group dev pytest
  ```

## 基本的な使用例

- コマンド形式

  ```
  # 標準的な日時形式
  call datetime-service.get_datetime {"format": "datetime"}
  # 結果: 2024-12-10 00:54:01

  # 日本語形式
  call datetime-service.get_datetime {"format": "datetime_jp"}
  # 結果: 2024年12月10日 00時54分01秒

  # ファイル名形式
  call datetime-service.get_datetime {"format": "filename_md"}
  # 結果: 20241210005401.md

  # 和暦
  call datetime-service.get_datetime {"format": "date_wareki"}
  # 結果: 令和6年12月10日

  # 別のタイムゾーン
  call datetime-service.get_datetime {"format": "datetime", "timezone": "America/New_York"}
  # 結果: 2024-12-09 10:54:01

  # 自由な書式
  call datetime-service.get_datetime {"format": "%Y/%-m/%-d (%a)"}
  # 結果: 2024/12/10 (Tue)

  # タイムゾーンの変換
  call datetime-service.convert_time {"time": "2024-12-10 14:30", "source_timezone": "Asia/Tokyo", "target_timezone": "America/New_York"}
  # 結果: 変換元 2024-12-10 14:30:00（+09:00）、変換先 2024-12-10 00:30:00（-05:00）、時差 -14:00

  # 1か月後を和暦で
  call datetime-service.shift_datetime {"base": "令和6年1月31日", "months": 1, "format": "date_wareki"}
  # 結果: 令和6年2月29日

  # ある日まであと何日
  call datetime-service.get_datetime_info {"datetime": "2024-12-25", "reference": "2024-12-10"}
  # 結果: ... "days_from_reference": 15, "relative": "in 15 days", "relative_jp": "15日後" ...
  ```

- Claudeデスクトップアプリのプロンプト例

  - User

    ```
    今の時刻をdate_slash形式で教えてください
    ```

  - Claude

    ```
    date_slash形式で現在の日付を取得します。

    現在の日付は 2024/12/12 です。
    ```

## サポートされている形式

| 形式名       | 例                          | 説明                     |
| ------------ | --------------------------- | ------------------------ |
| date         | 2024-12-10                  | 標準的な日付形式         |
| date_slash   | 2024/12/10                  | スラッシュ区切りの日付   |
| date_jp      | 2024年12月10日              | 日本語の日付形式         |
| datetime     | 2024-12-10 00:54:01         | 標準的な日時形式         |
| datetime_jp  | 2024年12月10日 00時54分01秒 | 日本語の日時形式         |
| datetime_t   | 2024-12-10T00:54:01         | T区切りの日時形式        |
| compact      | 20241210005401              | ID用のコンパクト形式     |
| compact_date | 20241210                    | 日付のみのコンパクト形式 |
| compact_time | 005401                      | 時刻のみのコンパクト形式 |
| filename_md  | 20241210005401.md           | Markdownファイル名形式   |
| filename_txt | 20241210005401.txt          | テキストファイル名形式   |
| filename_log | 20241210005401.log          | ログファイル名形式       |
| iso          | 2024-12-10T00:54:01+0900    | ISO 8601形式             |
| iso_basic    | 20241210T005401+0900        | 基本ISO形式              |
| log          | 2024-12-10 00:54:01.123456  | マイクロ秒付きログ形式   |
| log_compact  | 20241210_005401             | コンパクトなログ形式     |
| time         | 00:54:01                    | 時刻のみの形式           |
| time_jp      | 00時54分01秒                | 日本語の時刻形式         |
| date_wareki         | 令和6年12月10日                   | 和暦の日付               |
| datetime_wareki     | 令和6年12月10日 00時54分01秒      | 和暦の日時               |
| date_wareki_short   | R6.12.10                          | 和暦の日付（略記）       |
| date_jp_weekday     | 2024年12月10日（火）              | 曜日付きの日本語の日付   |
| datetime_jp_weekday | 2024年12月10日（火） 00時54分01秒 | 曜日付きの日本語の日時   |
| weekday_jp          | 火曜日                            | 日本語の曜日             |

和暦は、日本がグレゴリオ暦を採用した1873年1月1日（明治6年）以降に対応しています。元号の1年目は「元年」と表記します（例: 令和元年5月1日）。ただし `date_wareki_short` では数字で表記します（R1.5.1）。

## 自由な書式

`format` に `%` が含まれている場合は、書式として扱います（200文字まで）。

- 標準の[strftimeの記号](https://docs.python.org/ja/3/library/datetime.html#format-codes): `%Y %m %d %H %I %M %S %f %p %a %A %b %B %j %U %W %G %V %u %w %z %Z %c %x %X %%`
- ゼロを付けない記号（Windowsでも使えます）: `%-m %-d %-H %-I %-M %-S %-j %-y`
- 日本語の記号:

| 記号  | 意味                         | 例（2019年5月1日） |
| ----- | ---------------------------- | ------------------ |
| `%Je` | 元号                         | 令和               |
| `%JE` | 元号のローマ字の頭文字       | R                  |
| `%Jy` | 和暦の年（1年は「元」）      | 元                 |
| `%JY` | 和暦の年（1年も数字）        | 1                  |
| `%Ja` | 曜日                         | 水                 |
| `%JA` | 曜日                         | 水曜日             |

例: `%Je%Jy年%-m月%-d日（%Ja）` → 令和元年5月1日（水）

## デバッグ

MCPサーバーはstdioを介して実行されるため、デバッグが難しい場合があります。[MCP Inspector](https://github.com/modelcontextprotocol/inspector)の使用を推奨します：

- PyPIパッケージを使用する場合

  ```
  npx @modelcontextprotocol/inspector uvx mcp-datetime
  ```

- GitHubからダウンロードしたソースコードを使用する場合

  ```
  git clone https://github.com/ZeparHyfar/mcp-datetime.git
  npx @modelcontextprotocol/inspector uv --directory ./mcp-datetime run mcp-datetime
  ```

## ライセンス

このプロジェクトはMITライセンスの下で提供されています - 詳細は[LICENSE](LICENSE)ファイルを参照してください。
