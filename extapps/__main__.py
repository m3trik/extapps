# !/usr/bin/python
# coding=utf-8
"""Run extapps as a program: ``python -m extapps [panel]``, or the ``extapps`` command.

No argument opens a browser listing every panel; a panel's name (an entry-point
name in ``pyproject.toml``: ``compositor``, ``metashape_workflow``, ...) opens
that panel alone; ``--shortcut desktop`` / ``--shortcut start_menu`` writes a
launcher. The program is uitk's :class:`ExternalAppHub`: this module only
declares extapps' name, icon and taskbar identity. As ``HUB`` it is also how a
host's UI Browser (Maya, Blender) finds extapps to offer a desktop shortcut on
each panel's row.
"""

import os

from uitk import ExternalAppHub

HUB = ExternalAppHub(
    "extapps",
    title="extapps",
    icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "extapps.svg"),
    app_id="m3trik.extapps",
)

if __name__ == "__main__":
    raise SystemExit(HUB.run())
