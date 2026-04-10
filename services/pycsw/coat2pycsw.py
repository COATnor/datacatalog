import datetime
import json
import logging
import os
import time
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
    res = requests.get(package_search, params={"rows": 0})
    end = res.json()["result"]["count"]
    log.info("Found %d packages in COAT catalog", end)
    rows = 10
    for start in range(0, end, rows):
        res = requests.get(package_search, params={"start": start, "rows": rows})
        for dataset in res.json()["result"]["results"]:
            if dataset["type"] == "dataset":
                yield dataset


def get_bbox(dataset):
    for extra in dataset["extras"]:
        if extra["key"] == "spatial":
            break
    else:
        return
    return shape(json.loads(extra["value"])).bounds


with open("mappings/topics.yaml") as _f:
    coat2iso19115_topiccategory_mapping = yaml.safe_load(_f)


def coat2iso19115_topiccategory(category):
    """Compatibility workaround for old COAT topic category values"""
    return coat2iso19115_topiccategory_mapping.get(category, category)


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

    # https://github.com/geopython/pygeometa/blob/0.13.1/pygeometa/schemas/iso19139/main.j2
    for dataset in get_datasets(COAT_URL):
        dataset_url = urljoin(COAT_PUBLIC_URL, "dataset/" + dataset["name"])
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
                "topiccategory": [
                    coat2iso19115_topiccategory(dataset["topic_category"])
                ],
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
                    "individualname": dataset.get("author", ""),
                    "email": dataset.get("author_email", ""),
                },
                "distributor": {
                    "individualname": "Francesco Frassinelli",
                    "organisation": "NINA",
                    "positionname": "Senior engineer IT",
                    "url": "https://www.nina.no/english/Contact/Employees/Employee-info?AnsattID=15958",
                },
                "CI_ResponsibleParty": {
                    "individualname": dataset.get("author", ""),
                    "email": dataset.get("author_email", ""),
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
                    "url": urljoin(dataset_url, "zip"),
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
