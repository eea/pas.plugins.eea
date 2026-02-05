"""Control panel."""

from datetime import datetime
from logging import getLogger
from operator import methodcaller

from z3c.form import button
from z3c.form import form
from zope.interface import Interface

from plone import api
from plone import schema
from plone.app.registry.browser import controlpanel
from plone.autoform.form import AutoExtensibleForm

from pas.plugins.eea.sync import SyncEntra

logger = getLogger(__name__)


class IUserSyncForm(Interface):
    """Sync form definition."""

    add_new_users = schema.Bool(
        title="Add new users",
        default=True,
        required=False,
    )
    remove_missing_users = schema.Bool(
        title="Remove deleted users",
        default=True,
        required=False,
    )
    update_user_data = schema.Bool(
        title="Update existing user data",
        default=True,
        required=False,
    )
    sync_groups = schema.Bool(
        title="Fetch groups",
        default=True,
        required=False,
    )
    sync_group_members = schema.Bool(
        title="Fetch group members (slow)",
        default=True,
        required=False,
    )


class UserSyncForm(AutoExtensibleForm, form.EditForm):
    """Sync form."""

    schema = IUserSyncForm
    ignoreContext = True

    label = "Sync users with Entra ID"

    @button.buttonAndHandler("Start sync")
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        count_users, count_groups, seconds, done = self.do_sync(data)
        self.status = (
            f"Synced {count_users} users and {count_groups}"
            f" groups in {seconds} seconds ({done})"
        )

    @button.buttonAndHandler("Cancel")
    def handleCancel(self, _action):
        """User cancelled. Redirect back to the front page."""
        nav_root_url = api.portal.get_navigation_root(self.context).absolute_url()
        url_control_panel = f"{nav_root_url}/@@overview-controlpanel"
        return self.request.response.redirect(url_control_panel)

    def do_sync(self, data):
        """Start the sync."""
        t0 = datetime.now()
        syncer = SyncEntra()

        options = [
            "add_new_users",
            "remove_missing_users",
            "update_user_data",
            "sync_groups",
            "sync_group_members",
        ]

        for option in options:
            if data.get(option):
                methodcaller(option)(syncer)

        # syncer.sync_all()
        seconds = (datetime.now() - t0).total_seconds()
        logger.info(
            "Synced %s users and %s groups in %s seconds.",
            syncer.count_users,
            syncer.count_groups,
            seconds,
        )

        return (
            syncer.count_users,
            syncer.count_groups,
            seconds,
            datetime.isoformat(datetime.now()),
        )


class UserSyncControlPanel(controlpanel.ControlPanelFormWrapper):
    """Control panel form wrapper."""

    form = UserSyncForm
