# -*- coding: utf-8 -*-
# pylint: disable=too-many-ancestors

"""Module where all interfaces, events and exceptions live."""

from zope.publisher.interfaces.browser import IDefaultBrowserLayer

DEFAULT_ID = "eea_entra"


class IPasPluginsEeaLayer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""
