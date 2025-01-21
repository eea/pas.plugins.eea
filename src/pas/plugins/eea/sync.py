import logging
import uuid
from dataclasses import dataclass

from pas.plugins.authomatic.useridentities import UserIdentities
from pas.plugins.authomatic.useridentities import UserIdentity
from pas.plugins.authomatic.utils import authomatic_cfg

from BTrees.OOBTree import TreeSet  # noqa

from Products.PluggableAuthService.UserPropertySheet import UserPropertySheet

from pas.plugins.eea.query import ApiUser
from pas.plugins.eea.query import QueryConfig
from pas.plugins.eea.query import QueryEntra
from pas.plugins.eea.utils import get_authomatic_plugin
from pas.plugins.eea.utils import get_plugin
from pas.plugins.eea.utils import get_provider_name

logger = logging.getLogger(__name__)


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


class SyncEntra:

    _provider_name: str = None
    _qm: QueryEntra = None

    count_users: int = 0
    count_groups: int = 0

    def __init__(self):
        self._plugin_eea = get_plugin()
        self._plugin_authomatic = get_authomatic_plugin()
        self._init_query_manager()

    def _init_query_manager(self):
        settings = authomatic_cfg()
        provider_name = get_provider_name(settings)
        cfg = settings.get(provider_name, {}) if settings else {}
        query_config = QueryConfig(
            cfg["consumer_key"], cfg["consumer_secret"], cfg["domain"]
        )

        self._provider_name = provider_name
        self._qm = QueryEntra(query_config)

    def get_plone_uuid(self, service_uuid):
        plone_key = (self._provider_name, service_uuid)
        return self._plugin_authomatic._userid_by_identityinfo.get(
            plone_key, None
        )

    def get_service_uuid(self, plone_uuid):
        match = [
            service_uuid
            for (
                name,
                service_uuid,
            ), p_uuid in self._plugin_authomatic._userid_by_identityinfo.items()
            if p_uuid == plone_uuid and name == self._provider_name
        ]
        return match[0] if match else None

    def remember_user(self, user: ApiUser):
        user_key = (self._provider_name, user["id"])
        plone_uuid = str(uuid.uuid4())

        user_email = user["mail"] or user["userPrincipalName"]
        if "#EXT#" in user_email:
            user_email = ""

        uis = UserIdentities(plone_uuid)
        uis._identities[self._provider_name] = UserIdentity(
            MockAuthResult(self._provider_name, user)
        )
        uis._sheet = UserPropertySheet(
            id=plone_uuid,
            schema=None,
            **{"fullname": user["displayName"], "email": user_email},
        )
        self._plugin_authomatic._useridentities_by_userid[plone_uuid] = uis
        self._plugin_authomatic._userid_by_identityinfo[user_key] = plone_uuid

        self.count_users += 1
        logger.info("Added new user: %s (%s)", plone_uuid, user["displayName"])

    def sync_users(self):
        for user in self._qm.get_all_users():
            plone_uuid = self.get_plone_uuid(user["id"])
            if not plone_uuid:
                self.remember_user(user)

    def sync_groups(self):
        for group in self._qm.get_all_groups():
            self._plugin_eea._ad_groups[group["id"]] = group["displayName"]
            self.count_groups += 1

    def remember_user_group(self, plone_uuid, group_id):
        if not self._plugin_eea._ad_member_groups.get(plone_uuid):
            self._plugin_eea._ad_member_groups[plone_uuid] = TreeSet()
        self._plugin_eea._ad_member_groups[plone_uuid].add(group_id)

    def sync_group_members(self):
        for group_id in self._plugin_eea._ad_groups.keys():
            self._plugin_eea._ad_group_members[group_id] = TreeSet()
            for member in self._qm.get_group_members(group_id):
                if member["@odata.type"] == "#microsoft.graph.user":
                    plone_uuid = self.get_plone_uuid(member["id"])
                    self._plugin_eea._ad_group_members[group_id].add(
                        plone_uuid
                    )
                    self.remember_user_group(plone_uuid, group_id)
                elif member["@odata.type"] == "#microsoft.graph.group":
                    # TODO: remember groups as group members?
                    continue
