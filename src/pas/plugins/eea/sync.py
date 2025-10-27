
""" Handle synchronization. """

import logging
import uuid
from dataclasses import dataclass

from pas.plugins.authomatic.plugin import AuthomaticPlugin
from pas.plugins.authomatic.useridentities import UserIdentities
from pas.plugins.authomatic.useridentities import UserIdentity
from pas.plugins.authomatic.utils import authomatic_cfg

from BTrees.OOBTree import TreeSet  # noqa

from Products.PlonePAS.plugins.property import ZODBMutablePropertyProvider
from Products.PluggableAuthService.PluggableAuthService import (
    PluggableAuthService,
)
from Products.PluggableAuthService.UserPropertySheet import UserPropertySheet

from plone import api

from pas.plugins.eea import EEAEntraPlugin
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

    _cfg: dict = None

    _acl: PluggableAuthService = None

    _plugin_eea: EEAEntraPlugin = None
    _plugin_authomatic: AuthomaticPlugin = None
    _plugin_mutable_properties: ZODBMutablePropertyProvider = None

    _provider_name: str = None
    _qm: QueryEntra = None

    _new_users: set = None
    _new_groups: set = None

    count_users: int = 0
    count_groups: int = 0

    def __init__(self):
        self._acl = api.portal.get().acl_users
        self._plugin_eea = get_plugin()
        self._plugin_authomatic = get_authomatic_plugin()
        self._plugin_mutable_properties = self._acl.mutable_properties
        self._init_query_manager()
        self._new_users = set()
        self._new_groups = set()

    def _init_query_manager(self):
        settings = authomatic_cfg()
        provider_name = get_provider_name(settings)
        cfg = settings.get(provider_name, {}) if settings else {}
        query_config = QueryConfig(
            cfg["consumer_key"], cfg["consumer_secret"], cfg["domain"]
        )

        self._cfg = cfg
        self._provider_name = provider_name
        self._qm = QueryEntra(query_config)

    def _update_mutable_properties(self, plone_uuid, property_sheet):
        email = property_sheet.getProperty("email")
        if self._plugin_mutable_properties._storage.get(plone_uuid):
            user = self._acl._createUser(
                self._acl.plugins, plone_uuid, email or plone_uuid
            )
            self._plugin_mutable_properties.setPropertiesForUser(
                user, property_sheet
            )

    def get_plone_uuid(self, service_uuid):
        plone_key = (self._provider_name, service_uuid)
        return self._plugin_authomatic._userid_by_identityinfo.get(
            plone_key, None
        )

    def get_service_uuid(self, plone_uuid):
        storage = self._plugin_authomatic._userid_by_identityinfo.items()
        match = [
            service_uuid
            for (
                name,
                service_uuid,
            ), p_uuid in storage
            if p_uuid == plone_uuid and name == self._provider_name
        ]
        return match[0] if match else None

    def _get_user_email(self, user: ApiUser):
        user_email = user["mail"] or user["userPrincipalName"]

        if "#EXT#" in user_email:
            user_email = ""

        return user_email

    def _create_property_sheet(self, plone_uuid, user: ApiUser):
        pdata = {"id": plone_uuid}
        for akey, pkey in self._cfg.get("sync_propertymap", {}).items():
            if pkey and not pdata.get(pkey):
                pdata[pkey] = user.get(akey, "") or ""
        pdata["email"] = self._get_user_email(user)
        sheet = UserPropertySheet(**pdata)
        return sheet

    def remember_user(self, user: ApiUser):
        user_key = (self._provider_name, user["id"])
        plone_uuid = str(uuid.uuid4())

        uis = UserIdentities(plone_uuid)
        uis._identities[self._provider_name] = UserIdentity(
            MockAuthResult(self._provider_name, user)
        )
        uis._sheet = self._create_property_sheet(plone_uuid, user)
        self._plugin_authomatic._useridentities_by_userid[plone_uuid] = uis
        self._plugin_authomatic._userid_by_identityinfo[user_key] = plone_uuid
        self._plugin_eea._user_types[plone_uuid] = user["userType"]

        self.count_users += 1
        self._new_users.add(user["id"])
        logger.info("Added new user: %s (%s)", plone_uuid, user["displayName"])

    def add_new_users(self):
        properties = self._cfg.get("sync_propertymap", {}).keys()
        for user in self._qm.get_all_users(properties=properties):
            plone_uuid = self.get_plone_uuid(user["id"])
            if not plone_uuid:
                self.remember_user(user)

    def remove_missing_users(self):
        active_remote_uuids = {
            self.get_plone_uuid(user["id"])
            for user in self._qm.get_all_users(properties=["id"])
        }
        local_uuids = set(
            self._plugin_authomatic._useridentities_by_userid.keys()
        )
        to_delete = local_uuids.difference(active_remote_uuids)
        for plone_uuid in to_delete:
            service_uuid = self.get_service_uuid(plone_uuid)
            user_key = (self._provider_name, service_uuid)
            uis = self._plugin_authomatic._useridentities_by_userid[plone_uuid]
            user_props = uis._sheet
            user_fullname = (
                user_props.getProperty("fullname")
                if user_props
                else "User has no propertysheet."
            )
            del self._plugin_authomatic._useridentities_by_userid[plone_uuid]
            del self._plugin_authomatic._userid_by_identityinfo[user_key]
            logger.info("Removed user: %s (%s)", plone_uuid, user_fullname)
            self.count_users += 1

    def update_user_data(self):
        properties = self._cfg.get("sync_propertymap", {}).keys()
        for user in self._qm.get_all_users(properties=properties):
            if user["id"] in self._new_users:
                # Skip newly added users (they're already up to date).
                continue
            plone_uuid = self.get_plone_uuid(user["id"])
            if plone_uuid:
                uis = self._plugin_authomatic._useridentities_by_userid[
                    plone_uuid
                ]
                uis._sheet = self._create_property_sheet(plone_uuid, user)
                self._update_mutable_properties(plone_uuid, uis._sheet)
                self._plugin_eea._user_types[plone_uuid] = user["userType"]
                self.count_users += 1

    def sync_groups(self):
        self._plugin_eea._ad_groups.clear()
        for group in self._qm.get_all_groups():
            self._plugin_eea._ad_groups[group["id"]] = (
                group["displayName"],
                group["description"],
            )
            self.count_groups += 1

    def remember_user_group(self, plone_uuid, group_id):
        if not self._plugin_eea._ad_member_groups.get(plone_uuid):
            self._plugin_eea._ad_member_groups[plone_uuid] = TreeSet()
        self._plugin_eea._ad_member_groups[plone_uuid].add(group_id)

    def sync_group_members(self):
        group_id = None
        group_ids = self._plugin_eea._ad_groups.keys()

        # clear existing user to group mapping
        self._plugin_eea._ad_member_groups.clear()

        for item in self._qm.get_group_members_parallel(group_ids):
            if isinstance(item, str):
                group_id = item
                self._plugin_eea._ad_group_members[group_id] = TreeSet()
                if group_id not in self._new_groups:
                    self.count_groups += 1
            else:
                if item["@odata.type"] == "#microsoft.graph.user":
                    plone_uuid = self.get_plone_uuid(item["id"])
                    self._plugin_eea._ad_group_members[group_id].add(
                        plone_uuid
                    )
                    self.remember_user_group(plone_uuid, group_id)
                elif item["@odata.type"] == "#microsoft.graph.group":
                    self._plugin_eea._ad_group_members[group_id].add(
                        item["id"]
                    )
                    self.remember_user_group(item["id"], group_id)

    def sync_all(self):
        self.add_new_users()
        self.remove_missing_users()
        self.update_user_data()
        self.sync_groups()
        self.sync_group_members()
