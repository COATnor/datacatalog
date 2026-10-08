import logging
import re
import threading
from urllib.parse import urlsplit

import ckan.model as model
import ckan.plugins.toolkit as toolkit
import requests

log = logging.getLogger(__name__)

BULK_EVENT = "Dataset bulk download"
RESOURCE_EVENT = "Resource download"
BUNDLE_RESOURCE_NAME = "All resource data"

BULK_RE = re.compile(r"^/dataset/[^/]+/download_all$")
RESOURCE_RE = re.compile(r"^/dataset/[^/]+/resource/([^/]+)/download(/[^/]+)?$")


def enabled():
    return toolkit.asbool(toolkit.config.get("ckanext.coat.plausible_download_events", False))


def host():
    return toolkit.config.get("ckanext.coat.plausible_host", "https://plausible.io").rstrip("/")


def domain():
    return urlsplit(toolkit.config.get("ckan.site_url", "")).hostname or ""


def match_bulk_download(path):
    if BULK_RE.match(path or ""):
        return path.split("/")[2]
    return None


def match_resource_download(path):
    found = RESOURCE_RE.match(path or "")
    return found.group(1) if found else None


def package_names(package_id):
    package = toolkit.get_action("package_show")(
        {"ignore_auth": True, "model": model, "session": model.Session},
        {"id": package_id},
    )
    extras = {item["key"]: item["value"] for item in package.get("extras", [])}
    name = package["name"]
    return name, extras.get("base_name") or name


def resource_names(resource_id):
    resource = toolkit.get_action("resource_show")(
        {"ignore_auth": True, "model": model, "session": model.Session},
        {"id": resource_id},
    )
    name, base_name = package_names(resource["package_id"])
    return name, base_name, resource["name"]


def payload(event, url, dataset, base_name, resource=None):
    props = {"dataset": dataset, "base_name": base_name}
    if resource is not None:
        props["resource"] = resource
    return {"domain": domain(), "name": event, "url": url, "props": props}


def send_event(event_payload, user_agent, ip):
    try:
        requests.post(
            host() + "/api/event",
            json=event_payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": user_agent,
                "X-Forwarded-For": ip,
            },
            timeout=2,
        )
    except Exception as error:
        log.debug("plausible download event dropped: %s", error)


def track(response):
    try:
        if not enabled() or response.status_code != 200:
            return None
        request = toolkit.request
        if request.method != "GET":
            return None
        dataset_id = match_bulk_download(request.path)
        if dataset_id:
            name, base_name = package_names(dataset_id)
            event_payload = payload(BULK_EVENT, request.url, name, base_name)
        else:
            resource_id = match_resource_download(request.path)
            if not resource_id:
                return None
            name, base_name, resource = resource_names(resource_id)
            if resource == BUNDLE_RESOURCE_NAME:
                event_payload = payload(BULK_EVENT, request.url, name, base_name)
            else:
                event_payload = payload(RESOURCE_EVENT, request.url, name, base_name, resource)
        user_agent = request.headers.get("User-Agent", "")
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        thread = threading.Thread(
            target=send_event, args=(event_payload, user_agent, ip), daemon=True
        )
        thread.start()
        return event_payload
    except Exception as error:
        log.debug("plausible download tracking skipped: %s", error)
        return None
