"""レポート出力(HTML + PNG)。添付画像のスタイルを再現。"""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable, List, Tuple

# ヘッダー色(添付画像の青に近い)
HEADER_BG = "#4472C4"
HEADER_FG = "#FFFFFF"
ROW_BG = "#FFFFFF"
ROW_ALT_BG = "#F2F2F2"
BORDER = "#8FAADC"

Row = Tuple[int, str, float]


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>Daily Report {date}</title>
<style>
  body {{
    font-family: "Yu Gothic", "Meiryo", "Segoe UI", sans-serif;
    margin: 24px;
    color: #222;
  }}
  h2 {{ margin: 0 0 8px; }}
  table.daily-report {{
    border-collapse: collapse;
    border: 1px solid {border};
    font-family: "Yu Gothic", "Meiryo", "Segoe UI", sans-serif;
    font-size: 14px;
    min-width: 520px;
  }}
  table.daily-report th {{
    background: {header_bg};
    color: {header_fg};
    border: 1px solid {border};
    padding: 6px 12px;
    text-align: center;
    font-weight: bold;
  }}
  table.daily-report td {{
    border: 1px solid {border};
    padding: 6px 12px;
    background: {row_bg};
  }}
  table.daily-report tr:nth-child(even) td {{ background: {row_alt_bg}; }}
  table.daily-report td.no    {{ text-align: center; width: 48px; }}
  table.daily-report td.labor {{ text-align: center; width: 90px; }}
</style>
</head>
<body>
<h2>Today&#39;s Task ({date}) :</h2>
<table class="daily-report">
  <thead>
    <tr><th>No</th><th>Task</th><th>Labor(h)</th></tr>
  </thead>
  <tbody>
{rows}
  </tbody>
</table>
</body>
</html>
"""


def _format_hours(h: float) -> str:
    # 0.5 単位なので整数 or .5 で表示
    if abs(h - round(h)) < 1e-9:
        return f"{int(round(h))}"
    return f"{h:.1f}"


def render_html(day: str, rows: Iterable[Row], path: Path) -> None:
    body = []
    for i, (_, name, h) in enumerate(rows, 1):
        body.append(
            f'    <tr><td class="no">{i}</td>'
            f'<td>{escape(name)}</td>'
            f'<td class="labor">{_format_hours(h)}</td></tr>'
        )
    html = HTML_TEMPLATE.format(
        date=escape(day),
        rows="\n".join(body),
        header_bg=HEADER_BG,
        header_fg=HEADER_FG,
        row_bg=ROW_BG,
        row_alt_bg=ROW_ALT_BG,
        border=BORDER,
    )
    path.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------------------
# PNG (matplotlib)
# ---------------------------------------------------------------------------

def _pick_jp_font() -> str:
    """日本語が描画できそうなフォントを選ぶ。"""
    try:
        from matplotlib import font_manager
    except Exception:
        return "DejaVu Sans"
    candidates = [
        "Yu Gothic UI", "Yu Gothic", "Meiryo", "MS Gothic",
        "Noto Sans CJK JP", "Hiragino Sans", "TakaoPGothic",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for c in candidates:
        if c in available:
            return c
    return "DejaVu Sans"


def render_png(day: str, rows: List[Row], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import rcParams

    rcParams["font.family"] = _pick_jp_font()
    rcParams["axes.unicode_minus"] = False

    n = len(rows)
    # サイズ:列幅は固定、行数で高さ調整
    fig_w = 7.2
    row_h = 0.42
    header_h = 0.55
    title_h = 0.55
    fig_h = title_h + header_h + row_h * n + 0.3

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=160)
    ax.set_axis_off()

    cell_text = [[str(i), name, _format_hours(h)] for i, (_, name, h) in enumerate(rows, 1)]
    col_labels = ["No", "Task", "Labor(h)"]
    col_widths = [0.10, 0.72, 0.18]

    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        colWidths=col_widths,
        loc="upper center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    # 行高
    table.scale(1.0, 1.5)

    header_rgb = _hex_to_rgb(HEADER_BG)
    alt_rgb = _hex_to_rgb(ROW_ALT_BG)
    border_rgb = _hex_to_rgb(BORDER)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(border_rgb)
        cell.set_linewidth(0.8)
        if row == 0:
            cell.set_facecolor(header_rgb)
            cell.set_text_props(color="white", weight="bold")
        else:
            if row % 2 == 0:
                cell.set_facecolor(alt_rgb)
            # Task 列は左寄せ
            if col == 1:
                cell.set_text_props(ha="left")
                cell.PAD = 0.03

    # タイトル
    ax.text(
        0.0, 1.0,
        f"Today's Task ({day}) :",
        transform=ax.transAxes,
        fontsize=12, weight="bold", va="bottom", ha="left",
    )

    fig.tight_layout(pad=0.4)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ---------------------------------------------------------------------------
# エントリ
# ---------------------------------------------------------------------------

def render_report(day: str, rows: List[Row], html_path: Path, png_path: Path) -> None:
    render_html(day, rows, html_path)
    try:
        render_png(day, rows, png_path)
    except Exception as e:  # PNG 生成は best-effort
        print(f"⚠  PNG 生成に失敗しました: {e}\n   HTML のみ出力しています。")
