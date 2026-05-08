# Daily Report Agent — Workspace Guidelines

このリポジトリは「日報を自動で書いてくれるエージェント」です。  
**人間と会話するのは [日報アシスタント](.github/agents/daily-report.agent.md) エージェント**、実際の時間記録/集計/出力は **Python CLI ([src/daily_report.py](src/daily_report.py))** が担当します。

エージェントは CLI を「ツール」として呼び出します。**`outputs/<日付>/data.json` を直接編集しないでください。** 必ず CLI 経由で操作してください。

---

## アーキテクチャ

```
[ユーザー(日本語)] ──会話──▶ [日報アシスタント Agent]
                                   │ execute(terminal)
                                   ▼
                       python src/daily_report.py <subcommand>
                                   │
                                   ▼
                  outputs/YYYY-MM-DD/data.json    ← 状態
                                   │
                                   ▼
                  outputs/YYYY-MM-DD/report.{html,png}  ← 日報
```

- **エージェント側**は意図解釈のみ(自然言語 → CLI コマンド変換)。
- **CLI 側**は決定的な状態管理(タスク追加・セッション記録・レポート生成)。
- **1 日 = 1 フォルダ**で全部入り(状態 + 日報)。アーカイブ・共有・削除が一発。

---

## ディレクトリ構成

```
daily-report-agent/
├── AGENTS.md                          # このファイル
├── README.md
├── requirements.txt
├── src/
│   ├── daily_report.py                # CLI エントリ
│   └── report_render.py               # HTML / PNG 生成
├── outputs/                           # (gitignore) 日付ごと
│   └── 2026-05-08/
│       ├── data.json
│       ├── report.html
│       └── report.png
└── .github/agents/daily-report.agent.md
```

---

## ツール層: Python CLI

すべての操作は以下のサブコマンドで完結します。エージェントはこれだけを使ってください。

| 用途 | コマンド |
|---|---|
| タスク開始 / 同名なら**再開** | `python src/daily_report.py start "<タスク名>"` |
| 現在のタスクを停止 | `python src/daily_report.py stop` |
| 別タスクへ切替(自動で前を停止) | `python src/daily_report.py switch "<タスク名>"` |
| 状況確認 | `python src/daily_report.py status` |
| 一覧 | `python src/daily_report.py list [--date YYYY-MM-DD]` |
| 手動加算 | `python src/daily_report.py add "<タスク名>" <時間h>` |
| 時間上書き | `python src/daily_report.py edit <No> <時間h>` |
| 改名 | `python src/daily_report.py rename <No> "<新名>"` |
| 削除 | `python src/daily_report.py remove <No>` |
| 日報出力(HTML+PNG) | `python src/daily_report.py report [--date YYYY-MM-DD]` |

詳細は [README.md](README.md) を参照。

---

## セットアップ

**手動セットアップ不要**。初回 `report` 実行時に matplotlib が無ければ CLI が自動で `pip install` します。

手動で入れたい場合のみ:

```powershell
python -m pip install -r requirements.txt
```

`matplotlib` が無い環境でも HTML 出力は動きます(PNG だけ自動スキップ)。

---

## エージェントへの動作要件

エージェントを書く / 改修する際は以下を必ず守ってください。

1. **データは CLI 経由でのみ変更**。`outputs/<日付>/data.json` を直接書き換えない。
2. **同じタスクの再開は `start` で OK**(自動で同名タスクを継続して新セッションを追加)。
3. **タスク名は短く具体的に**。長すぎる説明は避け、必要なら `(...)` で補足。
4. **作業内容を聞く時は短く 1 質問ずつ**。長いフォームを出さない。
5. **時間は 0.5h 単位**で出力されることを前提に動く(`report` 側で四捨五入)。
6. **OneNote 貼り付け前提**: 最終アウトプットは PNG または HTML(必ず `outputs/<日付>/` に出力)。

---

## 出力フォーマット

`report` 実行で `outputs/<日付>/` 配下に生成されるファイル:

- `report.png` — OneNote にドラッグ&ドロップ
- `report.html` — ブラウザで開いて表をコピー → OneNote に貼付
- `data.json` — 同フォルダ内に状態が保存される(直接編集しない)

スタイルは「青ヘッダー + 縞模様」の表(添付フォーマット準拠)。
