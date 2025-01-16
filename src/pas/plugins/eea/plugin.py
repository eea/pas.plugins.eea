import logging
import uuid
from pathlib import Path
from time import time

import requests
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PlonePAS.interfaces.group import IGroupIntrospection
from Products.PlonePAS.interfaces.group import IGroupManagement
from Products.PlonePAS.plugins.autogroup import VirtualGroup
from Products.PluggableAuthService.UserPropertySheet import UserPropertySheet
from Products.PluggableAuthService.interfaces import plugins as pas_interfaces
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from pas.plugins.authomatic.useridentities import UserIdentities
from pas.plugins.authomatic.utils import authomatic_cfg
from plone.memoize import ram
from zope.interface import implementer

from pas.plugins.eea.utils import get_authomatic_plugin
from pas.plugins.eea.utils import get_provider_name

logging.basicConfig(level=logging.DEBUG)
reqlogger = logging.getLogger("urllib3")
reqlogger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
tpl_dir = Path(__file__).parent.resolve() / "browser"

_marker = {}

MS_TOKEN_CACHE: dict | None = None


def manage_addEEAEntraPlugin(context, id, title="", RESPONSE=None, **kw):
    """Create an instance of an EEA Plugin."""
    plugin = EEAEntraPlugin(id, title, **kw)
    context._setObject(plugin.getId(), plugin)
    if RESPONSE is not None:
        RESPONSE.redirect("manage_workspace")


manage_addEEAEntraPluginForm = PageTemplateFile(
    tpl_dir / "add_plugin.pt",
    globals(),
    __name__="addEEAEntraPlugin",
)


def _cachekey_query_api_endpoint(method, self, url, consistent=None,
                                 extra_headers=None):
    headers = tuple(extra_headers.items()) if extra_headers else None
    return time() // (60 * 60), url, consistent, headers


@implementer(
    pas_interfaces.IUserEnumerationPlugin,
    pas_interfaces.IGroupEnumerationPlugin,
    pas_interfaces.IGroupsPlugin,
    IGroupManagement,
    IGroupIntrospection,
)
class EEAEntraPlugin(BasePlugin):
    """EEA PAS Plugin"""

    security = ClassSecurityInfo()
    meta_type = "EEA Entra Plugin"
    manage_options = BasePlugin.manage_options

    # Tell PAS not to swallow our exceptions
    _dont_swallow_my_exceptions = True

    def __init__(self, id, title=None, **kw):
        self._setId(id)
        self.title = title
        self.plugin_caching = True

    @security.private
    def _getMSAccessToken(self):
        global MS_TOKEN_CACHE
        if MS_TOKEN_CACHE and MS_TOKEN_CACHE["expires"] > time():
            return MS_TOKEN_CACHE["access_token"]

        settings = authomatic_cfg()
        provider_name = get_provider_name(settings)
        cfg = settings.get(provider_name, {}) if settings else {}
        domain = cfg.get("domain")

        if domain:
            url = f"https://login.microsoftonline.com/{domain}/oauth2/v2.0/token"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            data = {
                "grant_type": "client_credentials",
                "client_id": cfg["consumer_key"],
                "client_secret": cfg["consumer_secret"],
                "scope": "https://graph.microsoft.com/.default",
            }

            # TODO: maybe do this with authomatic somehow? (perhaps extend the default plugin?)
            response = requests.post(url, headers=headers, data=data)
            token_data = response.json()

            # TODO: cache this and refresh when necessary
            MS_TOKEN_CACHE = {"expires": time() + token_data["expires_in"] - 60}
            MS_TOKEN_CACHE.update(token_data)
            return MS_TOKEN_CACHE["access_token"]

    @security.private
    @ram.cache(_cachekey_query_api_endpoint)
    def queryApiEndpoint(self, url, consistent=True, extra_headers=None):
        token = self._getMSAccessToken()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if not consistent:
            headers["ConsistencyLevel"] = "eventual"

        if extra_headers:
            headers.update(extra_headers)

        response = requests.get(url, headers=headers)
        return response

    def queryApiEndpointGetAll(self, url, *args, **kwargs):
        resp = self.queryApiEndpoint(url, *args, **kwargs)
        if resp.status_code == 200:
            data = resp.json()
            yield from data.get('value', [data])
            # next_url = data.get("@odata.nextLink")
            # if next_url:
            #     yield from self.queryApiEndpointGetAll(next_url, *args, **kwargs)

    @security.private
    def queryMSApiUsers(self, login=""):
        pluginid = self.getId()

        url = (
            f"https://graph.microsoft.com/v1.0/users/{login}"
            if login
            else "https://graph.microsoft.com/v1.0/users"
        )

        users = self.queryApiEndpointGetAll(url)

        return [
            {
                "login": user["displayName"],
                "id": user["id"],
                "pluginid": pluginid,
                "fullname": user["displayName"],
                "email": user.get("email", user["userPrincipalName"])
            }
            for user in users
        ]

    @security.private
    def queryMSApiUsersInconsistently(self, query="", properties=None):
        pluginid = self.getId()

        url = "https://graph.microsoft.com/v1.0/users"

        custom_query = ""

        if not properties and query:
            custom_query = f"displayName:{query}"

        if properties and properties.get("fullname"):
            custom_query = f"displayName:{properties.get('fullname')}"

        elif properties and properties.get("email"):
            custom_query = f"mail:{properties.get('email')}"

        if custom_query:
            url = f'{url}?$search="{custom_query}"'

        users = self.queryApiEndpointGetAll(url, consistent=False)

        return [
            {
                "login": user["displayName"],
                "id": user["id"],
                "pluginid": pluginid,
                "fullname": user["displayName"],
                "email": user.get("email", user["userPrincipalName"])
            }
            for user in users
        ]

    def rememberUsers(self, users):
        authomatic_plugin = get_authomatic_plugin()
        provider_name = get_provider_name(authomatic_cfg())
        known_identities = authomatic_plugin._userid_by_identityinfo

        for user in users:
            user_key = (provider_name, user["id"])

            if known_identities.get(user_key):
                continue

            userid = str(uuid.uuid4())
            useridentities = UserIdentities(userid)
            useridentities._sheet = UserPropertySheet(
                {"fullname": user["fullname"], "email": user["email"]})
            authomatic_plugin._useridentities_by_userid[userid] = useridentities
            authomatic_plugin._userid_by_identityinfo[user_key] = userid

        return users

    @security.private
    def queryMSApiUsersEndpoint(self, login="", exact=False, **properties):
        if exact:
            return self.queryMSApiUsers(login)
        else:
            return self.queryMSApiUsersInconsistently(login, properties)

    @security.private
    def enumerateUsers(
        self,
        id=None,
        login=None,
        exact_match=False,
        sort_by=None,
        max_results=None,
        **kw,
    ):
        if id and login and id != login:
            raise ValueError("plugin does not support id different from login")

        search_id = id or login

        if search_id and not isinstance(search_id, str):
            raise NotImplementedError("sequence is not supported.")

        return self.rememberUsers(
            self.queryMSApiUsersEndpoint(search_id, exact_match, **kw))

    @security.private
    def addGroup(self, *args, **kw):
        """noop"""
        pass

    @security.private
    def addPrincipalToGroup(self, *args, **kwargs):
        """noop"""
        pass

    @security.private
    def removeGroup(self, *args, **kwargs):
        """noop"""
        pass

    @security.private
    def removePrincipalFromGroup(self, *args, **kwargs):
        """noop"""
        pass

    @security.private
    def updateGroup(self, *args, **kw):
        """noop"""
        pass

    @security.private
    def setRolesForGroup(self, group_id, roles=()):
        rmanagers = self._getPlugins().listPlugins(
            pas_interfaces.IRoleAssignerPlugin)
        if not (rmanagers):
            raise NotImplementedError(
                "There is no plugin that can assign roles to groups"
            )
        for rid, rmanager in rmanagers:
            rmanager.assignRolesToPrincipal(roles, group_id)

    @security.private
    def getGroupById(self, group_id):
        groups = self.queryMSApiGroups(group_id)
        group = groups[0] if len(groups) == 1 else None
        if group:
            return VirtualGroup(
                group["id"],
                title=group["title"],
                description=group["title"],
            )

    @security.private
    def getGroupIds(self):
        return [group["id"] for group in self.queryMSApiGroups("")]

    @security.private
    def getGroupsForPrincipal(self, principal, *args, **kwargs):
        url = f"https://graph.microsoft.com/v1.0/users/{principal.getId()}/memberOf/microsoft.graph.group"
        groups = self.queryApiEndpointGetAll(url)
        return [group["id"] for group in groups]

    @security.private
    def getGroupMembers(self, group_id):
        url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members"
        users = self.queryApiEndpointGetAll(url)
        return [user["id"] for user in users]

    @security.private
    def queryMSApiGroups(self, group_id=""):
        pluginid = self.getId()

        url = (
            f"https://graph.microsoft.com/v1.0/groups/{group_id}"
            if group_id
            else "https://graph.microsoft.com/v1.0/groups"
        )

        groups = self.queryApiEndpointGetAll(url)
        return [
            {
                "title": group["displayName"],
                "id": group["id"],
                "groupid": group["id"],
                "pluginid": pluginid,
            }
            for group in groups
        ]

    @security.private
    def queryMSApiGroupsInconsistently(self, query="", properties=None):
        groups = []
        pluginid = self.getId()

        customQuery = ""

        if not properties and query:
            customQuery = f"displayName:{query}"

        if properties and properties.get("title"):
            customQuery = f"displayName:{properties.get('title')}"

        if customQuery:
            url = f'https://graph.microsoft.com/v1.0/groups?$search="{customQuery}"'
            groups = self.queryApiEndpointGetAll(url, consistent=False)

        return [
            {
                "title": group["displayName"],
                "id": group["id"],
                "groupid": group["id"],
                "pluginid": pluginid,
            }
            for group in groups
        ]

    @security.private
    def queryMSApiGroupsEndpoint(self, query="", exact=False, **properties):
        if exact or not query:
            return self.queryMSApiGroups(query)
        else:
            return self.queryMSApiGroupsInconsistently(query, properties)

    @security.private
    def enumerateGroups(
        self, id=None, exact_match=False, sort_by=None, max_results=None, **kw
    ):
        return self.queryMSApiGroupsEndpoint(id, exact_match, **kw)


InitializeClass(EEAEntraPlugin)
