#!/usr/bin/env python3
"""Uploading defaults data on CKAN."""

import yaml
import requests

from helpers.requests import raise_for_status_verbose

import argparse
import os


@raise_for_status_verbose
def organization_create(server, headers, data):
    """Create an organization."""
    return requests.post(f"{server}/api/action/organization_create",
                         headers=headers, data=data)


# Parser
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--server', default='http://localhost:5000',
                    help='CKAN server')
parser.add_argument('--initial', default='initial.yaml',
                    help='Defaults data file')
args = parser.parse_args()

defaults = yaml.load(open(args.initial).read())
headers = {'Authorization': os.environ['CKAN_API_KEY']}

for organization in defaults['organizations']:
    res = organization_create(args.server, headers, organization)
