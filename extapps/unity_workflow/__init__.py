# !/usr/bin/python
# coding=utf-8
"""Copy a model file into a Unity project's Assets and optionally launch the Editor.

A standalone Switchboard :class:`uitk.bridge.BridgeSlotsBase` panel driven by a
picked **model file** (the file-input sibling of mayatk's / blendertk's
selection-driven ``unity_bridge``). It copies the file into a Unity project's
``Assets/`` via :class:`unitytk.FileToUnityBridge` and optionally launches the
chosen Editor; the project actions (set / open / create) live on the 'Unity
Project' field's option menu. Runs from any host that loads uitk; a host can
pre-fill the file through ``set_model_path``.
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
