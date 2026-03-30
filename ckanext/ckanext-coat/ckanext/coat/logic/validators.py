from ckan.plugins.toolkit import Invalid
import ckan.plugins.toolkit as toolkit
from ckanext.coat.helpers import extras_dict
from ckan.common import config
import os.path

def lowercase_extension(value):
    filename, extension = os.path.splitext(value)
    return filename+extension.lower()

def _resource_name_conflict_global(context, pkg_dict, name, url):
    model = context['model']
    session = context['session']
    extras = extras_dict(pkg_dict)
    result = session.query(model.Package) \
        .join(model.PackageExtra,
            model.PackageExtra.package_id == model.Package.id) \
        .join(model.Resource,
            model.Resource.package_id == model.Package.id) \
        .filter(
            model.PackageExtra.key == 'base_name',
            model.PackageExtra.value != extras['base_name'],
            model.Resource.name.ilike(name),
            model.Resource.url != url,
        ).first()
    if result:
        raise Invalid('Resource with the same name already exists: ' + name)

def _resource_name_conflict_local(context, pkg_dict, name):
    for resource in pkg_dict['resources']:
        if resource['name'].lower() == name.lower():
            raise Invalid('Resource with the same name in the same ' \
                          'dataset already exists: ' + name)

def resource_name_conflict(key, data, errors, context):
    name = new_resource_id = data[(key[0], key[1], 'name')]
    pkg_dict = toolkit.get_action('package_show')(
        context, {'id': context['package'].id})
    if data.get((key[0], key[1], 'id')):
        # not a new resource
        # existing resources cannot be renamed due to helpers.is_protected
        return name
    if not name.strip():
        raise Invalid('Name cannot be empty')
    _resource_name_conflict_local(context, pkg_dict, name)
    globally_unique = config.get('ckanext.coat.resource_name_globally_unique', 'false').lower() == 'true'
    if globally_unique:
        url = data.get((key[0], key[1], 'url'))
        _resource_name_conflict_global(context, pkg_dict, name, url)
    return name

def private_on_creation(value):
    if value:
        return value
    raise Invalid('New datasets cannot be public (please set "Visibility" to "Private")')
