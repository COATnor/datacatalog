import ckan.plugins.toolkit as toolkit
from ckan.logic.action.create import package_create as ckan_package_create
from ckanext.coat.helpers import extras_dict, next_version
import string

allowed_characters = string.ascii_lowercase + string.digits + '-_'

@toolkit.side_effect_free
def package_create(context, data_dict):
    # parent dataset
    # https://github.com/aptivate/ckanext-datasetversions/issues/10
    if data_dict.get('__parent', False):
        return ckan_package_create(context, data_dict)

    # set base_name extra field, by mimicking slug-field
    base_name = ""
    for character in data_dict['title'].lower():
        if character in allowed_characters:
            base_name += character
        else:
            base_name += '-'
        base_name = base_name.replace('--', '-')
    base_name = base_name.strip('-')

    data_dict.setdefault('extras', [])
    if 'base_name' not in extras_dict(data_dict):
        data_dict['extras'].append(
            {'key': 'base_name', 'value': base_name},
         )

    # set version
    if not data_dict.get('version', ''):
        data_dict['version'] = '1'

    # append version to the name (it has to be unique)
    data_dict['name'] = base_name + '_v' + data_dict['version']

    # create package and version
    package = ckan_package_create(context, data_dict)
    toolkit.get_action('dataset_version_create')(
        context, {
            'id': package['id'],
            'base_name': base_name,
            'owner_org': data_dict['owner_org'],
            'type': data_dict['type'],
        }
    )

    return package
