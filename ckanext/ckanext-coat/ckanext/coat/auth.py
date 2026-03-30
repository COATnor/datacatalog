from datetime import datetime

import ckan.plugins.toolkit as toolkit

import ckanext.coat.helpers as h


def embargo_access(context, data_dict):
    package = h.get_package(data_dict, context)
    # In CKAN 2.10+, context['auth_user_obj'] is a Flask-Login proxy that is
    # truthy even for anonymous users (AnonymousUser has is_authenticated=False).
    # In CKAN 2.9, context['auth_user_obj'] was None for anonymous users.
    auth_user = context.get('auth_user_obj')
    is_anonymous = not auth_user or not getattr(auth_user, 'is_authenticated', bool(auth_user))
    if is_anonymous:
        embargo = package.get('embargo', None)
        if embargo:
            try:
                if datetime.now() < datetime.strptime(embargo, '%Y-%m-%d'):
                    raise toolkit.NotAuthorized('The dataset is under embargo until %s.' % embargo)
            except ValueError:
                pass # warning
