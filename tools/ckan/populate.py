#!/usr/bin/env python3
"""Uploading defaults data on CKAN."""

import yaml
import requests

import argparse
import os

defaults = yaml.load(open('initial.yaml').read())
headers = {'Authorization': os.environ['CKAN_API_KEY']}


def raise_for_status_verbose(req_function):
    """Decorate requests for extra error handling.

    It executes raise_for_status and add the server response to the error
    message.
    """
    def wrapper(*args, **kwargs):
        res = req_function(*args, **kwargs)
        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise type(error)(res.text) from error
        return res
    return wrapper


@raise_for_status_verbose
def organization_create(server, headers, data):
    """Create an organization."""
    return requests.post(f"{server}/api/action/organization_create",
                         headers=headers, data=data)


# Parser
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--server', default='http://localhost:5000',
                    help='CKAN server')
args = parser.parse_args()

for organization in defaults['organizations']:
    res = organization_create(args.server, headers, organization)
