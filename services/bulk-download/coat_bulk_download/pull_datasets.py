import logging
import traceback
import urllib.parse

import httpx

from .config import COAT_URL, GEOJSON_PATH
from .geojson import MissingDataException, handle_dataset

logger = logging.getLogger(__name__)


def get_datasets():
    package_search = urllib.parse.urljoin(COAT_URL, "api/3/action/package_search?q=type:dataset")
    response = httpx.get(package_search).json()
    datasets = response["result"]["results"]

    for dataset in datasets:
        logger.info(f"processing {dataset['title']}")
        f = GEOJSON_PATH / dataset["name"]
        try:
            if f.exists():
                f.unlink()
            handle_dataset(dataset)
        except MissingDataException as exc:
            logger.warning("%s, %s, %s", dataset["name"], MissingDataException, exc)
        except Exception:
            logger.error("%s, %s", dataset["name"], traceback.format_exc())


if __name__ == "__main__":
    get_datasets()
