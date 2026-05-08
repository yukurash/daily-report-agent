"""Daily Report Agent - 日報用タスク時間トラッカー & レポート生成ツール

使い方:
    python src/daily_report.py start "タスク名"     # 計測開始(同名なら再開)
    python src/daily_report.py stop                  # 計測停止
    python src/daily_report.py switch "別タスク"    # 現在を停止して別タスクへ
    python src/daily_report.py status                # 現在の状況
    python src/daily_report.py list                  # 今日のタスク一覧
    python src/daily_report.py add "タスク名" 1.5   # 手動で時間を追加(時間)
    python src/daily_report.py edit <No> 2.0        # No指定で時間を上書き
    python src/daily_report.py rename <No> "新名"   # タスク名を変更
    python src/daily_report.py remove <No>           # タスクを削除
    python src/daily_report.py report                # HTML/PNG レポート出力
    python src/daily_report.py report --date 2026-05-08

ファイル配置:
    outputs/<YYYY-MM-DD>/data.json     # その日の状態
    outputs/<YYYY-MM-DD>/report.html   # 日報(HTML)
    outputs/<YYYY-MM-DD>/report.png    # 日報(PNG)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# src/daily_report.py から見たプロジェクトルート
ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = ROOT / "outputs"


# ---------------------------------------------------------------------------
# データI/O
# ---------------------------------------------------------------------------

def today_str() -> str:
    return date.today().isoformat()


def day_dir(day: str) -> Path:
    return OUTPUTS_DIR / day


def data_path(day: str) -> Path:
    return day_dir(day) / "data.json"


def load_day(day: Optional[str] = None) -> dict:
    day = day or today_str()
    f = data_path(day)
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {"date": day, "tasks": [], "current": None}


def save_day(data: dict) -> None:
    d = day_dir(data["date"])
    d.mkdir(parents=True, exist_ok=True)
    (d / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# タスクユーティリティ
# ---------------------------------------------------------------------------

def _normalize(name: str) -> str:
    return name.strip().lower()


def find_task(data: dict, name: str) -> Optional[dict]:
    n = _normalize(name)
    for t in data["tasks"]:
        if _normalize(t["name"]) == n:
            return t
    return None


def task_seconds(task: dict, current: Optional[dict] = None) -> float:
    total = float(task.get("manual_seconds", 0))
    for s in task.get("sessions", []):
        try:
            total += (
                datetime.fromisoformat(s["end"]) - datetime.fromisoformat(s["start"])
            ).total_seconds()
        except (KeyError, ValueError):
            continue
    if current and _normalize(current["name"]) == _normalize(task["name"]):
        total += (datetime.now() - datetime.fromisoformat(current["start"])).total_seconds()
    return max(total, 0.0)


def round_half(hours: float) -> float:
    """0.5 単位で四捨五入。"""
    return round(hours * 2) / 2


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def stop_current(data: dict, now: Optional[str] = None) -> Optional[dict]:
    cur = data.get("current")
    if not cur:
        return None
    now = now or now_iso()
    task = find_task(data, cur["name"])
    if task is None:
        # 念のためフォールバック
        task = {"name": cur["name"], "sessions": [], "manual_seconds": 0}
        data["tasks"].append(task)
    task.setdefault("sessions", []).append({"start": cur["start"], "end": now})
    data["current"] = None
    return task


# ---------------------------------------------------------------------------
# コマンド
# ---------------------------------------------------------------------------

def cmd_start(args: argparse.Namespace) -> None:
    data = load_day()
    now = now_iso()
    if data.get("current"):
        if _normalize(data["current"]["name"]) == _normalize(args.name):
            print(f"既に '{data['current']['name']}' を計測中です。")
            return
        stopped = stop_current(data, now)
        elapsed = (
            datetime.fromisoformat(now) - datetime.fromisoformat(stopped["sessions"][-1]["start"])
        ).total_seconds() / 60
        print(f"⏸  '{stopped['name']}' を停止しました(このセッション {elapsed:.1f}分)")

    task = find_task(data, args.name)
    if task is None:
        task = {"name": args.name.strip(), "sessions": [], "manual_seconds": 0}
        data["tasks"].append(task)
        print(f"▶  新規タスク '{task['name']}' を開始しました。")
    else:
        prev_h = task_seconds(task) / 3600
        print(f"▶  既存タスク '{task['name']}' を再開しました(これまで {prev_h:.2f}h)")

    data["current"] = {"name": task["name"], "start": now}
    save_day(data)


def cmd_stop(args: argparse.Namespace) -> None:
    data = load_day()
    if not data.get("current"):
        print("実行中のタスクはありません。")
        return
    cur_start = data["current"]["start"]
    stopped = stop_current(data)
    elapsed = (
        datetime.now() - datetime.fromisoformat(cur_start)
    ).total_seconds() / 60
    save_day(data)
    total_h = task_seconds(stopped) / 3600
    print(f"⏹  '{stopped['name']}' を停止(このセッション {elapsed:.1f}分 / 累計 {total_h:.2f}h)")


def cmd_switch(args: argparse.Namespace) -> None:
    # start と同じ挙動でOK(start側で前タスクを止める)
    cmd_start(args)


def cmd_status(args: argparse.Namespace) -> None:
    data = load_day()
    cur = data.get("current")
    if cur:
        elapsed = (datetime.now() - datetime.fromisoformat(cur["start"])).total_seconds() / 60
        print(f"⏱  実行中: '{cur['name']}'  (このセッション {elapsed:.1f}分)")
    else:
        print("⏸  実行中のタスクはありません。")
    cmd_list(args)


def cmd_list(args: argparse.Namespace) -> None:
    day = getattr(args, "date", None) or today_str()
    data = load_day(day)
    cur = data.get("current") if day == today_str() else None
    if not data["tasks"]:
        print(f"({day}) タスクはまだありません。")
        return
    print(f"\n=== {data['date']} ===")
    print(f"{'No':<3} {'Task':<46} {'Labor(h)':>9} {'Raw(h)':>8}  Sessions")
    print("-" * 80)
    total_raw = 0.0
    total_round = 0.0
    for i, t in enumerate(data["tasks"], 1):
        sec = task_seconds(t, cur)
        h = sec / 3600
        rh = round_half(h)
        total_raw += h
        total_round += rh
        marker = " *" if cur and _normalize(cur["name"]) == _normalize(t["name"]) else "  "
        sessions = len(t.get("sessions", []))
        name = t["name"] if len(t["name"]) <= 44 else t["name"][:43] + "…"
        print(f"{i:<3} {name:<46} {rh:>9.1f} {h:>8.2f}  {sessions}回{marker}")
    print("-" * 80)
    print(f"{'':<3} {'合計':<46} {total_round:>9.1f} {total_raw:>8.2f}")


def _resolve_index(data: dict, no: int) -> int:
    idx = no - 1
    if idx < 0 or idx >= len(data["tasks"]):
        print(f"No={no} は範囲外です(1〜{len(data['tasks'])})。", file=sys.stderr)
        sys.exit(2)
    return idx


def cmd_add(args: argparse.Namespace) -> None:
    data = load_day()
    task = find_task(data, args.name)
    if task is None:
        task = {"name": args.name.strip(), "sessions": [], "manual_seconds": 0}
        data["tasks"].append(task)
    task["manual_seconds"] = task.get("manual_seconds", 0) + args.hours * 3600
    save_day(data)
    print(f"➕  '{task['name']}' に {args.hours}h を追加しました(累計 {task_seconds(task)/3600:.2f}h)。")


def cmd_edit(args: argparse.Namespace) -> None:
    """No指定でタスクの累計時間を上書き(セッションをクリアして manual_seconds に集約)。"""
    data = load_day()
    idx = _resolve_index(data, args.no)
    task = data["tasks"][idx]
    if data.get("current") and _normalize(data["current"]["name"]) == _normalize(task["name"]):
        print("実行中のタスクは編集できません。先に stop してください。", file=sys.stderr)
        sys.exit(2)
    task["sessions"] = []
    task["manual_seconds"] = args.hours * 3600
    save_day(data)
    print(f"✏  '{task['name']}' を {args.hours}h に上書きしました。")


def cmd_rename(args: argparse.Namespace) -> None:
    data = load_day()
    idx = _resolve_index(data, args.no)
    old = data["tasks"][idx]["name"]
    data["tasks"][idx]["name"] = args.name.strip()
    if data.get("current") and _normalize(data["current"]["name"]) == _normalize(old):
        data["current"]["name"] = args.name.strip()
    save_day(data)
    print(f"✏  リネーム: '{old}' → '{args.name.strip()}'")


def cmd_remove(args: argparse.Namespace) -> None:
    data = load_day()
    idx = _resolve_index(data, args.no)
    removed = data["tasks"].pop(idx)
    if data.get("current") and _normalize(data["current"]["name"]) == _normalize(removed["name"]):
        data["current"] = None
    save_day(data)
    print(f"🗑  削除しました: '{removed['name']}'")


def _ensure_dependencies() -> None:
    """初回実行時に必要パッケージ(matplotlib)が無ければ自動インストール。"""
    try:
        import matplotlib  # noqa: F401
        return
    except ImportError:
        pass
    req = ROOT / "requirements.txt"
    if not req.exists():
        return
    print("📦  初回セットアップ: 必要なパッケージをインストールします...")
    import subprocess
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(req), "--quiet"]
    )
    print("✅  セットアップ完了。")


def cmd_report(args: argparse.Namespace) -> None:
    _ensure_dependencies()
    from report_render import render_report  # 遅延 import(matplotlib 重い)

    day = args.date or today_str()
    data = load_day(day)
    if not data["tasks"]:
        print(f"({day}) タスクがないためレポートを生成できません。")
        return
    # 計測中なら確定して保存(中断扱い)
    if day == today_str() and data.get("current"):
        if not args.keep_running:
            stop_current(data)
            save_day(data)
            print("⏹  実行中タスクを停止してレポートを確定しました。")

    cur = data.get("current") if day == today_str() else None
    rows = []
    for i, t in enumerate(data["tasks"], 1):
        h = task_seconds(t, cur) / 3600
        rh = round_half(h)
        if rh <= 0 and not args.include_zero:
            continue
        rows.append((i, t["name"], rh))
    if not rows:
        print("出力対象のタスクがありません(0.5h未満は既定で除外)。--include-zero で含められます。")
        return

    out = day_dir(day)
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / "report.html"
    png_path = out / "report.png"
    render_report(day, rows, html_path, png_path)
    total = sum(r[2] for r in rows)
    print(f"📄  HTML:  {html_path}")
    print(f"🖼  PNG :  {png_path}")
    print(f"   合計 {total:.1f}h / {len(rows)}件")
    print("\nOneNote への貼り付け:")
    print("  ・PNG をエクスプローラからドラッグ&ドロップ、または")
    print("  ・HTML をブラウザで開き、表を選択してコピー → OneNote に貼り付け")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="daily-report",
        description="日報用タスク時間トラッカー(複数セッション対応)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="タスクの計測を開始(既存タスク名なら再開)")
    s.add_argument("name", help="タスク名")
    s.set_defaults(func=cmd_start)

    s = sub.add_parser("stop", help="現在のタスクを停止")
    s.set_defaults(func=cmd_stop)

    s = sub.add_parser("switch", help="現在を停止して別タスクへ切替(start のエイリアス)")
    s.add_argument("name", help="タスク名")
    s.set_defaults(func=cmd_switch)

    s = sub.add_parser("status", help="現在の状況と一覧")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("list", help="タスク一覧")
    s.add_argument("--date", help="YYYY-MM-DD 指定(省略時は今日)")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("add", help="手動でタスクと時間(h)を追加 / 既存に時間を加算")
    s.add_argument("name", help="タスク名")
    s.add_argument("hours", type=float, help="加算する時間(時間)")
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("edit", help="No指定でタスクの累計時間を上書き")
    s.add_argument("no", type=int, help="タスクNo")
    s.add_argument("hours", type=float, help="上書き後の時間(時間)")
    s.set_defaults(func=cmd_edit)

    s = sub.add_parser("rename", help="No指定でタスク名を変更")
    s.add_argument("no", type=int)
    s.add_argument("name")
    s.set_defaults(func=cmd_rename)

    s = sub.add_parser("remove", help="No指定でタスクを削除")
    s.add_argument("no", type=int)
    s.set_defaults(func=cmd_remove)

    s = sub.add_parser("report", help="HTML/PNG 形式でレポートを生成")
    s.add_argument("--date", help="YYYY-MM-DD 指定(省略時は今日)")
    s.add_argument("--include-zero", action="store_true", help="0.5h未満のタスクも含める")
    s.add_argument("--keep-running", action="store_true", help="実行中タスクを停止せずに出力")
    s.set_defaults(func=cmd_report)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
