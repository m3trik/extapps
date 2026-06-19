# !/usr/bin/python
# coding=utf-8
"""Unity Studio — launch the Unity Editor and manage projects.

A standalone Switchboard panel over the ``unitytk`` launcher engine
(:class:`unitytk.UnityLauncher` / :class:`unitytk.UnityFinder`): list the installed
Unity Editors, pick (or create) a project, and launch the editor -- no DCC required.
The Maya/Blender -> Unity asset hand-off lives separately in each DCC's
``unity_bridge`` (the bridge reads the live selection; this launcher does not).
"""
from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "extapps.unity_studio"


DEFAULT_INCLUDE = {
    "launcher": ["UnityStudioUI"],
    "slots": ["UnityStudioSlots"],
}


bootstrap_package(globals(), include=DEFAULT_INCLUDE)


__all__ = [
    "UnityStudioUI",
    "UnityStudioSlots",
]
