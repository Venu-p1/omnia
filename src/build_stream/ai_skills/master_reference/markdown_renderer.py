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

"""Renders a `MasterReferenceContent` into the single Markdown deliverable.

Each of the eight Appendix A tables is rendered as one Markdown table, per
FR-1.0: "each table SHALL be represented as a Markdown table or as YAML
embedded in a fenced block."
"""

from __future__ import annotations

from .reference_tables import MasterReferenceContent


def _escape(value: object) -> str:
    """Escape a cell value so it cannot break a Markdown table row."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list[object]]) -> str:
    """Render one Markdown table from a header row and data rows."""
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_escape(cell) for cell in row) + " |")
    return "\n".join(lines)


def _bool(value: bool) -> str:
    return "yes" if value else "no"


def render(content: MasterReferenceContent, *, version: str, generated_on: str) -> str:
    """Render the full master reference file as one Markdown document.

    Args:
        content: The assembled table content.
        version: The deliverable version to record in the header.
        generated_on: ISO date the file was (re)generated.

    Returns:
        The complete Markdown document text.
    """
    sections = [
        "# Master Reference File",
        "",
        f"**Version:** {version}  ",
        f"**Generated:** {generated_on}  ",
        "**Generator:** `src/build_stream/ai_skills/master_reference/build_master_reference.py`  ",
        "**Consumers:** Catalog Generation, Catalog Editing, Analysis skills "
        "(read directly via model context; see A.1 for the shared "
        "`support_status` gate in `selection_gate.py`)",
        "",
        "This file is a development-time deliverable created and maintained by "
        "the Build Stream team as part of the build/release process for the "
        "AI-assisted catalog authoring skills (ER-BSM-001-nersc-ai-skills-"
        "catalog-authoring, FR-1.0). It is not generated at skill-invocation "
        "time by an operator. Master catalogs remain the authoritative source "
        "for the concrete package set of an already-shipped configuration.",
        "",
        "---",
        "",
        "## A.1 Selection Catalogue",
        "",
        "One row per selectable option across every decision axis.",
        "",
        _table(
            ["axis", "option", "support_status", "notes", "provenance"],
            [
                [
                    row.axis,
                    row.option,
                    row.support_status.value,
                    row.notes,
                    row.provenance.as_text(),
                ]
                for row in content.selection_catalogue
            ],
        ),
        "",
        "---",
        "",
        "## A.2 Node-Role Table",
        "",
        "One row per node role, keyed by stack.",
        "",
        _table(
            ["stack", "role", "layer_name_pattern", "mandatory", "gpu_capable", "provenance"],
            [
                [
                    row.stack,
                    row.role,
                    row.layer_name_pattern,
                    _bool(row.mandatory),
                    _bool(row.gpu_capable),
                    row.provenance.as_text(),
                ]
                for row in content.node_roles
            ],
        ),
        "",
        "---",
        "",
        "## A.3 Functional-Layer Composition Table",
        "",
        "Role -> the groups its functional layer references, and the "
        "selection that governs each conditional group.",
        "",
        _table(
            ["role", "group", "inclusion", "governed_by", "provenance"],
            [
                [row.role, row.group, row.inclusion, row.governed_by, row.provenance.as_text()]
                for row in content.functional_layer_composition
            ],
        ),
        "",
        "---",
        "",
        "## A.4 Stack-Storage Compatibility Table",
        "",
        _table(
            [
                "storage_option",
                "valid_for_slurm",
                "valid_for_service_k8s",
                "mechanism",
                "default_for",
                "provenance",
            ],
            [
                [
                    row.storage_option,
                    _bool(row.valid_for_slurm),
                    _bool(row.valid_for_service_k8s),
                    row.mechanism,
                    row.default_for,
                    row.provenance.as_text(),
                ]
                for row in content.stack_storage_compatibility
            ],
        ),
        "",
        "---",
        "",
        "## A.5 Package Source Defaults Table",
        "",
        "Per OS version and architecture, the repositories/registries a "
        "package source may reference.",
        "",
        _table(
            [
                "source_name",
                "source_kind",
                "os_version",
                "architecture",
                "default_url",
                "gpgkey",
                "required_by",
                "provenance",
            ],
            [
                [
                    row.source_name,
                    row.source_kind,
                    row.os_version,
                    row.architecture,
                    row.default_url or "(operator-supplied)",
                    row.gpgkey or "-",
                    row.required_by,
                    row.provenance.as_text(),
                ]
                for row in content.package_source_defaults
            ],
        ),
        "",
        "---",
        "",
        "## A.6 Pinned Version Table",
        "",
        _table(
            ["component", "pinned_version", "pin_location", "arch_variance", "provenance"],
            [
                [
                    row.component,
                    row.pinned_version,
                    row.pin_location,
                    row.arch_variance,
                    row.provenance.as_text(),
                ]
                for row in content.pinned_versions
            ],
        ),
        "",
        "---",
        "",
        "## A.7 Supported Hardware Table",
        "",
        _table(
            [
                "category",
                "vendor_model",
                "detection_path",
                "catalog_effect",
                "support_status",
                "provenance",
            ],
            [
                [
                    row.category,
                    row.vendor_model,
                    row.detection_path,
                    row.catalog_effect,
                    row.support_status.value,
                    row.provenance.as_text(),
                ]
                for row in content.supported_hardware
            ],
        ),
        "",
        "---",
        "",
        "## A.8 Constraint and Co-Requisite Table",
        "",
        _table(
            ["constraint_id", "scope", "rule", "severity", "provenance"],
            [
                [row.constraint_id, row.scope, row.rule, row.severity, row.provenance.as_text()]
                for row in content.constraints
            ],
        ),
        "",
    ]

    if content.incomplete_rows:
        sections += [
            "---",
            "",
            "## Incomplete Rows (blocks packaging per FR-1.0/NFR-2)",
            "",
            _table(
                ["table", "identifier", "reason"],
                [[row.table, row.identifier, row.reason] for row in content.incomplete_rows],
            ),
            "",
        ]

    return "\n".join(sections) + "\n"
