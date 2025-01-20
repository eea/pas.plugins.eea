import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from time import time

import requests
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from pas.plugins.authomatic.useridentities import UserIdentities
from pas.plugins.authomatic.useridentities import UserIdentity
from pas.plugins.authomatic.utils import authomatic_cfg

from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import TreeSet
from zope.interface import alsoProvides
from zope.interface import implementer

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PlonePAS.interfaces.group import IGroupIntrospection
from Products.PlonePAS.interfaces.group import IGroupManagement
from Products.PlonePAS.plugins.autogroup import VirtualGroup
from Products.PluggableAuthService.interfaces import plugins as pas_interfaces
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.UserPropertySheet import UserPropertySheet

from plone import api
from plone.memoize import ram
from plone.protect.interfaces import IDisableCSRFProtection

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


def _cachekey_query_api_endpoint(
    method, self, url, consistent=None, extra_headers=None, session=None
):
    headers = tuple(extra_headers.items()) if extra_headers else None
    return time() // (60 * 60), url, consistent, headers, bool(session)


@dataclass
class MockProvider:
    name: str


@dataclass
class MockUser:
    user: dict

    def to_dict(self):
        return self.user


class MockAuthResult:
    provider: MockProvider
    user: MockUser

    def __init__(self, provider: str, user: dict):
        self.provider = MockProvider(provider)
        self.user = MockUser(user)


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

    _ad_groups: dict | None = None
    _ad_group_members: dict | None = None

    # Tell PAS not to swallow our exceptions
    _dont_swallow_my_exceptions = True

    def __init__(self, id, title=None, **kw):
        self._setId(id)
        self.title = title
        self.plugin_caching = True
        self._ad_groups = OOBTree()
        self._ad_group_members = OOBTree()
        self._ad_member_groups = OOBTree()

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
            url = (
                f"https://login.microsoftonline.com/{domain}/oauth2/v2.0/token"
            )
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            data = {
                "grant_type": "client_credentials",
                "client_id": cfg["consumer_key"],
                "client_secret": cfg["consumer_secret"],
                "scope": "https://graph.microsoft.com/.default",
            }

            response = requests.post(url, headers=headers, data=data)
            token_data = response.json()

            MS_TOKEN_CACHE = {
                "expires": time() + token_data["expires_in"] - 60
            }
            MS_TOKEN_CACHE.update(token_data)
            return MS_TOKEN_CACHE["access_token"]

    @security.private
    @ram.cache(_cachekey_query_api_endpoint)
    def queryApiEndpoint(
        self,
        url,
        consistent=True,
        extra_headers=None,
        session: requests.Session = None,
    ):
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

        requester = session if session else requests
        response = requester.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()

    def queryApiEndpointGetAll(self, url, *args, **kwargs):
        data = self.queryApiEndpoint(url, *args, **kwargs)
        if data:
            yield from data.get("value", [data])
            next_url = data.get("@odata.nextLink")
            if next_url:
                yield from self.queryApiEndpointGetAll(
                    next_url, *args, **kwargs
                )

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
                "email": user.get("email", user["userPrincipalName"]),
            }
            for user in users
        ]

    @security.private
    def queryMSApiUsersInconsistently(
        self, query="", properties=None, session=None
    ):
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

        users = self.queryApiEndpointGetAll(
            url, consistent=False, session=session
        )

        return [
            {
                "login": user["displayName"],
                "id": user["id"],
                "pluginid": pluginid,
                "fullname": user["displayName"],
                "email": user.get("email", user["userPrincipalName"]),
            }
            for user in users
        ]

    def getServiceUuid(self, plone_uuid):
        authomatic_plugin = get_authomatic_plugin()
        provider_name = get_provider_name(authomatic_cfg())
        plone_uuid_to_provider_uuid = {
            v: provider_uuid
            for (
                name,
                provider_uuid,
            ), v in authomatic_plugin._userid_by_identityinfo.items()
            if name == provider_name
        }
        return plone_uuid_to_provider_uuid.get(plone_uuid, plone_uuid)

    def getPloneUuid(self, service_uuid):
        authomatic_plugin = get_authomatic_plugin()
        provider_name = get_provider_name(authomatic_cfg())
        for (
            name,
            provider_uuid,
        ), plone_uuid in authomatic_plugin._userid_by_identityinfo.items():
            if provider_uuid == service_uuid and name == provider_name:
                return plone_uuid
        return service_uuid

    def rememberUsers(self, users):
        alsoProvides(api.env.getRequest(), IDisableCSRFProtection)

        authomatic_plugin = get_authomatic_plugin()
        provider_name = get_provider_name(authomatic_cfg())
        known_identities = authomatic_plugin._userid_by_identityinfo

        for user in users:
            user_key = (provider_name, user["id"])
            plone_uuid = known_identities.get(user_key)

            if plone_uuid:
                # replace provider id with internal plone uuid
                user["id"] = plone_uuid
                continue

            userid = str(uuid.uuid4())
            useridentities = UserIdentities(userid)
            useridentities._identities[provider_name] = UserIdentity(
                MockAuthResult(provider_name, user)
            )
            useridentities._sheet = UserPropertySheet(
                id=userid,
                schema=None,
                **{"fullname": user["fullname"], "email": user["email"]},
            )
            authomatic_plugin._useridentities_by_userid[userid] = (
                useridentities
            )
            authomatic_plugin._userid_by_identityinfo[user_key] = userid
            # replace provider id with internal plone uuid
            user["id"] = userid
            logger.info("Added new user: %s (%s)", userid, user["fullname"])

        return users

    @security.private
    def usersFromAuthomaticPlugin(self, *_args, **_kw):
        result = []
        pluginid = self.getId()
        authomatic_plugin = get_authomatic_plugin()
        identities = authomatic_plugin._useridentities_by_userid.values()
        for identity in identities:
            userid = identity.userid
            result.append(
                {"id": userid, "login": userid, "pluginid": pluginid}
            )
        return result

    @security.private
    def queryMSApiUsersEndpoint(
        self, login="", exact=False, session=None, **properties
    ):
        if exact:
            return self.queryMSApiUsers(self.getServiceUuid(login))
        else:
            return self.queryMSApiUsersInconsistently(
                login, properties, sesion=session
            )

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

        result = []
        if search_id and exact_match:
            authomatic_plugin = get_authomatic_plugin()
            result = authomatic_plugin.enumerateUsers(
                id, login, exact_match, sort_by, max_results, **kw
            )

        elif not search_id:
            result = self.usersFromAuthomaticPlugin(sort_by, max_results, **kw)

        if not result:
            session = requests.Session()
            result = self.rememberUsers(
                self.queryMSApiUsersEndpoint(
                    search_id, exact_match, session=session, **kw
                )
            )

        return result

    @security.private
    def addGroup(self, *args, **kw):
        """Noop"""
        pass

    @security.private
    def addPrincipalToGroup(self, *args, **kwargs):
        """Noop"""
        pass

    @security.private
    def removeGroup(self, *args, **kwargs):
        """Noop"""
        pass

    @security.private
    def removePrincipalFromGroup(self, *args, **kwargs):
        """Noop"""
        pass

    @security.private
    def updateGroup(self, *args, **kw):
        """Noop"""
        pass

    @security.private
    def setRolesForGroup(self, group_id, roles=()):
        rmanagers = self._getPlugins().listPlugins(
            pas_interfaces.IRoleAssignerPlugin
        )
        if not (rmanagers):
            raise NotImplementedError(
                "There is no plugin that can assign roles to groups"
            )
        for rid, rmanager in rmanagers:
            rmanager.assignRolesToPrincipal(roles, group_id)

    @security.private
    def getGroupById(self, group_id):
        # groups = self.queryMSApiGroups(group_id)
        # group = groups[0] if len(groups) == 1 else None
        groups = self.savedGroups(group_id)
        group = groups[0] if len(groups) == 1 else None
        if group:
            return VirtualGroup(
                group["id"],
                title=group["title"],
                description=group["title"],
            )

    @security.private
    def getGroupIds(self):
        return [x for x in self._ad_groups.keys()]
        # return [group["id"] for group in self.queryMSApiGroups("")]

    @security.private
    def getGroupsForPrincipal(self, principal, *args, **kwargs):
        principal_id = principal.getId()
        service_id = self.getServiceUuid(principal_id) or principal_id

        result = self._ad_member_groups.get(service_id, [])

        if not result:
            alsoProvides(api.env.getRequest(), IDisableCSRFProtection)
            url = f"https://graph.microsoft.com/v1.0/users/{service_id}/memberOf/microsoft.graph.group"
            groups = self.queryApiEndpointGetAll(url)
            self._ad_member_groups[service_id] = TreeSet(
                [group["id"] for group in groups]
            )
            result = self._ad_member_groups[service_id]

        return [x for x in result]

    @security.private
    def getGroupMembers(self, group_id):
        result = self._ad_group_members.get(group_id, [])
        if not result:
            alsoProvides(api.env.getRequest(), IDisableCSRFProtection)
            url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members"
            users = self.queryApiEndpointGetAll(url)
            self._ad_group_members[group_id] = TreeSet(
                [self.getPloneUuid(user["id"]) for user in users]
            )
            result = self._ad_group_members[group_id]
        return [x for x in result]

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
    def savedGroups(self, query=None):
        pluginid = self.getId()

        result = []

        if query:
            group_id, group_title = self._ad_groups.get(query, (None, None))
            if group_id:
                result = [
                    {
                        "title": group_title,
                        "id": group_id,
                        "groupid": group_id,
                        "pluginid": pluginid,
                    }
                ]

        if not result:
            result = [
                {
                    "title": group_title,
                    "id": group_id,
                    "groupid": group_id,
                    "pluginid": pluginid,
                }
                for group_id, group_title in self._ad_groups.values()
            ]

        return result

    @security.private
    def rememberGroups(self, groups):
        alsoProvides(api.env.getRequest(), IDisableCSRFProtection)
        for group in groups:
            if group["id"] in self._ad_groups:
                continue
            self._ad_groups[group["id"]] = (group["id"], group["title"])
        return groups

    @security.private
    def enumerateGroups(
        self, id=None, exact_match=False, sort_by=None, max_results=None, **kw
    ):
        result = []
        if not id:
            result = self.savedGroups()

        elif id and exact_match:
            result = self.savedGroups(id)

        # if not result:
        #     result = self.rememberGroups(self.queryMSApiGroupsEndpoint(id, exact_match, **kw))

        return result


InitializeClass(EEAEntraPlugin)
