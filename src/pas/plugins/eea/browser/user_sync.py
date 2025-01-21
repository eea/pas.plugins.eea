from datetime import datetime
from logging import getLogger

from z3c.form import button
from z3c.form import form
from zope.interface import Interface

from plone import api
from plone import schema
from plone.autoform.form import AutoExtensibleForm

from pas.plugins.eea.sync import SyncEntra

logger = getLogger(__name__)


class IUserSyncForm(Interface):
    start_sync = schema.Bool(title="Start sync?", default=False)


class UserSyncForm(AutoExtensibleForm, form.EditForm):
    schema = IUserSyncForm
    ignoreContext = True

    label = "Sync users with Entra ID"

    @button.buttonAndHandler("Ok")
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        t0 = datetime.now()
        count_users, count_groups, done = self.do_sync()
        seconds = (datetime.now() - t0).total_seconds()

        self.status = f"Synced {count_users} users and {count_groups} groups in {seconds} seconds ({done})"

    @button.buttonAndHandler("Cancel")
    def handleCancel(self, action):
        """User cancelled. Redirect back to the front page."""
        return self.request.response.redirect(api.portal.get().absolute_url())

    def do_sync(self):
        syncer = SyncEntra()
        syncer.sync_users()
        syncer.sync_groups()
        syncer.sync_group_members()

        return (
            syncer.count_users,
            syncer.count_groups,
            datetime.isoformat(datetime.now()),
        )
