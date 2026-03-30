# -*- coding: utf-8 -*-

import ckan.logic as logic
import ckan.model as model
from ckanext.scheming.helpers import scheming_get_dataset_schema
import json
import os

file_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'presets')
_get_or_bust = logic.get_or_bust


def data_dict_with_spatial(context, data_dict):
    #t = _get_or_bust(data_dict, "type")
    t = 'dataset'
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
    lon_min, lon_max = min(longitudes)-e, max(longitudes)+e
    lat_min, lat_max = min(latitudes)-e, max(latitudes)+e
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


def scheming_dataset_choices(field, dataset_type='dataset'):
    params = {
        'q': ' AND '.join([
            'dataset_type:'+dataset_type,
            'state:active',
            'version_i:*',
        ]),
        'include_private': True,
        'rows': 0,
    }
    params['rows'] = logic.get_action('ckan_package_search')({}, params)['count']
    search = logic.get_action('ckan_package_search')({}, params)
    for dataset in search['results']:
        label = dataset['name']
        if 'temporal_start' in dataset and 'temporal_end' in dataset:
            label += " ({temporal_start} -> {temporal_end})".format(**dataset)
        yield {
            'value': dataset['name'],
            'label': label,
        }


def scheming_protocol_choices(field):
    yield from scheming_dataset_choices(field, dataset_type='protocol')


def scheming_author_choice(field):
    for user in model.user.User.all():
        if user.name in ('default',): # 'administrator'
            continue
        yield {
            'value': user.name,
            'label': user.fullname or user.name,
        }


def authors_fullnames():
    fullnames = {}
    for user in model.user.User.all():
        if user.name in ('default',):
            continue
        if user.fullname:
            fullnames[user.name] = user.fullname
            if user.email:
                fullnames[user.email] = user.fullname
    return fullnames


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

    fullnames = authors_fullnames()
    resolved = [fullnames.get(e, e) for e in author.split(",") if e]

    if not resolved:
        return None
    return resolved[0] + (" et al." if len(resolved) > 1 else "")


def scheming_author_choice_required(field):
    yield {
        'value': '',
        'label': "-- Select a name --",
    }
    for choice in scheming_author_choice(field):
        yield choice


def scheming_protocol_choice(field):
    params = {
        'q': ' AND '.join([
            'dataset_type:protocol',
            'state:active',
            'version_i:*',
        ]),
        'include_private': True,
        'rows': 0,
    }
    params['rows'] = logic.get_action('ckan_package_search')({}, params)['count']
    search = logic.get_action('ckan_package_search')({}, params)
    for dataset in search['results']:
        label = dataset['name']
        yield {
            'value': dataset['name'],
            'label': label,
        }


def scheming_protocol_choice_required(field):
    yield {
        'value': '',
        'label': "-- Select a protocol --",
    }
    for choice in scheming_protocol_choice(field):
        yield choice


def get_site_statistics():
   stats = {}
   stats['dataset_count'] = logic.get_action('package_search')(
       {}, {"rows": 1})['count']
   stats['group_count'] = len(logic.get_action('group_list')({}, {}))
   stats['organization_count'] = len(
       logic.get_action('organization_list')({}, {}))
   stats['user_count'] = len(
       logic.get_action('user_list')({}, {}))
   return stats


with open(os.path.join(file_dir, 'publishers.json')) as publishers_file:
    publishers = json.load(publishers_file)


def scheming_publisher_choices(field):
    return publishers


def scheming_publisher_tags(field=None):
    for publisher in scheming_publisher_choices(field):
        yield publisher['value']


def scheming_publisher_choices_required(field):
    yield {"value": "", "label": "-- Select a publisher --"}
    for entry in scheming_publisher_choices(field):
        yield entry


with open(os.path.join(file_dir, 'tags.json')) as tags_file:
    tags = json.load(tags_file)


def scheming_coat_tags(field=None):
    for tag in tags:
        yield tag['value']


with open(os.path.join(file_dir, 'locations.json')) as locations_file:
    locations = json.load(locations_file)


def scheming_locations_choices(field):
    return locations


def scheming_locations_tags(field=None):
    for location in locations:
        yield location['label']


with open(os.path.join(file_dir, 'categories.json')) as categories_file:
    categories = json.load(categories_file)


def scheming_topic_category_choices(field):
    return categories


def scheming_topic_category_choices_required(field):
    choices = [
        {"value": "", "label": "-- Select a category --"},
    ]
    choices.extend(scheming_topic_category_choices(field))
    return choices


with open(os.path.join(file_dir, 'names.json')) as names_file:
    names = []
    for name in json.load(names_file):
        names.append({
            'label': name,
            'value': name.split(' - ')[-1].split('(')[0]
        })


def scheming_scientific_name_choices(field):
    return names


def scheming_scientific_name_tags(field=None):
    for scientific_name in scheming_scientific_name_choices(field):
        yield scientific_name['value']
