# -*- coding: utf-8 -*-

"""
Collect Claude Code usage from the local session logs, keep a daily summary in
``state/claude_code_usage.json`` and render a heatmap SVG for the README.

Claude Code writes every API response to ``~/.claude/projects/**/*.jsonl``. Those
logs are deleted after ``cleanupPeriodDays``, so each run merges the freshly parsed
days into the JSON file and never drops a day that is already recorded.

Usage::

    python -m machugwu.claude_code_usage
"""

import json
import argparse
import dataclasses
from pathlib import Path
from datetime import date, datetime, timedelta

dir_project_root = Path(__file__).absolute().parent.parent
dir_claude_projects = Path.home().joinpath(".claude", "projects")
path_usage_json = dir_project_root.joinpath("state", "claude_code_usage.json")
path_usage_svg = dir_project_root.joinpath("claude-code-usage.svg")

TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


@dataclasses.dataclass
class DailyUsage:
    """
    Usage of one local calendar day.

    - ``prompts``: messages you sent (tool results and subagent prompts excluded).
    - ``responses``: API responses from Claude, subagents included.
    - ``messages``: ``prompts + responses``.
    - token fields: summed from the ``usage`` block of each response.
    """

    date: str
    prompts: int = 0
    responses: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    models: dict[str, int] = dataclasses.field(default_factory=dict)

    @property
    def messages(self) -> int:
        return self.prompts + self.responses

    @property
    def total_tokens(self) -> int:
        return sum(getattr(self, field) for field in TOKEN_FIELDS)

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["messages"] = self.messages
        data["total_tokens"] = self.total_tokens
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "DailyUsage":
        names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})


def to_local_date(timestamp: str) -> str:
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return dt.astimezone().date().isoformat()


def is_human_prompt(record: dict) -> bool:
    if record.get("isSidechain") or record.get("isMeta"):
        return False
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return not content.startswith("<")  # slash command / local command echo
    if isinstance(content, list):
        return not any(
            isinstance(block, dict) and block.get("type") == "tool_result"
            for block in content
        )
    return False


def iter_records(dir_root: Path):
    for path in dir_root.rglob("*.jsonl"):
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def collect(dir_root: Path = dir_claude_projects) -> dict[str, DailyUsage]:
    """
    Parse every session log into per-day usage.

    One API response is written as several lines (one per content block) with the
    same ``message.id``, and resumed sessions copy earlier lines into a new file,
    so responses are de-duplicated by ``(message.id, requestId)`` and prompts by
    ``uuid``.
    """
    responses: dict[tuple, tuple[str, str, dict]] = dict()
    prompts: dict[str, str] = dict()
    for record in iter_records(dir_root):
        timestamp = record.get("timestamp")
        if not timestamp:
            continue
        type_ = record.get("type")
        if type_ == "assistant":
            message = record.get("message") or {}
            usage = message.get("usage")
            model = message.get("model") or "unknown"
            if not usage or model == "<synthetic>":
                continue
            key = (message.get("id"), record.get("requestId"))
            previous = responses.get(key)
            # later lines of the same response may carry a larger output count
            if previous is None or usage.get("output_tokens", 0) >= previous[2].get(
                "output_tokens", 0
            ):
                responses[key] = (timestamp, model, usage)
        elif type_ == "user" and is_human_prompt(record):
            prompts[record.get("uuid")] = timestamp

    days: dict[str, DailyUsage] = dict()

    def get_day(timestamp: str) -> DailyUsage:
        day = to_local_date(timestamp)
        if day not in days:
            days[day] = DailyUsage(date=day)
        return days[day]

    for timestamp in prompts.values():
        get_day(timestamp).prompts += 1
    for timestamp, model, usage in responses.values():
        daily = get_day(timestamp)
        daily.responses += 1
        daily.models[model] = daily.models.get(model, 0) + 1
        for field in TOKEN_FIELDS:
            setattr(daily, field, getattr(daily, field) + (usage.get(field) or 0))
    return days


def load(path: Path = path_usage_json) -> dict[str, DailyUsage]:
    if not path.exists():
        return dict()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {d["date"]: DailyUsage.from_dict(d) for d in data["days"]}


def merge(
    old: dict[str, DailyUsage],
    new: dict[str, DailyUsage],
) -> dict[str, DailyUsage]:
    """
    Keep the larger record of each day: a smaller fresh count means some of that
    day's logs were already cleaned up.
    """
    merged = dict(old)
    for day, daily in new.items():
        if day not in merged or daily.total_tokens >= merged[day].total_tokens:
            merged[day] = daily
    return merged


def dump(days: dict[str, DailyUsage], path: Path = path_usage_json):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "days": [days[day].to_dict() for day in sorted(days)],
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def summarize(days: dict[str, DailyUsage], today: date, n_days: int) -> dict:
    start = today - timedelta(days=n_days - 1)
    selected = [
        daily for day, daily in days.items() if start.isoformat() <= day <= today.isoformat()
    ]
    return {
        "days": n_days,
        "active_days": sum(1 for d in selected if d.messages),
        "messages": sum(d.messages for d in selected),
        "prompts": sum(d.prompts for d in selected),
        "responses": sum(d.responses for d in selected),
        "output_tokens": sum(d.output_tokens for d in selected),
        "total_tokens": sum(d.total_tokens for d in selected),
    }


# ------------------------------------------------------------------------------
# SVG
# ------------------------------------------------------------------------------
# One-hue orange ramp. Light mode goes light -> dark with usage, dark mode goes
# dark -> light, so "more" always reads as "more contrast with the surface".
SVG_STYLE = """
.bg { fill: #ffffff; stroke: #d0d7de; }
.title { fill: #1f2328; font: 600 15px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
.label { fill: #59636e; font: 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
.head { fill: #59636e; font: 600 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; letter-spacing: .04em; }
.value { fill: #1f2328; font: 600 18px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.rule { stroke: #d0d7de; }
.l0 { fill: #ebeae6; } .l1 { fill: #f6c7a3; } .l2 { fill: #ec9a5f; }
.l3 { fill: #d4692a; } .l4 { fill: #9c4416; }
@media (prefers-color-scheme: dark) {
  .bg { fill: #0d1117; stroke: #30363d; }
  .title, .value { fill: #e6edf3; }
  .label, .head { fill: #9198a1; }
  .rule { stroke: #30363d; }
  .l0 { fill: #21262d; } .l1 { fill: #5c3018; } .l2 { fill: #92461c; }
  .l3 { fill: #d0672a; } .l4 { fill: #f4a66d; }
}
"""

CELL = 13
GAP = 3
STEP = CELL + GAP


def human(n: int) -> str:
    for unit, size in (("B", 10**9), ("M", 10**6), ("K", 10**3)):
        if n >= size:
            return f"{n / size:.1f}{unit}"
    return str(n)


def level_thresholds(values: list[int]) -> list[int]:
    """Quartiles of the non-zero days, so one huge day doesn't wash out the rest."""
    values = sorted(v for v in values if v > 0)
    if not values:
        return [1, 1, 1]
    return [values[int(len(values) * q)] for q in (0.25, 0.5, 0.75)]


def level_of(value: int, thresholds: list[int]) -> int:
    if value <= 0:
        return 0
    return 1 + sum(value > t for t in thresholds)


def render_svg(days: dict[str, DailyUsage], today: date, n_days: int = 90) -> str:
    # grid: columns are weeks (Sunday first), rows are weekdays
    start = today - timedelta(days=n_days - 1)
    grid_start = start - timedelta(days=(start.weekday() + 1) % 7)
    n_weeks = (today - grid_start).days // 7 + 1

    values = {
        day: days[day].total_tokens
        for day in days
        if start.isoformat() <= day <= today.isoformat()
    }
    thresholds = level_thresholds(list(values.values()))

    pad = 20
    grid_x = pad + 30
    grid_y = 62
    grid_w = n_weeks * STEP - GAP
    stats_x = grid_x + grid_w + 36
    width = stats_x + 330
    height = grid_y + 7 * STEP - GAP + 44

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Claude Code usage heatmap, last {n_days} days">',
        f"<style>{SVG_STYLE}</style>",
        f'<rect class="bg" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6"/>',
        f'<text class="title" x="{pad}" y="30">Claude Code usage · last {n_days} days</text>',
    ]

    # month labels above the week holding the 1st; the first column gets the
    # starting month only when the next label is far enough away not to overlap
    labels = []
    for week in range(n_weeks):
        week_days = [grid_start + timedelta(days=week * 7 + row) for row in range(7)]
        firsts = [d for d in week_days if d.day == 1 and start <= d <= today]
        if firsts:
            labels.append((week, firsts[0]))
    if not labels or labels[0][0] >= 3:
        labels.insert(0, (0, start))
    for week, day in labels:
        out.append(
            f'<text class="label" x="{grid_x + week * STEP}" y="{grid_y - 8}">'
            f'{day.strftime("%b")}</text>'
        )

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = grid_y + row * STEP + CELL - 2
        out.append(f'<text class="label" x="{pad}" y="{y}">{name}</text>')

    for week in range(n_weeks):
        for row in range(7):
            day = grid_start + timedelta(days=week * 7 + row)
            if day < start or day > today:
                continue
            key = day.isoformat()
            daily = days.get(key)
            level = level_of(values.get(key, 0), thresholds)
            tip = (
                f"{key}: {daily.messages:,} messages, {human(daily.total_tokens)} tokens"
                if daily
                else f"{key}: no usage"
            )
            out.append(
                f'<rect class="l{level}" x="{grid_x + week * STEP}" '
                f'y="{grid_y + row * STEP}" width="{CELL}" height="{CELL}" rx="2">'
                f"<title>{tip}</title></rect>"
            )

    # legend under the grid
    legend_y = grid_y + 7 * STEP + 12
    legend_x = grid_x + grid_w - 5 * (CELL - 2 + GAP) - 34
    out.append(f'<text class="label" x="{legend_x - 32}" y="{legend_y + 9}">Less</text>')
    for level in range(5):
        x = legend_x + level * (CELL - 2 + GAP)
        out.append(
            f'<rect class="l{level}" x="{x}" y="{legend_y}" '
            f'width="{CELL - 2}" height="{CELL - 2}" rx="2"/>'
        )
    out.append(
        f'<text class="label" x="{legend_x + 5 * (CELL - 2 + GAP) + 4}" '
        f'y="{legend_y + 9}">More</text>'
    )

    # stats table: one row per window
    col_messages = stats_x + 90
    col_tokens = stats_x + 210
    out.append(f'<text class="head" x="{col_messages}" y="{grid_y + 4}">MESSAGES</text>')
    out.append(f'<text class="head" x="{col_tokens}" y="{grid_y + 4}">TOKENS</text>')
    out.append(
        f'<line class="rule" x1="{stats_x}" x2="{width - pad}" '
        f'y1="{grid_y + 14}" y2="{grid_y + 14}"/>'
    )
    for i, n in enumerate((7, 30, 90)):
        s = summarize(days, today, n)
        y = grid_y + 44 + i * 30
        out.append(f'<text class="label" x="{stats_x}" y="{y}">Last {n} days</text>')
        out.append(f'<text class="value" x="{col_messages}" y="{y + 1}">{human(s["messages"])}</text>')
        out.append(f'<text class="value" x="{col_tokens}" y="{y + 1}">{human(s["total_tokens"])}</text>')

    out.append(
        f'<text class="label" x="{stats_x}" y="{height - 16}">'
        f"Updated {today.isoformat()} · from local Claude Code session logs</text>"
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--days", type=int, default=90, help="heatmap window in days")
    args = parser.parse_args()

    days = merge(load(), collect())
    dump(days)
    today = date.today()
    path_usage_svg.write_text(render_svg(days, today, args.days), encoding="utf-8")

    print(f"{'window':<10}{'active':>8}{'prompts':>10}{'responses':>11}{'messages':>10}"
          f"{'output':>10}{'tokens':>10}")
    for n in (7, 30, 90):
        s = summarize(days, today, n)
        print(f"{f'{n} days':<10}{s['active_days']:>8}{s['prompts']:>10,}{s['responses']:>11,}"
              f"{s['messages']:>10,}{human(s['output_tokens']):>10}{human(s['total_tokens']):>10}")
    print(f"wrote {path_usage_json.relative_to(dir_project_root)}")
    print(f"wrote {path_usage_svg.relative_to(dir_project_root)}")


if __name__ == "__main__":
    main()
