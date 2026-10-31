# !/usr/bin/python
# coding=utf-8
"""Copy a model into a Unity project's Assets and optionally launch the Editor.

The one Unity panel, a Switchboard :class:`uitk.bridge.ParamPanelSlots`: on its
own it copies a picked **model file** into a Unity project's ``Assets/`` via
:class:`unitytk.FileToUnityBridge`; opened by a host (tentacle's menus in Maya
and Blender) that injects its Unity engine (``slots.engine``), it also sends the
**current scene** -- the host exports the Scope and the panel delivers it. The
project actions (set / open / create) live on the 'Unity Project' field's
option menu. A host can also pre-fill the file through ``set_model_path``.
"""

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.unity_workflow"


DEFAULT_INCLUDE = {
    "launcher": ["UnityWorkflowUI"],
    "slots": ["UnityWorkflowSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = [
    "UnityWorkflowUI",
    "UnityWorkflowSlots",
]
