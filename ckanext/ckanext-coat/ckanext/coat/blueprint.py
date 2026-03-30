import copy
import datetime
import os

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
from ckan.common import _
from flask import Blueprint

from ckanext.coat.helpers import (
    extras_dict,
    get_resource_path,
    new_context,
    next_version,
)
from ckanext.datasetversions.helpers import get_context

coat = Blueprint('coat', __name__)

def new_version(uid):
    context = new_context()
    data_dict = {'id': uid}

    # check if package exists
    try:
        package = toolkit.get_action('package_show')(context, data_dict)
    except (logic.NotFound, logic.NotAuthorized):
        base.abort(404, _('Dataset not found'))

    resources = package['resources']
    context = get_context(context)  # needed ?

    # remove references to the original package
    for key in ('id', 'revision_id'):
        if key in package:
            del package[key]

    # remove also doi entry:
    for key in ('doi', 'doi_date_published', 'doi_publisher', 'doi_status'):
        if key in package:
            del package[key]

    # update the new package values
    base_name = extras_dict(package)['base_name']
    package.update({
        'resources': [],
        'metadata_created': datetime.datetime.now(),
        'medatata_modified': datetime.datetime.now(),
        'name': base_name,
        'private': True,
        'version': next_version(package),
    })

    # save the package
    package_new = toolkit.get_action('package_create')(context, package)

    # populate the new package with the old resources
    for original_resource in resources:
        # clone the resource
        resource = copy.deepcopy(original_resource)
        for key in ('id', 'revision_id'):
            if key in resource:
                del resource[key]
        # modify the new resource
        resource['package_id'] = package_new['id']
        if resource['url_type'] != 'upload':
            resource['url'] = resource['name']
        resource_new = toolkit.get_action('resource_create')(context, resource)
        # avoid hardlinking when cloning link resources
        if resource['url_type'] != "upload":
            continue
        src = get_resource_path(original_resource)
        dst = get_resource_path(resource_new)
        dst_dir = os.path.dirname(dst)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        os.link(src, dst)

    return h.redirect_to('dataset.read', id=base_name)

coat.add_url_rule(u'/dataset/<uid>/new_version', view_func=new_version)