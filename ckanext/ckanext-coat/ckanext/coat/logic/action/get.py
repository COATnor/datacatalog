import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.model as model
from ckan.logic.action.get import package_search as ckan_package_search
from ckan.logic.action.get import resource_show as ckan_resource_show
from ckanext.coat import auth

@toolkit.side_effect_free
def package_search(context, data_dict):
    data_dict.setdefault('fq_list', [])
    data_dict['fq_list'].append(
        '{!collapse field=base_name max=version_i}'
    )
    return ckan_package_search(context, data_dict)

@toolkit.chained_action
def package_show(original_action, context, data_dict):
    package = original_action(context, data_dict)
    context['package'] = model.Package.get(package['name'])
    try:
        auth.embargo_access(context, data_dict)
    except logic.NotAuthorized:
        for resource in package['resources']:
            resource['url'] = "#resource-under-embargo"
    return package

@toolkit.side_effect_free
def resource_show(context, data_dict):
    resource = ckan_resource_show(context, data_dict)
    auth.embargo_access(context, resource)
    return resource
