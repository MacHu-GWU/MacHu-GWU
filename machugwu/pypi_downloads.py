# -*- coding: utf-8 -*-

"""
Fetch the monthly PyPI downloads of my popular packages from pypistats.org and
rewrite the package list in ``README.md``.

The list lives between two invisible HTML comments in the README::

    <!-- BEGIN pypi-downloads -->
    ...
    <!-- END pypi-downloads -->

Everything between the markers is regenerated on each run. pypistats.org has no
batch endpoint, so packages are fetched one by one with a short pause in between.

The exact numbers and the fetch date are also written to
``state/pypi_downloads.json`` for local inspection. ``state/`` is gitignored:
only the rendered README is committed.

Usage::

    python -m machugwu.pypi_downloads
"""

import re
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

dir_project_root = Path(__file__).absolute().parent.parent
path_readme = dir_project_root.joinpath("README.md")
path_downloads_json = dir_project_root.joinpath("state", "pypi_downloads.json")

github_username = "MacHu-GWU"

# Packages shown in the README, in display order.
packages = [
    "uszipcode",
    "pathlib_mate",
    "sqlalchemy_mate",
    "s3pathlib",
    "boto_session_manager",
    "iterproxy",
    "func_args",
]

MARKER_BEGIN = "<!-- BEGIN pypi-downloads -->"
MARKER_END = "<!-- END pypi-downloads -->"

SLEEP_SECONDS = 1


def normalize(package: str) -> str:
    """
    PyPI normalized name, e.g. ``func_args`` -> ``func-args``.
    """
    return re.sub(r"[-_.]+", "-", package).lower()


def get_recent_downloads(package: str) -> dict[str, int]:
    """
    Return ``{"last_day": ..., "last_week": ..., "last_month": ...}``.
    """
    url = f"https://pypistats.org/api/packages/{normalize(package)}/recent"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"{github_username}-readme-bot"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())["data"]


def humanize(n: int) -> str:
    """
    ``671365`` -> ``671k``, ``1234567`` -> ``1.2M``.
    """
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def badge_url(monthly_downloads: int) -> str:
    """
    A shields.io static badge, e.g. ``downloads | 671k/month``.
    """
    message = urllib.parse.quote(f"{humanize(monthly_downloads)}/month", safe="")
    return f"https://img.shields.io/badge/downloads-{message}-blue"


def render_line(package: str, monthly_downloads: int) -> str:
    github_url = f"https://github.com/{github_username}/{package}-project"
    pypistats_url = f"https://pypistats.org/packages/{normalize(package)}"
    badge = f"[![]({badge_url(monthly_downloads)})]({pypistats_url})"
    return f"- [{package}]({github_url}): {badge}"


def update_readme(block: str):
    text = path_readme.read_text()
    pattern = re.compile(
        re.escape(MARKER_BEGIN) + r".*?" + re.escape(MARKER_END),
        flags=re.DOTALL,
    )
    if not pattern.search(text):
        raise ValueError(
            f"{MARKER_BEGIN!r} ... {MARKER_END!r} not found in {path_readme}"
        )
    new_block = f"{MARKER_BEGIN}\n{block}\n{MARKER_END}"
    path_readme.write_text(pattern.sub(lambda _: new_block, text, count=1))


def write_json(downloads: dict[str, dict[str, int]]):
    path_downloads_json.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "packages": downloads,
    }
    path_downloads_json.write_text(json.dumps(data, indent=4) + "\n")


def main():
    downloads = dict()
    lines = list()
    for i, package in enumerate(packages):
        if i:
            time.sleep(SLEEP_SECONDS)
        data = get_recent_downloads(package)
        print(f"{package}: {data['last_month']:,} downloads last month")
        downloads[package] = data
        lines.append(render_line(package, data["last_month"]))
    update_readme("\n".join(lines))
    write_json(downloads)
    print(f"Updated {path_readme} and {path_downloads_json}")


if __name__ == "__main__":
    main()
