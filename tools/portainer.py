#!/usr/bin/env python3
"""Deploy stack on Portainer."""

from portainer.api import PortainerManager

import argparse
import os
import random
import string

# Parser
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('name', help='Name of the stack')
parser.add_argument('project_directory',
                    help="Working directory containing the Compose an file")
parser.add_argument('--server', default='http://localhost:9000',
                    help='Portainer server')
args = parser.parse_args()

# Stack name limitations:
#  - https://github.com/portainer/portainer/issues/2020
#  - https://github.com/portainer/portainer/issues/2289
clean = ''
for character in args.name.lower():
    if character in string.ascii_lowercase:
        clean += character

# Docker files
print("Reading docker-compose.yml...")
compose = open(args.project_directory+'/docker-compose.yml').read()
env = {}
print("Reading .env...")
for line in open(args.project_directory+'/.env').readlines():
    key, value = line.strip().split('=', 1)
    env[key] = value

# Workaround for https://github.com/portainer/portainer/issues/2354
compose = string.Template(compose).substitute(env)

# Initialization and authentication
manager = PortainerManager(
    server=args.server,
    username=os.environ['PORTAINER_USERNAME'],
    password=os.environ['PORTAINER_PASSWORD'],
    verify=False,  # HTTPS self-signed certificate workaround
)
print("Authenticating...")
manager.authentication()

# Create or update the stack
for stack in manager.stack_list():
    if stack['Name'] == args.name:
        print("Stack found. Updating...")
        manager.stack_update(stack['Id'], stack['EndpointId'], compose, env)
        break
else:
    print("Stack not found. Creating...")
    ids = [group['Id'] for group in manager.endpoint_list()]
    endpoint = random.choice(ids)
    manager.stack_create(args.name, endpoint, compose, env)

print("Done.")
