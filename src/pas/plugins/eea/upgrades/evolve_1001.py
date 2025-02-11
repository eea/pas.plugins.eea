import logging

from BTrees.OOBTree import OOBTree  # noqa

from pas.plugins.eea.sync import SyncEntra
from pas.plugins.eea.utils import get_plugin

logger = logging.getLogger(__name__)


def run(_):
    plugin = get_plugin()

    # add missing _user_types
    if not hasattr(plugin, "_user_types"):
        plugin._user_types = OOBTree()
        logger.info("Added _user_types to eea_entra plugin.")

    new_ad_groups = OOBTree()
    for group_id, group_title in plugin._ad_groups.items():
        if isinstance(group_title, tuple):
            new_ad_groups[group_id] = group_title
        else:
            new_ad_groups[group_id] = (group_title, "")

    plugin._ad_groups = new_ad_groups
    plugin._p_changed = 1

    logger.info("Begin user update...")
    syncer = SyncEntra()
    syncer.update_user_data()
