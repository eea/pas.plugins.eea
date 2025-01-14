from plone import api

from .interfaces import DEFAULT_ID
from .plugin import EEAEntraPlugin


def get_plugin() -> EEAEntraPlugin:
    return api.portal.get().acl_users.get(DEFAULT_ID)
