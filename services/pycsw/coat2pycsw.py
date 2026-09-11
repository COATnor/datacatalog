#!/usr/bin/env python3
import datetime
import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import urljoin

import pycsw.core.admin
import pycsw.core.config
import requests
import yaml
from pycsw.core import metadata, repository, util
from pygeometa.core import read_mcf
from pygeometa.schemas.iso19139 import ISO19139OutputSchema
from shapely.geometry import shape
from sqlalchemy.exc import OperationalError
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_delay

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

COAT_URL = os.environ["COAT_URL"]
COAT_PUBLIC_URL = os.getenv("COAT_PUBLIC_URL", COAT_URL)
DATABASE = os.environ["DATABASE"]
TABLE = "records"
INTERVAL = int(os.getenv("INTERVAL", 86400))


def get_datasets(url):
    package_search = urljoin(url, "api/3/action/package_search")
    package_show = urljoin(url, "api/3/action/package_show")
    res = requests.get(package_search, params={"rows": 0}, timeout=10)
    end = res.json()["result"]["count"]
    log.info("Found %d packages in COAT catalog", end)
    rows = 10
    for start in range(0, end, rows):
        res = requests.get(package_search, params={"start": start, "rows": rows}, timeout=10)
        for dataset in res.json()["result"]["results"]:
            if dataset["type"] != "dataset":
                continue
            # Harvest the full record via package_show so derived fields
            # (e.g. resource_citations) are computed once by the plugin.
            show = requests.post(package_show, json={"id": dataset["name"]}, timeout=10)
            show.raise_for_status()
            yield show.json()["result"]


def get_bbox(dataset):
    for extra in dataset["extras"]:
        if extra["key"] == "spatial":
            break
    else:
        return
    return shape(json.loads(extra["value"])).bounds


with Path("mappings/topics.yaml").open() as _f:
    coat2iso19115_topiccategory_mapping = yaml.safe_load(_f)

with Path("mappings/publishers.yml").open() as _f:
    publishers = yaml.safe_load(_f)


def coat2iso19115_topiccategory(category):
    """Compatibility workaround for old COAT topic category values"""
    return coat2iso19115_topiccategory_mapping.get(category, category)


def publisher_label_from_email(email):
    """Resolve the full organization label from an author's email domain."""
    domain = (email or "").strip().rsplit("@", 1)[-1].lower()
    for publisher in publishers:
        if domain in publisher.get("domains", []):
            return publisher["label"]
    return None


def fetch_fullnames(url):
    """Build a lookup of author email -> full name from the public user list."""
    user_list = urljoin(url, "api/3/action/user_list")
    res = requests.get(user_list, params={"all_fields": True}, timeout=10)
    names = {}
    for user in res.json()["result"]:
        fullname = user.get("fullname") or user.get("name") or ""
        names.setdefault(user.get("email"), fullname)
        names.setdefault(user.get("name"), fullname)
    return names


def parse_contact(author, fullnames, fallback_email=""):
    """Split an author value into ``(display name, email)``.

    Handles plain emails, usernames, and ``Name <email>`` tokens (mirrors
    ``ckanext.coatcustom.helpers.parse_authors`` for the single-author
    dataset case, using the pre-fetched ``fullnames`` lookup).
    """
    token = (author or "").strip()
    if not token:
        return "", (fallback_email or "").strip()
    if "<" in token and ">" in token:
        name_part, _, rest = token.partition("<")
        email = rest.partition(">")[0].strip()
        name = name_part.strip() or fullnames.get(email, email)
        return name, email
    if "@" in token:
        email = token.strip()
        return fullnames.get(email, email), email
    # username: resolve display name via lookup, email via derived field
    email = (fallback_email or "").strip()
    return fullnames.get(token, token), email


def normalize_datetime(timestamp):
    if not timestamp:
        return timestamp
    parsed = datetime.datetime.fromisoformat(timestamp)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


@retry(
    stop=stop_after_delay(int(os.getenv("TIMEOUT", 300))),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
    before_sleep=before_sleep_log(log, logging.WARNING),
)
def main():
    log.info("Fetching datasets from %s", COAT_URL)
    context = pycsw.core.config.StaticContext()
    try:
        repository.setup(DATABASE, TABLE)
    except OperationalError:
        log.debug("Database already set up")

    pycsw.core.admin.delete_records(context, DATABASE, TABLE)
    repo = repository.Repository(DATABASE, context, table=TABLE)

    fullnames = fetch_fullnames(COAT_URL)

    # https://github.com/geopython/pygeometa/blob/0.19.0/pygeometa/schemas/iso19139/contact.j2
    for dataset in get_datasets(COAT_URL):
        dataset_url = urljoin(COAT_PUBLIC_URL, "dataset/" + dataset["name"])
        author = dataset.get("author", "")
        derived_email = dataset.get("author_email", "") or ""
        if isinstance(derived_email, list):
            derived_email = derived_email[0] if derived_email else ""
        individualname, email = parse_contact(author, fullnames, derived_email)
        organization = publisher_label_from_email(email)
        dataset_metadata = {
            "mcf": {"version": 1.0},
            "metadata": {
                "identifier": dataset["id"],
                "language": "en",
                "charset": "utf8",
                "datestamp": normalize_datetime(dataset["metadata_modified"]),
                "dataseturi": dataset_url,
            },
            "spatial": {"datatype": "vector", "geomtype": "point"},
            "identification": {
                "language": "en",
                "charset": "utf8",
                "title": {"en": dataset["title"]},
                "abstract": {"en": dataset["notes"]},
                "edition": dataset["version"],
                "dates": {"creation": normalize_datetime(dataset["metadata_created"])},
                "keywords": {
                    "default": {
                        "keywords": {
                            "en": [tag["name"] for tag in dataset["tags"]],
                        }
                    }
                },
                "topiccategory": [coat2iso19115_topiccategory(dataset["topic_category"])],
                "extents": {
                    "spatial": [{"bbox": get_bbox(dataset), "crs": 4326}],
                    "temporal": [
                        {
                            "begin": normalize_datetime(dataset.get("temporal_start")),
                            "end": normalize_datetime(dataset.get("temporal_end")),
                        }
                    ],
                },
                "fees": "None",
                "uselimitation": dataset["license_id"].replace("_", "-"),
                "accessconstraints": "otherRestrictions",
                "rights": {
                    "en": dataset["resource_citations"],
                },
                "url": dataset_url,
                "status": "onGoing",
                "maintenancefrequency": "continual",
            },
            "contact": {
                "pointOfContact": {
                    "individualname": individualname,
                    "email": email,
                    "organization": organization,
                },
                "distributor": {
                    "individualname": "Francesco Frassinelli",
                    "organization": "Norwegian Institute for Nature Research",
                    "positionname": "Senior engineer IT",
                    "url": "https://www.nina.no/vare-ansatte/francesco-frassinelli",
                },
            },
            "distribution": {
                "landingpage": {
                    "url": dataset_url,
                    "type": "WWW:LINK-1.0-http--link",
                    "rel": "canonical",
                    "name": 'Landing page for dataset "' + dataset["name"] + '"',
                    "description": {
                        "en": 'Landing page for dataset "' + dataset["name"] + '"',
                    },
                    "function": "download",
                },
                "zip": {
                    "url": urljoin(dataset_url + "/", "zip"),
                    "type": "WWW:DOWNLOAD-1.0-http--download",
                    "rel": "canonical",
                    "name": 'ZIP-compressed dataset "' + dataset["name"] + '"',
                    "description": {
                        "en": 'ZIP-compressed dataset "' + dataset["name"] + '"',
                    },
                    "function": "download",
                },
            },
        }

        mcf_dict = read_mcf(dataset_metadata)
        iso_os = ISO19139OutputSchema()
        xml_string = iso_os.write(mcf_dict)

        record = metadata.parse_record(context, xml_string, repo)[0]
        repo.insert(record, "local", util.get_today_and_now())
        log.info("Indexed dataset %s", dataset["name"])

    log.info("Done indexing")


if __name__ == "__main__":
    while True:
        main()
        log.info("Sleeping for %d seconds", INTERVAL)
        time.sleep(INTERVAL)
