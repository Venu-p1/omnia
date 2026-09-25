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

"""Extraction from Build Stream / Repo Manager repository configuration.

Implements the second FR-1.0 creation-process input: "extract repository and
registry source defaults from the buildstream repository configuration"
(`src/repo_manager/input/repo_manager_config.yml`). Also cross-references
`src/repo_manager/plugins/module_utils/input_validation/core/config.py`'s
`expected_versions` map, which is how the AMD/ROCm and BeeGFS version pins
in A.1/A.6 are known without an online query: those components have a
version pin here but no catalog group anywhere under
`src/main/samples/catalogs/**` (checked by the caller).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .reference_tables import PackageSourceDefaultRow, Provenance

# RHEL entitlement repos: URL is auto-populated from the subscription unless
# the customer is unsubscribed, in which case the operator must supply it.
_SUBSCRIPTION_REPOS = {"baseos", "appstream", "codeready-builder"}
# Repos pre-populated with an empty URL by design; the operator MUST supply one.
_OPERATOR_SUPPLIED_REPOS = {"slurm_custom", "ldms", "vast"}


@dataclass(frozen=True)
class RepoConfigExtraction:
    """Everything this module derives from `repo_manager_config.yml`."""

    package_source_defaults: list[PackageSourceDefaultRow]
    expected_versions: dict[str, str]


def _source_kind(repo_name: str, has_default_url: bool) -> str:
    """Classify one repository entry per the A.5 `source_kind` vocabulary."""
    if repo_name in _SUBSCRIPTION_REPOS:
        return "subscription_repo"
    if repo_name in _OPERATOR_SUPPLIED_REPOS:
        return "operator_supplied_repo"
    if has_default_url:
        return "default_repo"
    return "operator_supplied_repo"


def _rows_for_version_arch(
    version: str, arch: str, repos: dict, rel_path: str
) -> list[PackageSourceDefaultRow]:
    """Build one A.5 row per RPM repository entry for a given OS version/arch."""
    rows = []
    all_repos = dict(repos)
    all_repos.update(repos.get("additional_repos") or {})
    all_repos.update(repos.get("user_repos") or {})
    for repo_name, repo_cfg in all_repos.items():
        if repo_name in ("additional_repos", "user_repos") or not isinstance(repo_cfg, dict):
            continue
        default_url = repo_cfg.get("url") or ""
        rows.append(
            PackageSourceDefaultRow(
                source_name=repo_name,
                source_kind=_source_kind(repo_name, bool(default_url)),
                os_version=version,
                architecture=arch,
                default_url=default_url,
                gpgkey=repo_cfg.get("gpgkey") or "",
                required_by=f"packages referencing reponame={repo_name}",
                provenance=Provenance(source=rel_path, captured_on="__CAPTURE_DATE__"),
            )
        )
    return rows


def extract_from_repo_config(repo_config_path: Path, repo_root: Path) -> RepoConfigExtraction:
    """Extract A.5 Package Source Defaults rows and `expected_versions` pins.

    Args:
        repo_config_path: Path to `repo_manager_config.yml`.
        repo_root: Repository root, used to render provenance as a relative path.

    Returns:
        A `RepoConfigExtraction` with one row per configured RPM repository
        (subscription, default, operator-supplied) and any registries.
    """
    with repo_config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    rel_path = str(repo_config_path.relative_to(repo_root))
    rows: list[PackageSourceDefaultRow] = []
    for version, by_arch in (config.get("repositories") or {}).items():
        for arch, repos in by_arch.items():
            rows.extend(_rows_for_version_arch(version, arch, repos, rel_path))

    for registry_name, registry_cfg in (config.get("registries") or {}).items():
        rows.append(
            PackageSourceDefaultRow(
                source_name=registry_name,
                source_kind="registry",
                os_version="(any)",
                architecture="(any)",
                default_url=(registry_cfg or {}).get("base_url", ""),
                gpgkey="",
                required_by="packages referencing registry field",
                provenance=Provenance(source=rel_path, captured_on="__CAPTURE_DATE__"),
            )
        )

    expected_versions_path = (
        repo_root
        / "src"
        / "repo_manager"
        / "plugins"
        / "module_utils"
        / "input_validation"
        / "core"
        / "config.py"
    )
    expected_versions = _extract_expected_versions(expected_versions_path)

    return RepoConfigExtraction(package_source_defaults=rows, expected_versions=expected_versions)


def _extract_expected_versions(config_py_path: Path) -> dict[str, str]:
    """Parse the `expected_versions` dict literal out of Repo Manager's config.py.

    Avoids importing the module (which pulls in Ansible-only dependencies);
    a targeted regex over the literal is sufficient and keeps this build-time
    tool dependency-free.
    """
    text = config_py_path.read_text(encoding="utf-8")
    block_match = re.search(r"expected_versions\s*=\s*\{(?P<body>[^}]*)\}", text, re.DOTALL)
    if not block_match:
        return {}
    pair_pattern = re.compile(r'"(?P<key>[a-z0-9_]+)"\s*:\s*"(?P<value>[^"]+)"')
    body = block_match.group("body")
    return {m.group("key"): m.group("value") for m in pair_pattern.finditer(body)}
