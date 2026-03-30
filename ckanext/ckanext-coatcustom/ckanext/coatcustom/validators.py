import json

import ckan.plugins.toolkit as toolkit
from ckan.lib.navl import validators as ckan_validators
from ckan.logic import NotFound


def required_custom(key, data, errors, context):
    extras = data.get(('__extras',), {})
    if extras.get('__parent'):
        ckan_validators.ignore_missing(key, data, errors, context)
    else:
        ckan_validators.not_empty(key, data, errors, context)

def str_to_bool(value):
    return str(value).lower() == "true"

def bool_to_str(value):
    return str(value)

def commalist_to_json(value):
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        if type(value) == str:
            return value.split(',')
        else:
            return value

def select_parent_locations(selected_values, sep=" - "):
    if not selected_values:
        return []
    if type(selected_values) == str:
        selected_values = selected_values.split(',')
    elif type(selected_values) == list:
        selected_values = [selected_values]
    generated = set()
    for selected_value in selected_values:
        while sep in selected_value:
            generated.add(selected_value)
            selected_value, _ = selected_value.rsplit(sep, 1)
        generated.add(selected_value)
    return list(generated)

def list_to_tag_string(value):
    if type(value) in (list, set):
        return ','.join(v for v in value if v)
    else:
        return value

def tag_string_to_list(value):
    if type(value) in (list, set):
        return [v for v in value if v]
    elif isinstance(value, str):
        return [v.strip() for v in value.split(',') if v.strip()]
    else:
        return []


def _associated_datasets(data):
    context = {'ignore_auth': True}
    datasets = data.get(('datasets',), '')
    if datasets:
        for name in datasets.split(','):
            try:
                pkg = toolkit.get_action('ckan_package_show')(context, {'id': name})
            except NotFound:
                pass
            else:
                yield pkg

def merge_from_datasets(key, data, errors, context):
    sep = ","
    values = set()
    for package in _associated_datasets(data):
        parts = package.get(key[0])
        if not parts:
            continue
        if type(parts) == str:
            parts = parts.split(sep)
        for part in parts:
            part = part.strip()
            if part:
                values.add(part)
    data[key] = sep.join(values)

def merge_tags_from_datasets(key, data, errors, context):
    # Extract tags from datasets
    tags = set()
    for package in _associated_datasets(data):
        for tag in package['tags']:
            if tag:
                tags.add(tag['name'])
    data[key] = ",".join(tags)
    # Remove old tags
    #for data_key in data.copy().keys():
    #    if data_key[0] == 'tags':
    #        del data[data_key]
    # Create new tags
    toolkit.get_validator('tag_string_convert')(key, data, errors, context)
