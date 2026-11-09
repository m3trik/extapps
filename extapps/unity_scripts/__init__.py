# !/usr/bin/python
# coding=utf-8
"""Run built-in and your own C# scripts in a Unity project from one panel.

The one Unity panel, a Switchboard :class:`uitk.bridge.ParamPanelSlots`: pick a
script (the built-ins: Send to Unity, Make Prefab, Reimport Folder; your own
in ``ptk.ScriptTemplate.user_dir("unity")``), set the rows it names, and Run.
A script that takes an asset is given the **model file**, copied into the
project's ``Assets/`` first, or, opened by a host (a DCC's menus) that
injects its Unity engine (``slots.engine``), the **current scene**, which the
host's Scene Exporter exports. The script runs in the Unity
editor that has the project open, through the connection installed in it
(:class:`UnityConnection`); the project actions live on the 'Unity Project'
field's option menu. A host can also pre-fill the file through
``set_model_path``.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.unity_scripts"


DEFAULT_INCLUDE = {
    "launcher": ["UnityScriptsUI"],
    "slots": ["UnityScriptsSlots"],
    "unity_connection": ["UnityConnection"],
    "unity_deliverer": ["UnityDeliverer"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = [
    "UnityScriptsUI",
    "UnityScriptsSlots",
    "UnityConnection",
    "UnityDeliverer",
]
