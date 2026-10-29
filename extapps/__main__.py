# !/usr/bin/python
# coding=utf-8
"""Run the standalone panels as a program: ``python -m extapps [panel]``, or the ``extapps`` command.

Kept for compatibility. The panels are tentacle's since extapps 0.7.0 (its
program is ``python -m tentacle``), and launchers written before they moved run
this one: ``<python> -m extapps <panel>``. It is uitk's :class:`ExternalAppHub`
under extapps' name, icon and taskbar identity, naming tentacle (``tentacletk``)
as the panels' provider -- as data, never an import: it serves them from an
installed tentacle or a source checkout, and installs tentacletk on the first
panel asked for where it is missing. No argument opens a browser listing every panel; a panel's name
(``compositor``, ``metashape_workflow``, ...) opens that panel alone;
``--shortcut desktop`` / ``--shortcut start_menu`` writes a launcher.
"""

import os

from uitk import ExternalAppHub

HUB = ExternalAppHub(
    "extapps",
    title="extapps",
    icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "extapps.svg"),
    app_id="m3trik.extapps",
    # The panels moved to tentacle: (distribution, import name) of their provider.
    providers=[("tentacletk", "tentacle")],
)

if __name__ == "__main__":
    raise SystemExit(HUB.run())
