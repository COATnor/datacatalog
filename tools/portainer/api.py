"""API for Portainer"""

import requests

from helpers.requests import raise_for_status_verbose

import json


class PortainerManager:
    """Simple (and incomplete) Portainer API manager."""

    def __init__(self, server, username, password, **options):
        """Set API endpoint, credentials and options."""
        self.api = server+'/api'
        self.username = username
        self.password = password
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
        """Authenticate and retrieve a JSON Web Token."""
        token = self._token_request().json()['jwt']
        self.opts['headers']['Authorization'] = 'Bearer '+token
        return token

    @raise_for_status_verbose
    def _stack_list_request(self):
        return requests.get(self.api+'/stacks', **self.opts)

    def stack_list(self):
        """Get a list of the stacks."""
        return self._stack_list_request().json()

    @raise_for_status_verbose
    def stack_create(self, name, endpoint, stack, env):
        """Create a new stack."""
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
        """Update the configuration of a stack."""
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
        """Delete a stack."""
        return requests.delete(f"{self.api}/stacks/{uid}", **self.opts)

    @raise_for_status_verbose
    def _endpoint_list_request(self):
        return requests.get(f"{self.api}/endpoint_groups", **self.opts)

    def endpoint_list(self):
        """Get a list of the endpoints."""
        return self._endpoint_list_request().json()
