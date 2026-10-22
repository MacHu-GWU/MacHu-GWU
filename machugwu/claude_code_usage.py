# -*- coding: utf-8 -*-

"""
Collect Claude Code usage from the local session logs, keep a daily summary in
``state/claude_code_usage.json`` and render a heatmap SVG for the README.

Usage::

    python -m machugwu.claude_code_usage   # or: mise run cc-usage

**Where the data comes from**

Claude Code writes each session to ``~/.claude/projects/<project>/<session>.jsonl``
(subagents under ``<session>/subagents/*.jsonl``), one JSON object per line. Two
line types matter here:

- ``"type": "user"``: something sent to the model on the user side. This is
  either a prompt you typed, or a tool result Claude Code feeds back, or a
  prompt the main agent hands to a subagent.
- ``"type": "assistant"``: part of one API response, with ``message.usage``
  holding the token counts of that response.

There is no official server-side usage history for Pro / Max plans, so these
local logs are the only per-day source. They only cover this machine (not other
devices, not claude.ai), and Claude Code deletes them after ``cleanupPeriodDays``
(default 30). Each run therefore merges the freshly parsed days into the JSON
file and never drops a day that is already recorded.

**Metric definitions**

- **prompts**: messages you typed. Tool results, subagent prompts, slash-command
  echoes and other injected ``isMeta`` lines are excluded.
- **api_calls**: model requests, one per API response. An agent turn is a loop:
  call the model, run the tool it asks for, call the model again with the
  result, so one prompt usually costs ~10 API calls, more with subagents. This
  is why api_calls is an order of magnitude larger than prompts.
- **subagent_api_calls**: the part of ``api_calls`` made by subagents
  (``isSidechain`` lines). Already included in ``api_calls``.
- **tokens**: from each response's ``usage`` block. ``total_tokens`` is
  ``input + output + cache_creation_input + cache_read_input``. Every API call
  re-sends the whole conversation, which is mostly served from the prompt cache,
  so ``cache_read_input_tokens`` dominates the total. ``output_tokens`` is what
  Claude actually generated.
- Days are local calendar days of the machine running this script.
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

#: summary windows printed to the terminal and shown in the SVG
WINDOWS = (7, 30, 90)


@dataclasses.dataclass
class DailyUsage:
    """
    Usage of one local calendar day. See the module docstring for what each
    metric means.
    """

    date: str
    prompts: int = 0
    api_calls: int = 0
    subagent_api_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    #: model id -> number of API calls
    models: dict[str, int] = dataclasses.field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return sum(getattr(self, field) for field in TOKEN_FIELDS)

    @property
    def is_active(self) -> bool:
        return bool(self.prompts or self.api_calls)

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["total_tokens"] = self.total_tokens  # derived, written for readers only
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "DailyUsage":
        data = dict(data)
        # the first version of the JSON called api_calls "responses"
        if "responses" in data and "api_calls" not in data:
            data["api_calls"] = data.pop("responses")
        names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})


def to_local_date(timestamp: str) -> str:
    """``2026-10-22T01:49:26.382Z`` -> local date such as ``2026-10-21``."""
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return dt.astimezone().date().isoformat()


def is_human_prompt(record: dict) -> bool:
    """
    Tell a prompt you typed apart from the other ``"type": "user"`` lines.
    """
    # subagent prompts written by the main agent, and injected context
    if record.get("isSidechain") or record.get("isMeta"):
        return False
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        # slash commands and local command output are logged as
        # "<command-name>..." / "<local-command-stdout>..." strings
        return not content.startswith("<")
    if isinstance(content, list):
        # a tool result is fed back to the model as a user message
        return not any(
            isinstance(block, dict) and block.get("type") == "tool_result"
            for block in content
        )
    return False


def iter_records(dir_root: Path):
    """Yield every JSON line of every session log, skipping broken lines."""
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

    The raw lines over-count, so both sides are de-duplicated before counting:

    - One API response is written as several ``assistant`` lines (one per content
      block: thinking, text, each tool call) sharing the same ``message.id``.
    - A resumed or forked session copies the earlier lines into its new file.

    API calls are keyed by ``(message.id, requestId)`` and prompts by ``uuid``.
    Without this the counts come out roughly 3x too high.
    """
    # (message.id, requestId) -> (timestamp, model, usage, is_subagent)
    api_calls: dict[tuple, tuple[str, str, dict, bool]] = dict()
    # uuid -> timestamp
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
            # "<synthetic>" lines are messages Claude Code made up locally
            # (e.g. an error notice), not real model calls
            if not usage or model == "<synthetic>":
                continue
            key = (message.get("id"), record.get("requestId"))
            previous = api_calls.get(key)
            # later lines of the same response may carry a larger output count
            if previous is None or usage.get("output_tokens", 0) >= previous[2].get(
                "output_tokens", 0
            ):
                api_calls[key] = (
                    timestamp,
                    model,
                    usage,
                    bool(record.get("isSidechain")),
                )
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
    for timestamp, model, usage, is_subagent in api_calls.values():
        daily = get_day(timestamp)
        daily.api_calls += 1
        daily.subagent_api_calls += is_subagent
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
    day's logs were already cleaned up, so the stored record is more complete.
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
    """Totals of the last ``n_days`` days, today included."""
    start = today - timedelta(days=n_days - 1)
    selected = [
        daily
        for day, daily in days.items()
        if start.isoformat() <= day <= today.isoformat()
    ]
    return {
        "days": n_days,
        "active_days": sum(d.is_active for d in selected),
        "prompts": sum(d.prompts for d in selected),
        "api_calls": sum(d.api_calls for d in selected),
        "subagent_api_calls": sum(d.subagent_api_calls for d in selected),
        "output_tokens": sum(d.output_tokens for d in selected),
        "total_tokens": sum(d.total_tokens for d in selected),
    }


# ------------------------------------------------------------------------------
# SVG
# ------------------------------------------------------------------------------
# GitHub shows a README SVG through <img>, so it can't run scripts or show hover
# tooltips (the <title> on each cell only works when the SVG is opened directly),
# but it does honor prefers-color-scheme for dark mode.
#
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
    """12345678 -> ``12.3M``"""
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
    """0 = no usage, 1..4 = quartile of a day with usage."""
    if value <= 0:
        return 0
    return 1 + sum(value > t for t in thresholds)


def render_svg(days: dict[str, DailyUsage], today: date, n_days: int = 90) -> str:
    """
    Heatmap of ``total_tokens`` per day on the left, a prompts / API calls /
    tokens table for each of :data:`WINDOWS` on the right.
    """
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
    col_prompts = stats_x + 90
    col_api_calls = col_prompts + 95
    col_tokens = col_api_calls + 110
    width = col_tokens + 110
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
                f"{key}: {daily.prompts:,} prompts, {daily.api_calls:,} API calls, "
                f"{human(daily.total_tokens)} tokens"
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
    for x, head in (
        (col_prompts, "PROMPTS"),
        (col_api_calls, "API CALLS"),
        (col_tokens, "TOKENS"),
    ):
        out.append(f'<text class="head" x="{x}" y="{grid_y + 4}">{head}</text>')
    out.append(
        f'<line class="rule" x1="{stats_x}" x2="{width - pad}" '
        f'y1="{grid_y + 14}" y2="{grid_y + 14}"/>'
    )
    for i, n in enumerate(WINDOWS):
        s = summarize(days, today, n)
        y = grid_y + 44 + i * 30
        out.append(f'<text class="label" x="{stats_x}" y="{y}">Last {n} days</text>')
        for x, key in (
            (col_prompts, "prompts"),
            (col_api_calls, "api_calls"),
            (col_tokens, "total_tokens"),
        ):
            out.append(f'<text class="value" x="{x}" y="{y + 1}">{human(s[key])}</text>')

    out.append(
        f'<text class="label" x="{stats_x}" y="{height - 16}">'
        f"Prompts = messages I typed · API calls incl. subagents · "
        f"updated {today.isoformat()}</text>"
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

    columns = [
        ("window", 10),
        ("active", 8),
        ("prompts", 10),
        ("api_calls", 11),
        ("subagent", 10),
        ("output", 10),
        ("tokens", 10),
    ]
    print("".join(f"{name:<{w}}" if i == 0 else f"{name:>{w}}" for i, (name, w) in enumerate(columns)))
    for n in WINDOWS:
        s = summarize(days, today, n)
        cells = [
            f"{n} days",
            f"{s['active_days']}",
            f"{s['prompts']:,}",
            f"{s['api_calls']:,}",
            f"{s['subagent_api_calls']:,}",
            human(s["output_tokens"]),
            human(s["total_tokens"]),
        ]
        print("".join(f"{c:<{w}}" if i == 0 else f"{c:>{w}}" for i, (c, (_, w)) in enumerate(zip(cells, columns))))
    print("prompts = messages you typed; api_calls = model requests incl. subagent ones;")
    print("tokens = input + output + cache write + cache read (cache read dominates)")
    print(f"wrote {path_usage_json.relative_to(dir_project_root)}")
    print(f"wrote {path_usage_svg.relative_to(dir_project_root)}")


if __name__ == "__main__":
    main()
