import ckan.lib.uploader as uploader
import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as toolkit
from ckan.common import g

from ckanext.coat import auth


def is_resource(obj):
    return 'package_id' in obj

def extras_dict(package):
    return {f['key']:f['value'] for f in package.get('extras', {})}

def new_context():
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'for_view': True,
        'auth_user_obj': g.userobj,
    }
    for attr in ('user', 'userobj'):
        if hasattr(g, attr):
            context[attr] = getattr(g, attr)
    return context

def get_package(obj, context=None):
    if not context:
        context = new_context()
    if is_resource(obj):
        data_dict = {'id': obj['package_id']}
    else:
        for attr in ('id', 'name_or_id'):
            if attr in obj:
                data_dict = {attr: obj[attr]}
                break
    return toolkit.get_action('ckan_package_show')(context, data_dict)

def is_public(package):
    return not package.get('private', False)

def is_protected(obj, action='update'):
    if is_resource(obj):
        if action == 'update':
            return # WORKAROUND FOR BULK UPLOAD
            raise toolkit.NotAuthorized('Cannot modify a resource: you have to delete it first')
        package = get_package(obj)
    else:
        package = obj
    if is_public(package):
        if g.userobj and g.userobj.sysadmin:
            return  # sysadmins may modify public datasets
        raise toolkit.NotAuthorized('Public datasets cannot be modified: make it private if you really need to amend some information')

def next_version(obj):
    version = obj.get('version', '1')
    if version.isdigit():
        version = str(int(version)+1)
    return version

def get_resource_path(res):
    return uploader.get_resource_uploader(res).get_path(res['id'])

def is_under_embargo(package):
    context = new_context()
    try:
        auth.embargo_access(context, package)
    except logic.NotAuthorized:
        return True
    return False

