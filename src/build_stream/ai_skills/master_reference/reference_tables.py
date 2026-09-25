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

"""Row-shaped data models for the eight Appendix A master reference tables.

Every row across every table carries `support_status` (where applicable)
and a `Provenance` record, per FR-1.0 / NFR-1 (ER-BSM-001-nersc-ai-skills-
catalog-authoring). A row that cannot be resolved from any of the three
FR-1.0 sources (master catalogs, repository configuration, online sources)
is represented as an `IncompleteRow` instead of a fabricated value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SupportStatus(str, Enum):
    """Vocabulary shared by the Selection Catalogue and Supported Hardware tables."""

    SUPPORTED = "supported"
    PLANNED = "planned"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class Provenance:
    """Where a row's value came from and when it was captured (NFR-1)."""

    source: str
    captured_on: str

    def as_text(self) -> str:
        """Render as the single provenance cell used by every table."""
        return f"{self.source} (captured {self.captured_on})"


@dataclass(frozen=True)
class IncompleteRow:
    """A gap the creation process could not resolve from any source (NFR-2).

    Recorded instead of a fabricated value; blocks packaging until the gap
    is resolved or explicitly accepted (FR-1.0).
    """

    table: str
    identifier: str
    reason: str


@dataclass(frozen=True)
class SelectionRow:
    """A.1 Selection Catalogue: one row per selectable option per axis."""

    axis: str
    option: str
    support_status: SupportStatus
    provenance: Provenance
    notes: str = ""


@dataclass(frozen=True)
class NodeRoleRow:
    """A.2 Node-Role Table: one row per node role, keyed by stack."""

    stack: str
    role: str
    layer_name_pattern: str
    mandatory: bool
    gpu_capable: bool
    provenance: Provenance


@dataclass(frozen=True)
class FunctionalLayerCompositionRow:
    """A.3 Functional-Layer Composition Table: role -> referenced groups."""

    role: str
    group: str
    inclusion: str  # "always" | "conditional"
    governed_by: str
    provenance: Provenance


@dataclass(frozen=True)
class StackStorageCompatibilityRow:
    """A.4 Stack-Storage Compatibility Table."""

    storage_option: str
    valid_for_slurm: bool
    valid_for_service_k8s: bool
    mechanism: str
    default_for: str
    provenance: Provenance


@dataclass(frozen=True)
class PackageSourceDefaultRow:  # pylint: disable=too-many-instance-attributes
    """A.5 Package Source Defaults Table."""

    source_name: str
    source_kind: str
    os_version: str
    architecture: str
    default_url: str
    gpgkey: str
    required_by: str
    provenance: Provenance


@dataclass(frozen=True)
class PinnedVersionRow:
    """A.6 Pinned Version Table."""

    component: str
    pinned_version: str
    pin_location: str
    arch_variance: str
    provenance: Provenance


@dataclass(frozen=True)
class SupportedHardwareRow:
    """A.7 Supported Hardware Table."""

    category: str
    vendor_model: str
    detection_path: str
    catalog_effect: str
    support_status: SupportStatus
    provenance: Provenance


@dataclass(frozen=True)
class ConstraintRow:
    """A.8 Constraint and Co-Requisite Table."""

    constraint_id: str
    scope: str
    rule: str
    severity: str  # "blocking" | "warning"
    provenance: Provenance


@dataclass
class MasterReferenceContent:  # pylint: disable=too-many-instance-attributes
    """The fully assembled content model backing the eight Appendix A tables."""

    selection_catalogue: list[SelectionRow] = field(default_factory=list)
    node_roles: list[NodeRoleRow] = field(default_factory=list)
    functional_layer_composition: list[FunctionalLayerCompositionRow] = field(
        default_factory=list
    )
    stack_storage_compatibility: list[StackStorageCompatibilityRow] = field(
        default_factory=list
    )
    package_source_defaults: list[PackageSourceDefaultRow] = field(default_factory=list)
    pinned_versions: list[PinnedVersionRow] = field(default_factory=list)
    supported_hardware: list[SupportedHardwareRow] = field(default_factory=list)
    constraints: list[ConstraintRow] = field(default_factory=list)
    incomplete_rows: list[IncompleteRow] = field(default_factory=list)

    def is_packageable(self) -> bool:
        """A file with any incomplete row SHALL NOT be packaged (FR-1.0)."""
        return len(self.incomplete_rows) == 0

    def find_selection(self, axis: str, option: str) -> Optional[SelectionRow]:
        """Look up one Selection Catalogue row by axis and option (case-insensitive)."""
        axis_norm = axis.strip().lower()
        option_norm = option.strip().lower()
        for row in self.selection_catalogue:
            if row.axis.strip().lower() == axis_norm and row.option.strip().lower() == option_norm:
                return row
        return None

    def supported_alternatives(self, axis: str) -> list[str]:
        """List every `supported` option on the given axis, for gate refusals."""
        axis_norm = axis.strip().lower()
        return [
            row.option
            for row in self.selection_catalogue
            if row.axis.strip().lower() == axis_norm
            and row.support_status == SupportStatus.SUPPORTED
        ]
