""" Sync users. """

import argparse
from datetime import datetime

import Zope2
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.users import system as system_user
from Testing.makerequest import makerequest
from Zope2.Startup.run import make_wsgi_app
from zope.component.hooks import setSite
from zope.globalrequest import setRequest

from pas.plugins.eea.sync import SyncEntra

parser = argparse.ArgumentParser(
    prog="EEAEntraSync",
    description="Sync users and groups from EEA Entra ID",
    epilog="Always runs a full sync.",
)

parser.add_argument(
    "--portal",
    dest="portal_id",
    required=True,
    help="Portal ID",
)

def run_standalone():
    parser.add_argument(
        "--zope-conf",
        dest="zope_conf",
        required=True,
        help="Path to zope.conf",
    )
    args = parser.parse_args()
    make_wsgi_app({}, args.zope_conf)
    app = Zope2.app()
    app = makerequest(app)
    app.REQUEST["PARENTS"] = [app]
    setRequest(app.REQUEST)
    newSecurityManager(None, system_user)
    run(app)


def run(app):
    args = parser.parse_args()
    portal = app[args.portal_id]
    setSite(portal)

    syncer = SyncEntra()

    print("Syncing users and groups...")
    t0 = datetime.now()
    syncer.sync_all()
    seconds = (datetime.now() - t0).total_seconds()
    print(f"...sync complete after {seconds} seconds.")


if __name__ == "__main__":
    run(Zope2.app())
