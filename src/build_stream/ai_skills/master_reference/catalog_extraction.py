# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Extraction from master catalogs (`src/main/samples/catalogs/**/*.json`).

Implements the first FR-1.0 creation-process input: "extract the shipped
selections, layer-to-group mappings, and pinned versions from the master
catalogs." Every row this module produces carries a `Provenance` pointing at
the exact catalog file(s) it was read from.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .reference_tables import (
    FunctionalLayerCompositionRow,
    NodeRoleRow,
    PinnedVersionRow,
    Provenance,
)

# Node roles are named `<role>_rhel_<os_version>_<architecture>`; "os" itself
# is not a role but the shared base layer every stack includes.
_LAYER_NAME_PATTERN = re.compile(
    r"^(?P<role>[a-z0-9_]+?)_rhel_(?P<os_version>[0-9_]+)_(?P<architecture>x86_64|aarch64)$"
)

# Packages without an explicit "version" field still carry one in their
# human-readable "name", e.g. "kubeadm-1.35.1" or "calico-v3.32.1" (rpm/manifest)
# or "cffi==1.17.1" (pip_module). This is the same value the id-based suffix
# (e.g. "kubeadm_1_35_1") encodes, but the hyphenated/pinned "name" field is
# unambiguous where the id is not (some ids embed multi-part component names
# before the version, e.g. "cri_o_1_35_1", "csi_powerscale_v2_17_0").
_TRAILING_VERSION = re.compile(r"[-_](?P<version>v?\d+(?:\.\d+){1,3})$")

# Node roles known to carry a GPU-capable driver group when selected (A.2);
# derived from the functional-layer composition itself
# (nvidia_stack_driver_groupv1 reference), not asserted independently.
_MANDATORY_ROLES = {
    "os",
    "slurm_control_node",
    "slurm_node",
    "service_kube_control_plane",
    "service_kube_node",
}


@dataclass(frozen=True)
class CatalogExtraction:
    """Everything this module derives from one directory of catalog samples."""

    node_roles: list[NodeRoleRow]
    functional_layer_composition: list[FunctionalLayerCompositionRow]
    pinned_versions: list[PinnedVersionRow]


def _iter_catalog_files(catalogs_dir: Path) -> Iterable[Path]:
    """Yield every catalog JSON file under `catalogs_dir`, sorted for determinism."""
    return sorted(catalogs_dir.glob("**/*.json"))


def _load_catalog(path: Path) -> dict:
    """Load one catalog JSON file."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _summarize_files(files: set[str]) -> str:
    """Condense a provenance file set into one readable citation.

    Full per-row file lists are unreadable once a role/group appears in a
    dozen catalog samples; cite the count and up to two examples instead.
    """
    ordered = sorted(files)
    if len(ordered) <= 2:
        return f"master catalogs: {', '.join(ordered)}"
    return f"master catalogs: {len(ordered)} files, e.g. {ordered[0]}, {ordered[1]}"


def _stack_for_role(role: str) -> str:
    """Map a role identifier to its owning stack (A.2)."""
    if role == "os":
        return "(any)"
    if role.startswith("service_kube"):
        return "service_k8s"
    return "slurm"


def _governing_selection(component: str) -> tuple[str, str]:
    """Classify a conditionally-included group by the selection that governs it (A.3)."""
    if "nvidia" in component:
        return "conditional", "gpu=NVIDIA"
    if "vast" in component:
        return "conditional", "storage=VAST"
    if "powerscale" in component:
        return "conditional", "storage=PowerScale"
    if "infiniband" in component:
        return "conditional", "network=IB"
    return "always", "-"


def _resolve_package_version(pkg: dict) -> Optional[str]:
    """Resolve a package's pinned version from its explicit field or its name."""
    name = pkg.get("name", "")
    version = pkg.get("version")
    if version is None and "==" in name:
        version = name.rsplit("==", 1)[1]
    if version is None:
        trailing = _TRAILING_VERSION.search(name)
        version = trailing.group("version") if trailing else None
    return version


def _accumulate_layers(catalog: dict, rel_path: str, node_roles: dict, composition: dict) -> None:
    """Fold one catalog's functional layers into the running node-role and
    functional-layer-composition accumulators."""
    for layer in catalog.get("functionallayer", []):
        match = _LAYER_NAME_PATTERN.match(layer["name"])
        if not match:
            continue
        role = match.group("role")
        stack = _stack_for_role(role)
        node_roles.setdefault((stack, role), set()).add(rel_path)

        for component in layer.get("components", []):
            inclusion, governed_by = _governing_selection(component)
            entry = composition.setdefault(
                (role, component),
                {"inclusion": inclusion, "governed_by": governed_by, "files": set()},
            )
            entry["files"].add(rel_path)


def _accumulate_packages(catalog: dict, rel_path: str, pinned: dict) -> None:
    """Fold one catalog's resolvable-version packages into the pinned-version accumulator."""
    for pkg_id, pkg in catalog.get("packages", {}).items():
        version = _resolve_package_version(pkg)
        if version is None:
            continue
        record = pinned.setdefault(pkg_id, {"version": version, "locations": set(), "files": set()})
        location = f"packages.{pkg_id} (packagetype={pkg.get('packagetype', 'unknown')})"
        record["locations"].add(location)
        record["files"].add(rel_path)


def extract_from_catalogs(catalogs_dir: Path) -> CatalogExtraction:
    """Extract Node-Role, Functional-Layer Composition, and Pinned Version rows.

    Args:
        catalogs_dir: Root directory holding one or more `<os_version>/*.json`
            master catalog samples (e.g. `src/main/samples/catalogs`).

    Returns:
        A `CatalogExtraction` with one deduplicated row set per table, each
        row's provenance naming every catalog file it was observed in.
    """
    node_roles: dict[tuple[str, str], set[str]] = {}
    composition: dict[tuple[str, str], dict] = {}
    pinned: dict[str, dict] = {}

    for catalog_path in _iter_catalog_files(catalogs_dir):
        catalog = _load_catalog(catalog_path)["catalog"]
        rel_path = str(catalog_path.relative_to(catalogs_dir.parent.parent.parent.parent))
        _accumulate_layers(catalog, rel_path, node_roles, composition)
        _accumulate_packages(catalog, rel_path, pinned)

    node_role_rows = [
        NodeRoleRow(
            stack=stack,
            role=role,
            layer_name_pattern="<role>_rhel_<os_version>_<architecture>",
            mandatory=role in _MANDATORY_ROLES,
            gpu_capable=any(
                "nvidia" in component
                for (r, component) in composition
                if r == role
            ),
            provenance=Provenance(
                source=_summarize_files(files),
                captured_on="__CAPTURE_DATE__",
            ),
        )
        for (stack, role), files in sorted(node_roles.items())
    ]

    composition_rows = [
        FunctionalLayerCompositionRow(
            role=role,
            group=component,
            inclusion=entry["inclusion"],
            governed_by=entry["governed_by"],
            provenance=Provenance(
                source=_summarize_files(entry["files"]),
                captured_on="__CAPTURE_DATE__",
            ),
        )
        for (role, component), entry in sorted(composition.items())
    ]

    pinned_rows = [
        PinnedVersionRow(
            component=component,
            pinned_version=record["version"],
            pin_location="; ".join(sorted(record["locations"])),
            arch_variance="see per-architecture catalog file list in provenance",
            provenance=Provenance(
                source=_summarize_files(record["files"]),
                captured_on="__CAPTURE_DATE__",
            ),
        )
        for component, record in sorted(pinned.items())
    ]

    return CatalogExtraction(
        node_roles=node_role_rows,
        functional_layer_composition=composition_rows,
        pinned_versions=pinned_rows,
    )


def architectures_shipped_for_stack(catalogs_dir: Path, stack_prefix: str) -> set[str]:
    """Return every architecture for which a catalog file name starts with `stack_prefix`.

    Used to derive stack/architecture support (e.g. Kubernetes ships only
    `service_k8s_x86_64.json`, never `service_k8s_aarch64.json`) directly
    from which catalog files exist, instead of asserting it independently.
    """
    architectures: set[str] = set()
    for catalog_path in _iter_catalog_files(catalogs_dir):
        name = catalog_path.stem
        if not name.startswith(stack_prefix):
            continue
        if "aarch64" in name:
            architectures.add("aarch64")
        if "x86_64" in name:
            architectures.add("x86_64")
    return architectures
