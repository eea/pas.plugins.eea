from pas.plugins.authomatic.interfaces import DEFAULT_ID as DEFAULT_AUTHOMATIC_ID
from pas.plugins.authomatic.plugin import AuthomaticPlugin
from plone import api

from .interfaces import DEFAULT_ID
from .plugin import EEAEntraPlugin


def get_plugin() -> EEAEntraPlugin:
    return api.portal.get().acl_users.get(DEFAULT_ID)


def get_authomatic_plugin() -> AuthomaticPlugin:
    return api.portal.get().acl_users.get(DEFAULT_AUTHOMATIC_ID)


def get_provider_name(cfg, default="microsoft"):
    for name, settings in cfg.items():
        if settings.get("class_") == "authomatic.providers.oauth2.MicrosoftOnline":
            return name
    return default
