# -*- coding: utf-8 -*-

"""
Requirements::

    pip install -U pypistats

Google Sheet: https://docs.google.com/spreadsheets/d/1iDPOgXn0PqxlMWdUH6guUKYdaTZN6JC78Nv-WL6J6kY/edit?gid=0#gid=0
"""

import typing as T
import time
import json
from datetime import date
from pathlib import Path

import requests
from diskcache import Cache

cache = Cache(".cache")

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"}

def get_last_month_download(package: str) -> int:
    print(f"work on {package}")
    if package in cache:
        print("  fetching from Cache ...")
        n = cache[package]
    else:
        print("  fetching from API ...")
        time.sleep(1)
        url = f"https://pypistats.org/api/packages/{package}/recent"
        res = requests.get(url, headers=headers)
        text = res.text
        print(text)
        data = json.loads(text)
        n = data["data"]["last_month"]
        cache[package] = n
    print(f"    {n}")
    return n


# https://pypi.org/manage/projects/
package_list = """
aws-dynamodb-io
simple-aws-ecr
aws-lambda-layer
aws-sdk-polars
pynamodb-mate
compress
aws-glue-catalog
dbsnaplake
jsonpolars
simpletype
polars-writer
s3pathlib
s3manifesto
fast-dynamodb-json
acore-server-bootstrap
acore-server-monitoring-measurement
acore-paths
acore-constants
acore-server-monitoring-core
acore-soap-remote
acore-soap-agent
acore-soap
acore-server
acore-server-config
hotkeynet
acore-soap-app
acore-df
aws-ops-alpha
wow-sdm
acore-db-app
wow-wtf
wow-acc
acore-server-metadata
packer-ami-workflow
acore-db-ssh-tunnel
ssh2awsec2
simple-aws-ec2
simple-aws-rds
aws-ssm-run-command
config-patterns
vislog
acore-conf
sqlalchemy-mate
aws-textract
aws-textract-pipeline
aws-comprehend
findref
aws-glue-container-launcher
docfly
aws-console-url-search
aws-resource-search
windtalker
zelfred
awscli-mate
attrs-mate
pathlib-mate
boto-session-manager
pyproject-ops
picage
unistream
abstract-tracker
tt4human
afwf
fixa
gh-action-open-id-in-aws
virtualenv-bootstrap
aws-console-url
cross-aws-account-iam-role
pysecret
aws-cloudformation
iterproxy
sayt
aws-arns
versioned
jmespath-token
afwf-shell
git-web-url
aws-glue-artifact
airflow-dag-artifact
aws-a2i
cookiecutter-maker
sftp-to-s3
dataclasses-sqlitedict
pygitrepo
cottonformation
aws-lambda-event
aws-stepfunction
light-emoji
func-args
aws-codecommit
aws-codebuild
rstobj
dynamodb-cache
# loggerFactory
lakeformation
superjson
configirl
uszipcode
aws-text-insight
pgr
s3splitmerge
troposphere-mate
crawlib
mongoengine-mate
lbdrabbit
s3iotools
pylbd
sfm
dba
dupe-remove
rolex
constant2
invsearch
loc
inspect_mate
apipool
mongomock-mate
pytq-crawlib
attrsmallow
convert2
pytq
fileshelf
utf8config
pymongo_mate
elementary_math
ezinstall
crawl_redfin
cazipcode
pandas_mate
constant
# dataIO
# autocompvar
# crawl_trulia
# crawl_zillow
# diablo2_doc
# macro
# potplayer
# filetool
# wechinelearn
# ctmatching
# pyclopedia
# crosys
# ssan
# angora
# geomate
# canbeAny
# pyknackhq
# sqlite4dummy
""".strip().splitlines()

lines: T.List[str] = list()
line = "\t".join(["name", "monthly_downloads"])
lines.append(line)
for package in package_list:
    if package.startswith("#"):
        continue
    n = get_last_month_download(package)
    print(package, n)
    line = "\t".join([package, str(n)])
    lines.append(line)


filename = f"pypi_download_status_{date.today()}.tsv"
Path(filename).write_text("\n".join(lines))
