#!/usr/bin/env python3

import requests

import argparse
import json
import os
import random
import string


def raise_for_status_verbose(req_function):
    def wrapper(*args, **kwargs):
        res = req_function(*args, **kwargs)
        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise type(error)(res.text) from error
        return res
    return wrapper


class PortainerManager:
    def __init__(self, server, username=None, password=None, **options):
        self.api = server+'/api'
        self.username = username
        self.password = password
        if not self.username:
            self.username = os.environ['PORTAINER_USERNAME']
        if not self.password:
            self.password = os.environ['PORTAINER_PASSWORD']
        self.opts = options
        self.opts['headers'] = {}

    @raise_for_status_verbose
    def _token_request(self):
        credentials = json.dumps({
            'Username': self.username,
            'Password': self.password,
        })
        return requests.post(self.api+'/auth', data=credentials, **self.opts)

    def authentication(self):
        token = self._token_request().json()['jwt']
        self.opts['headers']['Authorization'] = 'Bearer '+token

    @raise_for_status_verbose
    def _stack_list_request(self):
        return requests.get(self.api+'/stacks', **self.opts)

    def stack_list(self):
        return self._stack_list_request().json()

    @raise_for_status_verbose
    def stack_create(self, name, endpoint, stack, env):
        config = json.dumps({
            'StackFileContent': stack,
            'Env': [env],
            'Name': name,
        })
        params = {'type': 2, 'method': 'string', 'endpointId': str(endpoint)}
        return requests.post(f"{self.api}/stacks",
                             params=params, data=config, **self.opts)

    @raise_for_status_verbose
    def stack_update(self, uid, endpoint, stack, env):
        config = json.dumps({
            'StackFileContent': stack,
            'Env': [env],
            'Prune': True,
        })
        params = {'endpointId': str(endpoint)}
        return requests.put(f"{self.api}/stacks/{uid}",
                            params=params, data=config, **self.opts)

    @raise_for_status_verbose
    def stack_delete(self, uid):
        return requests.delete(f"{self.api}/stacks/{uid}", **self.opts)

    @raise_for_status_verbose
    def _endpoint_list_request(self):
        return requests.get(f"{self.api}/endpoint_groups", **self.opts)

    def endpoint_list(self):
        return self._endpoint_list_request().json()


# Parser
parser = argparse.ArgumentParser(description="Deploy stack on Portainer")
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
