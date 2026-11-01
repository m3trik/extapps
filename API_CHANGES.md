# extapps — API Changes

_Diff vs the last release (origin/main @ 79b0294)._

## Moved out (4)

- `unity_workflow/_unity_panel.py::UnityPanelMixin` → `extapps.UnityWorkflowSlots` (from 0.8.0)
- `unity_workflow/_unity_panel.py::UnityPanelMixin.default_output_dir` → `extapps.UnityWorkflowSlots` (from 0.8.0)
- `unity_workflow/_unity_panel.py::UnityPanelMixin.list_template_modes` → `extapps.UnityWorkflowSlots` (from 0.8.0)
- `unity_workflow/_unity_panel.py::UnityPanelMixin.template_dir` → `extapps.UnityWorkflowSlots` (from 0.8.0)

## Added (10)

- `__init__.py::MOVED_NAMES(constant)`
- `marmoset_workflow/_marmoset_workflow.py::MarmosetWorkflow(class)`
- `substance_workflow/env_utils/painter_connection.py::PainterConnection.op_timeout() -> float`
- `unity_workflow/parameters.py::FILE_SOURCE(constant)`
- `unity_workflow/parameters.py::SCENE_SOURCE(constant)`
- `unity_workflow/parameters.py::SOURCE_LABELS(constant)`
- `unity_workflow/slots.py::UnityWorkflowSlots.default_output_dir(self) -> str`
- `unity_workflow/slots.py::UnityWorkflowSlots.engine(self)`
- `unity_workflow/slots.py::UnityWorkflowSlots.list_template_modes(self)`
- `unity_workflow/slots.py::UnityWorkflowSlots.template_dir(self) -> Path`

## Signature changed (1)

- `marmoset_workflow/slots.py::MarmosetWorkflowSlots.make_bridge`
  - was: `(self) -> MarmosetEngine`
  - now: `(self) -> MarmosetWorkflow`
