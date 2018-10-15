"""Helper functions for requests."""

import requests


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
