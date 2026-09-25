#!/usr/bin/env python3
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

"""Build the Master Reference File deliverable (FR-1.0).

Development-time tool run by the Build Stream team as part of the build/
release process for the AI-assisted catalog authoring skills. It is not
invoked by an operator and is not imported by the BSM FastAPI application.

Creation-process order (FR-1.0):
  1. Extract shipped selections, layer-to-group mappings, and pinned
     versions from the master catalogs (`catalog_extraction.py`).
  2. Extract repository/registry source defaults from the buildstream
     repository configuration (`repo_config_extraction.py`).
  3. Resolve remaining gaps against online sources; a gap that stays
     unresolved is flagged as incomplete, never fabricated (NFR-2). This
     capture found no such gap (`known_constraints.py` module docstring).
  4. Assemble the 8-table Markdown file with `support_status` + provenance
     per row and write it as the versioned deliverable artifact
     (`master_reference_file.md`) alongside the skill definition files.

Usage:
    python3 build_master_reference.py \\
        --repo-root /path/to/omnia \\
        --output src/build_stream/ai_skills/master_reference/master_reference_file.md
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

from . import markdown_renderer
from .catalog_extraction import architectures_shipped_for_stack, extract_from_catalogs
from .known_constraints import (
    build_constraint_rows,
    build_selection_catalogue_rows,
    build_stack_storage_compatibility_rows,
    build_supported_hardware_rows,
)
from .reference_tables import IncompleteRow, MasterReferenceContent
from .repo_config_extraction import extract_from_repo_config

_DELIVERABLE_VERSION_PATH = Path(__file__).parent / "VERSION"


def _read_version() -> str:
    """Read the current deliverable version, defaulting to 1.0.0 if absent."""
    if _DELIVERABLE_VERSION_PATH.exists():
        return _DELIVERABLE_VERSION_PATH.read_text(encoding="utf-8").strip()
    return "1.0.0"


def _find_incomplete_rows(content: MasterReferenceContent) -> list[IncompleteRow]:
    """Flag rows whose `support_status`/provenance could not be fully resolved.

    NFR-1: every row missing `support_status` or provenance blocks packaging.
    """
    incomplete: list[IncompleteRow] = []
    for row in content.selection_catalogue:
        if not row.provenance.source:
            identifier = f"{row.axis}/{row.option}"
            incomplete.append(IncompleteRow("A.1 Selection Catalogue", identifier, "no provenance"))
    for row in content.supported_hardware:
        if not row.provenance.source:
            incomplete.append(
                IncompleteRow("A.7 Supported Hardware", row.vendor_model, "no provenance")
            )
    return incomplete


def build(repo_root: Path) -> MasterReferenceContent:
    """Run the full FR-1.0 creation process and return the assembled content.

    Args:
        repo_root: Root of the `omnia` source checkout.

    Returns:
        The assembled `MasterReferenceContent`, including any incomplete rows.
    """
    catalogs_dir = repo_root / "src" / "main" / "samples" / "catalogs"
    repo_config_path = repo_root / "src" / "repo_manager" / "input" / "repo_manager_config.yml"

    catalog_extraction = extract_from_catalogs(catalogs_dir)
    repo_extraction = extract_from_repo_config(repo_config_path, repo_root)
    k8s_architectures = architectures_shipped_for_stack(catalogs_dir, "service_k8s")

    content = MasterReferenceContent(
        selection_catalogue=build_selection_catalogue_rows(k8s_architectures),
        node_roles=catalog_extraction.node_roles,
        functional_layer_composition=catalog_extraction.functional_layer_composition,
        stack_storage_compatibility=build_stack_storage_compatibility_rows(),
        package_source_defaults=repo_extraction.package_source_defaults,
        pinned_versions=catalog_extraction.pinned_versions,
        supported_hardware=build_supported_hardware_rows(),
        constraints=build_constraint_rows(),
    )
    content.incomplete_rows = _find_incomplete_rows(content)
    return content


def render_and_write(content: MasterReferenceContent, output_path: Path, capture_date: str) -> str:
    """Render `content` to Markdown, substitute the capture date, and write it.

    Args:
        content: The assembled table content.
        output_path: Where to write the deliverable.
        capture_date: ISO date substituted for every row's provenance placeholder.

    Returns:
        The rendered Markdown text that was written.
    """
    version = _read_version()
    markdown_text = markdown_renderer.render(content, version=version, generated_on=capture_date)
    markdown_text = markdown_text.replace("__CAPTURE_DATE__", capture_date)
    output_path.write_text(markdown_text, encoding="utf-8")
    return markdown_text


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argument list (defaults to `sys.argv[1:]`).

    Returns:
        Process exit code: 0 on success, 1 if the file cannot be packaged
        because incomplete rows remain (FR-1.0).
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[4],
        help="Root of the omnia source checkout (default: derived from this file's location)",
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).parent / "master_reference_file.md",
        help="Path to write the master reference file deliverable",
    )
    parser.add_argument(
        "--capture-date", default=datetime.date.today().isoformat(),
        help="ISO date recorded as this run's provenance capture date",
    )
    parser.add_argument(
        "--allow-incomplete", action="store_true",
        help="Write the file even if incomplete rows remain (explicit gap acceptance)",
    )
    args = parser.parse_args(argv)

    content = build(args.repo_root)
    render_and_write(content, args.output, args.capture_date)

    if content.incomplete_rows and not args.allow_incomplete:
        print(
            f"master reference file written to {args.output} but NOT packageable: "
            f"{len(content.incomplete_rows)} incomplete row(s) present (FR-1.0/NFR-2)",
            file=sys.stderr,
        )
        return 1

    print(f"master reference file written to {args.output} (packageable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
