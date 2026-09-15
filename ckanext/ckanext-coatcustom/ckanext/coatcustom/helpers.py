import json
import re
from pathlib import Path

import ckan.logic as logic
import ckan.model as model
import yaml

from ckanext.scheming.helpers import scheming_get_dataset_schema

file_dir = Path(__file__).resolve().parent / "presets"
_get_or_bust = logic.get_or_bust


def data_dict_with_spatial(context, data_dict, old_location=None):
    if old_location is not None and old_location == data_dict.get("location"):
        return data_dict
    # t = _get_or_bust(data_dict, "type")
    t = "dataset"
    expanded = data_dict.get("expanded", True)
    s = scheming_get_dataset_schema(t, expanded)

    longitudes = []
    latitudes = []
    for field in s["dataset_fields"]:
        if field["field_name"] != "location":
            continue
        for choice in locations:
            value = choice["label"].split(" - ")[-1]
            if value not in (data_dict.get("location") or []):
                continue
            longitudes.append(choice["lon"])
            latitudes.append(choice["lat"])

    if not longitudes or not latitudes:
        return data_dict

    # create buffer (needed to index single-point bboxes)
    # longitude buffer: < 5.6 meters at latitude > 60 degrees
    # latitude buffer: ~11 meters
    e = 0.0001
    lon_min, lon_max = min(longitudes) - e, max(longitudes) + e
    lat_min, lat_max = min(latitudes) - e, max(latitudes) + e
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [lon_min, lat_max],
                [lon_max, lat_max],
                [lon_max, lat_min],
                [lon_min, lat_min],
                [lon_min, lat_max],
            ]
        ],
    }

    value = json.dumps(geometry)
    data_dict.setdefault("extras", [])  # ?
    for item in data_dict["extras"]:
        if item.get("key") == "spatial":
            item["value"] = value
            break
    else:
        data_dict["extras"].append({"key": "spatial", "value": value})

    return data_dict


def scheming_dataset_choices(field, dataset_type="dataset"):
    params = {
        "q": " AND ".join(
            [
                "dataset_type:" + dataset_type,
                "state:active",
                "version_i:*",
            ]
        ),
        "include_private": True,
        "rows": 0,
    }
    params["rows"] = logic.get_action("ckan_package_search")({}, params)["count"]
    search = logic.get_action("ckan_package_search")({}, params)
    for dataset in search["results"]:
        label = dataset["name"]
        if "temporal_start" in dataset and "temporal_end" in dataset:
            label += " ({temporal_start} -> {temporal_end})".format(**dataset)
        yield {
            "value": dataset["name"],
            "label": label,
        }


def scheming_protocol_choices(field):
    yield from scheming_dataset_choices(field, dataset_type="protocol")


def scheming_author_choice(field):
    for user in model.user.User.all():
        if user.name in ("default",):  # 'administrator'
            continue
        yield {
            "value": user.name,
            "label": user.fullname or user.name,
        }


def authors_fullnames():
    fullnames = {}
    for user in model.user.User.all():
        if user.name in ("default",):
            continue
        if user.fullname:
            fullnames[user.name] = user.fullname
            if user.email:
                fullnames[user.email] = user.fullname
    return fullnames


def scheming_author_autocomplete_tags(field=None):
    """Suggest authors in ``Full Name <email>`` form so the stored value stays parseable."""
    for user in model.user.User.all():
        if user.name in ("default",):
            continue
        fullname = user.fullname or user.name
        email = (user.email or "").strip()
        if email:
            yield f"{fullname} <{email}>"
        else:
            yield user.name


def authors_display_from_parsed(parsed):
    """Format parsed authors as "First Author" or "First Author et al."."""
    resolved = [a["name"] for a in parsed if a["name"]]
    if not resolved:
        return None
    return resolved[0] + (" et al." if len(resolved) > 1 else "")


def coatcustom_get_authors_display(pkg_dict):
    """Resolve author usernames/emails to full display names.

    Works for both datasets (single author) and state variables (comma-separated
    list of authors merged from linked datasets).
    Returns "First Author" for one author, "First Author et al." for multiple.
    Returns None if no author can be resolved.
    """
    author = pkg_dict.get("author")
    if not author:
        return None
    return authors_display_from_parsed(parse_authors(author))


def scheming_author_choice_required(field):
    yield {
        "value": "",
        "label": "-- Select a name --",
    }
    yield from scheming_author_choice(field)


def scheming_protocol_choice(field):
    params = {
        "q": " AND ".join(
            [
                "dataset_type:protocol",
                "state:active",
                "version_i:*",
            ]
        ),
        "include_private": True,
        "rows": 0,
    }
    params["rows"] = logic.get_action("ckan_package_search")({}, params)["count"]
    search = logic.get_action("ckan_package_search")({}, params)
    for dataset in search["results"]:
        label = dataset["name"]
        yield {
            "value": dataset["name"],
            "label": label,
        }


def scheming_protocol_choice_required(field):
    yield {
        "value": "",
        "label": "-- Select a protocol --",
    }
    yield from scheming_protocol_choice(field)


def get_site_statistics():
    stats = {}
    stats["dataset_count"] = logic.get_action("package_search")({}, {"rows": 1})["count"]
    stats["group_count"] = len(logic.get_action("group_list")({}, {}))
    stats["organization_count"] = len(logic.get_action("organization_list")({}, {}))
    stats["user_count"] = len(logic.get_action("user_list")({}, {}))
    return stats


with (file_dir / "publishers.yml").open() as publishers_file:
    publishers = yaml.safe_load(publishers_file)


def scheming_publisher_choices(field):
    return publishers


def scheming_publisher_tags(field=None):
    for publisher in scheming_publisher_choices(field):
        yield publisher["value"]


def scheming_publisher_choices_required(field):
    yield {"value": "", "label": "-- Select a publisher --"}
    yield from scheming_publisher_choices(field)


def publisher_from_email(email):
    """Map an email address to its publisher short code (e.g. uit.no -> UiT)."""
    domain = (email or "").strip().rsplit("@", 1)[-1].lower()
    for publisher in publishers:
        if domain in publisher.get("domains", []):
            return publisher["value"]
    return None


def publishers_from_emails(emails):
    """Resolve email addresses to publisher short codes.

    Unknown domains are skipped. Returns a comma-separated string of
    unique codes.
    """
    codes = []
    seen = set()
    for email in emails:
        code = publisher_from_email(email)
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
    return ",".join(codes)


def publishers_from_authors(author):
    """Resolve an author list to the set of publisher short codes.

    Emails are extracted via :func:`parse_authors` (handles usernames and
    ``Name <email>`` tokens); unknown domains are skipped. Returns a
    comma-separated string of unique codes.
    """
    return publishers_from_emails(author_emails(author))


ANGLE_PATTERN = re.compile(
    r"""
    (?P<name>.*?) \s* < (?P<email>[^<>\s]+) > $
    """,
    re.VERBOSE,
)


def parse_authors(authors):
    """Parse a comma-separated list of authors into ``{"name", "email"}`` dicts.

    Each entry may be a plain email or username, or a ``Name Surname <email>``
    form. Usernames/emails are resolved to full names via the user list when
    possible. Anything else is kept as a raw name. Returns a list.
    """
    fullnames = authors_fullnames()
    parsed = []
    for author in (authors or "").split(","):
        author = author.strip()
        if not author:
            continue
        match = ANGLE_PATTERN.match(author)
        if match:
            name = match.group("name") or None
            email = match.group("email")
        else:
            name, email = None, author
        if "@" not in email:
            user = model.user.User.get(email)
            if user is None:
                parsed.append({"name": name or author, "email": ""})
                continue
            email = (user.email or "").strip()
            name = name or user.fullname or user.name
        elif not name:
            name = fullnames.get(email) or email
        parsed.append({"name": name, "email": email})
    return parsed


def author_emails(author):
    """Return the list of email addresses parsed from an author field."""
    return [a["email"] for a in parse_authors(author) if a["email"]]


def authors_display_names(author):
    """Return a comma-separated string of author display names.

    Names are resolved via :func:`parse_authors` (usernames/emails resolved to
    full names when possible). Returns an empty string when there are none.
    """
    names = [a["name"] for a in parse_authors(author) if a["name"]]
    return ", ".join(names)


with (file_dir / "tags.yml").open() as tags_file:
    tags = yaml.safe_load(tags_file)


def scheming_coat_tags(field=None):
    for tag in tags:
        yield tag["value"]


with (file_dir / "locations.yml").open() as locations_file:
    locations = yaml.safe_load(locations_file)


def scheming_locations_choices(field):
    return locations


def scheming_locations_tags(field=None):
    for location in locations:
        yield location["label"]


with (file_dir / "categories.yml").open() as categories_file:
    categories = yaml.safe_load(categories_file)


def scheming_topic_category_choices(field):
    return categories


def scheming_topic_category_choices_required(field):
    choices = [
        {"value": "", "label": "-- Select a category --"},
    ]
    choices.extend(scheming_topic_category_choices(field))
    return choices


with (file_dir / "names.yml").open() as names_file:
    names = []
    for name in yaml.safe_load(names_file):
        names.append({"label": name, "value": name.split(" - ")[-1].split("(")[0]})


def scheming_scientific_name_choices(field):
    return names


def scheming_scientific_name_tags(field=None):
    for scientific_name in scheming_scientific_name_choices(field):
        yield scientific_name["value"]
