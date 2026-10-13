import logging
import re

import ckan.model as model

from ckanext.coat import helpers

log = logging.getLogger(__name__)

BULK_RE = re.compile(r"^/dataset/([^/]+)/(download_all|zip)$")


def blocked_dataset(path):
    """Dataset name when a bulk-download URL targets an actively embargoed
    dataset, else None.

    Date-based rather than access-aware on purpose: ckanext-downloadall
    streams resources server-side without the viewer's credentials, so an
    embargoed dataset yields an empty zip for everyone. Refuse up front
    instead of failing mid-stream.
    """
    found = BULK_RE.match(path or "")
    if not found:
        return None
    try:
        package = model.Package.get(found.group(1))
        if package is None or package.state != "active":
            return None
        extras = dict(package.extras or {})
        if helpers.has_active_embargo({"embargo": extras.get("embargo"), "extras": extras}):
            return package.name
    except Exception as error:
        log.debug("embargo gate skipped: %s", error)
    return None
