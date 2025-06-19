# -*- coding: utf-8 -*-

"""
Requirements::

    pip install -U pypistats
    pip install -U pypistats

Google Sheet: https://docs.google.com/spreadsheets/d/1iDPOgXn0PqxlMWdUH6guUKYdaTZN6JC78Nv-WL6J6kY/edit?gid=0#gid=0
"""

import typing as T
import time
from pathlib import Path

import tabulate
import requests
from diskcache import Cache

dir_here = Path(__file__).absolute().parent
dir_tmp = dir_here.joinpath("tmp")

path_library_io_api_key = dir_tmp.joinpath("library_io_api_key.txt")
api_key = path_library_io_api_key.read_text().strip()

dir_cache = dir_tmp.joinpath(".cache")
cache = Cache(str(dir_cache))

libraries_io_username = "MacHu-GWU"
per_page = 30


def get_libraries(page: int):
    print(f"Fetching page {page} from libraries.io ...")
    time.sleep(1)
    url = (
        f"https://libraries.io/api/search?"
        f"platforms=PyPI"
        f"&q={libraries_io_username}"
        f"&per_page={per_page}"
        f"&page={page}"
        f"&api_key={api_key}"
    )
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()
    return data


@cache.memoize(expire=30 * 24 * 60 * 60)
def get_all_libraries() -> list[dict[str, T.Any]]:
    items = list()
    for page in range(1, 100 + 1):
        result = get_libraries(page)
        if not result:
            break
        items.extend(result)
    print(f"Done got {len(items)} libraries from libraries.io")
    return items


@cache.memoize(expire=30 * 24 * 60 * 60)
def get_last_month_download(package: str):
    print(f"Fetching download status of {package!r}")
    time.sleep(1)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
    }
    url = f"https://pypistats.org/api/packages/{package.lower()}/recent"
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()
    print("  Done")
    return data


black_list = {
    "diablo2_doc",
    "pyclopedia",
}

items = get_all_libraries()
records = list()
for item in items:
    name = item["name"]
    if name in black_list:
        continue
    data = get_last_month_download(name)
    # monthly_downloads = data["data"]["last_month"]
    # description = item["description"]
    records.append((item, data))
records = sorted(records, key=lambda tp: tp[1]["data"]["last_month"], reverse=True)

columns = ["package", "downloads", "description"]
rows = list()
for item, data in records:
    name = item["name"]
    description = item["description"]
    if description:
        description = description.strip()
    else:
        description = "No description"
    monthly_downloads = data["data"]["last_month"]

    package = f"[{name}](https://pypi.org/project/{name}/)"
    # downloads = f"![](https://img.shields.io/pypi/dm/{name}.svg)"
    downloads = f"{monthly_downloads}"
    rows.append((package, downloads, description))

tb = tabulate.tabulate(rows, headers=columns, tablefmt="github")
path_download_stats_ = dir_tmp.joinpath("pypi_download_stats.md")
path_download_stats_.write_text(str(tb))
