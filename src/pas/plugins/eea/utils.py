from pas.plugins.authomatic.interfaces import DEFAULT_ID as DEFAULT_AUTHOMATIC_ID
from plone import api

from .interfaces import DEFAULT_ID


def get_plugin() -> 'pas.plugins.eea.plugin.EEAEntraPlugin':
    return api.portal.get().acl_users.get(DEFAULT_ID)


def get_authomatic_plugin() -> 'pas.plugins.authomatic.plugin.AuthomaticPlugin':
    return api.portal.get().acl_users.get(DEFAULT_AUTHOMATIC_ID)


def get_provider_name(cfg, default="microsoft"):
    for name, settings in cfg.items():
        if settings.get("class_") == "authomatic.providers.oauth2.MicrosoftOnline":
            return name
    return default
