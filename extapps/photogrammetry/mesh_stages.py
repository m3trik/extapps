# !/usr/bin/python
# coding=utf-8
"""Shared, SDK-agnostic mesh post-processing stages (PyMeshLab-backed).

``measure_mesh`` (QC metrics + gate), ``refine_mesh`` (isotropic remesh +
curvature-weighted decimation with before/after/deviation QC),
``bake_vertex_color`` (vertex color → texture) and the legacy
``clean_mesh_advanced`` repair pass are identical for RealityCapture and
Metashape — they operate on the *exported mesh file*, never the engine
SDK, calling :class:`pythontk.MeshOps` plus the engine's QC log. One
mixin both engines inherit, the :class:`PrepStagesMixin` pattern.

Because these are file-level stages, they deliberately do **not** gate on
``mock_mode`` the way SDK stages do: a mock-constructed workflow (the
``--post-only`` venv pass runs exactly that) still does real work when
the exported file exists. ``mock_mode`` only softens the *missing-input*
case so mock pipeline runs stay quiet.

Host requirements: ``self.qc`` (a ``pythontk.QcLog``), ``self.project_path``
(str), ``self.name`` (str), and ``self._notify(stage, fraction)``.
Optional: ``self.gate`` (a ``pythontk.QcGate`` — the ``"mesh"`` gate is
checked when present) and ``self.mock_mode``.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple


class MeshStagesMixin:
    """Measure / refine / bake / repair stages shared by both photogrammetry engines."""

    # ------------------------------------------------------------ plumbing
    def _default_model_path(self) -> str:
        """The conventional export target: ``<project>/<name>.obj``."""
        return os.path.join(self.project_path, f"{self.name}.obj")

    def _resolve_mesh_ops(self, st: Dict[str, Any]):
        """``pythontk.MeshOps`` when usable, else ``None`` with the QC stage
        marked ``fallback`` — a missing optional dep is a skip, never a
        ``[mock]`` and never an exception."""
        try:
            from pythontk import MeshOps
        except ImportError:
            self.qc.warn("MeshOps not importable (pythontk missing)")
            st["fallback"] = "pythontk_missing"
            return None
        if not MeshOps.available():
            self.qc.warn(
                "pymeshlab not installed - mesh stage skipped. "
                "Install with: pip install extapps[mesh]"
            )
            print("pymeshlab not installed; mesh stage skipped.")
            st["fallback"] = "pymeshlab_missing"
            return None
        return MeshOps

    def _mesh_input(self, st: Dict[str, Any], stage: str, path: str) -> Optional[str]:
        """Existing input path, else ``None`` — quiet ``[mock]`` in mock runs
        (no export exists there by design), a QC warning otherwise."""
        if path and os.path.isfile(path):
            return path
        if getattr(self, "mock_mode", False):
            print(f"[mock] {stage}('{path}')")
            st["fallback"] = "mock_no_input"
        else:
            self.qc.warn(f"{stage}: mesh input not found: {path}")
            st["fallback"] = "input_missing"
        return None

    def _check_mesh_gate(self, metrics: Optional[Dict[str, Any]]) -> None:
        """Evaluate the ``"mesh"`` gate when the host carries one. Callers
        pass the *final* metrics they produced; the last stage to run owns
        the recorded verdict (``qc.data["gates"]["mesh"]``)."""
        gate = getattr(self, "gate", None)
        if gate is not None and metrics:
            gate.check("mesh", metrics)

    # ------------------------------------------------------------ stages
    def measure_mesh(self, model_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """QC metrics for the exported mesh file, evaluated against the
        ``"mesh"`` gate. Returns the metrics dict, or ``None`` when skipped.

        The producer-agnostic replacement for SDK-side ``_mesh_metrics``:
        it reads the exported *file*, so the same gate covers a Metashape
        export, a RealityScan export, or anything else that lands an OBJ.
        """
        self._notify("measure_mesh", 0.0)
        metrics: Optional[Dict[str, Any]] = None
        with self.qc.stage("mesh_measure") as st:
            model_path = model_path or self._default_model_path()
            st["input"] = model_path
            ops = self._resolve_mesh_ops(st)
            if ops is None:
                return None
            src = self._mesh_input(st, "measure_mesh", model_path)
            if src is None:
                return None
            metrics = ops.measure(src)
            st.update(metrics)
            print(
                f"Mesh measured: {metrics['faces']} faces, "
                f"{metrics['components']} components, "
                f"{metrics['non_two_manifold_edges']} non-manifold edges."
            )
        self._check_mesh_gate(metrics)
        return metrics

    def refine_mesh(
        self,
        model_path: Optional[str] = None,
        output_path: Optional[str] = None,
        remesh_target_pct: float = 0.0,
        decimate_target_faces: int = 0,
        curvature_weighted: bool = True,
        compare_deviation: bool = True,
    ) -> Optional[str]:
        """Isotropic remesh and/or curvature-weighted decimation on the
        exported mesh, with before/after metrics and Hausdorff deviation in
        the QC stage. Returns the refined mesh path, or ``None`` when skipped.

        Parameters:
            model_path: Source mesh (defaults to ``<project>/<name>.obj``).
            output_path: Destination (defaults to ``<stem>_refined<ext>``).
            remesh_target_pct: Isotropic remesh target edge length as % of
                the bbox diagonal — the evenness pass scans need *before*
                collapse. 0 = skip remeshing.
            decimate_target_faces: Quadric-collapse face target. 0 = skip
                decimation.
            curvature_weighted: Spend the decimation budget adaptively on
                high-curvature areas (Decimation-Master-style).
            compare_deviation: Record Hausdorff deviation vs the source
                (``hausdorff_peak_pct`` feeds the ``"mesh"`` gate).
        """
        self._notify("refine_mesh", 0.0)
        after: Optional[Dict[str, Any]] = None
        out: Optional[str] = None
        with self.qc.stage("mesh_refine") as st:
            model_path = model_path or self._default_model_path()
            st["input"] = model_path
            st["remesh_target_pct"] = remesh_target_pct
            st["decimate_target_faces"] = decimate_target_faces
            st["curvature_weighted"] = curvature_weighted
            if remesh_target_pct <= 0 and decimate_target_faces <= 0:
                st["fallback"] = "no_work_requested"
                return None
            ops = self._resolve_mesh_ops(st)
            if ops is None:
                return None
            src = self._mesh_input(st, "refine_mesh", model_path)
            if src is None:
                return None
            stem, in_ext = os.path.splitext(src)
            with ops.session(src) as s:
                # Measure inside the session: scan meshes are routinely
                # multi-GB, so a separate measure() would double the load cost.
                before = s.measure()
                st["before"] = before
                if remesh_target_pct > 0:
                    s.op("remesh_isotropic", targetlen=remesh_target_pct)
                if decimate_target_faces > 0:
                    if curvature_weighted:
                        s.op("curvature_scalar")
                    s.op(
                        "decimate_quadric",
                        targetfacenum=int(decimate_target_faces),
                        preserveboundary=True,
                        preservenormal=True,
                        qualityweight=curvature_weighted,
                        autoclean=True,
                    )
                out = s.save(output_path or f"{stem}_refined{in_ext}")
                after = s.measure()
            st["output"] = out
            if compare_deviation:
                deviation = ops.compare(out, src)
                st["deviation"] = deviation
                after = {**after, **deviation}
            # AFTER the merge: the gate grades `after` with the deviation
            # folded in, so recording it before would leave the sidecar
            # missing the very metric (hausdorff_peak_pct) the verdict used.
            st["after"] = after
            print(
                f"Mesh refined: {before['faces']} -> {after['faces']} faces"
                + (
                    f", deviation peak {after['hausdorff_peak_pct']:.3f}% of diag."
                    if compare_deviation and after.get("hausdorff_peak_pct") is not None
                    else "."
                )
            )
        self._check_mesh_gate(after)
        return out

    def bake_vertex_color(
        self,
        model_path: Optional[str] = None,
        output_path: Optional[str] = None,
        texture_size: int = 1024,
    ) -> Optional[Tuple[str, str]]:
        """Bake per-vertex color to a texture on auto-generated UVs
        (``pythontk.MeshOps.bake_vertex_color``). Returns
        ``(mesh_path, texture_path)``, or ``None`` when skipped — including
        when the mesh simply has no vertex color to bake."""
        self._notify("bake_vertex_color", 0.0)
        with self.qc.stage("mesh_bake") as st:
            model_path = model_path or self._default_model_path()
            st["input"] = model_path
            st["texture_size"] = texture_size
            ops = self._resolve_mesh_ops(st)
            if ops is None:
                return None
            src = self._mesh_input(st, "bake_vertex_color", model_path)
            if src is None:
                return None
            try:
                mesh_path, tex_path = ops.bake_vertex_color(
                    src, output_path=output_path, texture_size=texture_size
                )
            except ValueError as e:  # no vertex color — a skip, not a failure
                self.qc.warn(f"bake_vertex_color: {e}")
                st["fallback"] = "no_vertex_color"
                return None
            st["output"] = mesh_path
            st["texture"] = tex_path
            print(f"Vertex color baked: {mesh_path} + {tex_path}")
            return mesh_path, tex_path

    def run_mesh_stages(
        self,
        model_path: Optional[str] = None,
        remesh_target_pct: float = 0.0,
        decimate_target_faces: int = 0,
        bake_texture_size: int = 0,
    ) -> Optional[str]:
        """The file-level stages in pipeline order: repair → refine (when a
        remesh/decimate target is set) → measure + gate (otherwise) → bake
        (opt-in). The single composition both engines' ``run_combined``
        sequences and the Metashape ``--post-only`` pass share; returns the
        path of the furthest-derived mesh (or ``None`` when nothing ran)."""
        cleaned = self.clean_mesh_advanced(exported_model_path=model_path)
        target = cleaned or model_path
        if remesh_target_pct > 0 or decimate_target_faces > 0:
            refined = self.refine_mesh(
                model_path=target,
                remesh_target_pct=remesh_target_pct,
                decimate_target_faces=decimate_target_faces,
            )
            target = refined or target
        else:
            self.measure_mesh(model_path=target)  # gate the final mesh either way
        if bake_texture_size > 0:
            self.bake_vertex_color(model_path=target, texture_size=bake_texture_size)
        return target

    def clean_mesh_advanced(
        self,
        exported_model_path: Optional[str] = None,
        decimate_target_faces: int = 0,
    ) -> Optional[str]:
        """PyMeshLab repair pass on the exported mesh file (duplicate/close
        vertex weld, isolated-piece pruning, non-manifold repair, hole fill,
        optional decimation). Returns the cleaned mesh path, or ``None``
        when skipped."""
        self._notify("clean_mesh_advanced", 0.0)
        with self.qc.stage("clean_mesh_advanced") as st:
            exported_model_path = exported_model_path or self._default_model_path()
            st["input"] = exported_model_path
            st["decimate_target_faces"] = decimate_target_faces
            ops = self._resolve_mesh_ops(st)
            if ops is None:
                return None
            src = self._mesh_input(st, "clean_mesh_advanced", exported_model_path)
            if src is None:
                return None
            result = ops.clean(src, decimate_target_faces=decimate_target_faces)
            st["output"] = result
            print(f"Mesh cleaned (PyMeshLab): {result}")
            return result
