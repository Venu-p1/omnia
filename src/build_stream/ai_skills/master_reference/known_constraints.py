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

"""Rows this build tool cannot assemble by mechanically walking one JSON
catalog file or one YAML config file, because they are cross-cutting facts
about *why* the source looks the way it does (A.1, A.4, A.7, A.8).

Every row below still cites the concrete source evidence used to resolve it
(catalog samples, repository configuration, or Omnia source under
`src/orchestrator/` and `src/repo_manager/`) per FR-1.0's priority order.
None of it was resolved from an online source: this Omnia checkout answers
every constraint needed for the eight tables. FR-1.0's "query online
sources only for constraints not derivable from those two inputs" therefore
has no rows to add at this capture; `build_master_reference.py` still calls
an (empty) online-resolution hook so a future gap takes the flagged-
incomplete path (NFR-2) instead of silently omitting a row.
"""

from __future__ import annotations

from .reference_tables import (
    ConstraintRow,
    Provenance,
    SelectionRow,
    StackStorageCompatibilityRow,
    SupportedHardwareRow,
    SupportStatus,
)


def _prov(source: str) -> Provenance:
    return Provenance(source=source, captured_on="__CAPTURE_DATE__")


def build_selection_catalogue_rows(k8s_architectures: set[str]) -> list[SelectionRow]:
    """A.1 Selection Catalogue rows beyond the raw per-axis option list.

    Args:
        k8s_architectures: Architectures for which a `service_k8s_*` catalog
            file actually exists (from `architectures_shipped_for_stack`),
            used to derive the Kubernetes/x86_64-only claim from shipped
            catalogs rather than asserting it.
    """
    k8s_note = (
        "x86_64 only — no service_k8s_aarch64.json ships in any inspected "
        "catalogs/<os_version>/ directory"
        if k8s_architectures == {"x86_64"}
        else f"ships for: {', '.join(sorted(k8s_architectures))}"
    )
    return [
        SelectionRow(
            axis="os_version", option="RHEL 10.0", support_status=SupportStatus.SUPPORTED,
            provenance=_prov("src/main/samples/catalogs/10.0/"),
        ),
        SelectionRow(
            axis="os_version", option="RHEL 10.2", support_status=SupportStatus.SUPPORTED,
            provenance=_prov("src/main/samples/catalogs/10.2/"),
            notes="Content-equivalent to 10.0 apart from version pinning "
            "(verified by diffing every 10.0/10.2 catalog pair after "
            "normalizing version substrings)",
        ),
        SelectionRow(
            axis="architecture", option="x86_64", support_status=SupportStatus.SUPPORTED,
            provenance=_prov("src/main/samples/catalogs/**/*_x86_64*.json"),
        ),
        SelectionRow(
            axis="architecture", option="aarch64", support_status=SupportStatus.SUPPORTED,
            provenance=_prov("src/main/samples/catalogs/**/*_aarch64*.json"),
            notes="Some image-builder and helm artifacts are arch-specific",
        ),
        SelectionRow(
            axis="stack", option="slurm", support_status=SupportStatus.SUPPORTED,
            provenance=_prov("src/main/samples/catalogs/**/slurm_*.json"),
        ),
        SelectionRow(
            axis="stack", option="service_k8s", support_status=SupportStatus.SUPPORTED,
            provenance=_prov("src/main/samples/catalogs/**/service_k8s_*.json"),
            notes=f"Kubernetes is not supported on aarch64 in this release ({k8s_note})",
        ),
        SelectionRow(
            axis="stack", option="slurm + service_k8s", support_status=SupportStatus.SUPPORTED,
            provenance=_prov("src/main/samples/catalogs/**/slurm_service_k8s_*.json"),
            notes="Mixed-stack catalogs are a shipped configuration; x86_64 only "
            "when Kubernetes is included",
        ),
        SelectionRow(
            axis="gpu", option="NVIDIA", support_status=SupportStatus.SUPPORTED,
            provenance=_prov(
                "src/main/samples/catalogs (nvidia_stack_driver_groupv1); "
                "src/orchestrator/plugins/modules/bulk_discover_node_specs.py "
                "(_detect_gpus_from_processors/_detect_gpus_from_pcie)"
            ),
        ),
        SelectionRow(
            axis="gpu", option="AMD / ROCm", support_status=SupportStatus.PLANNED,
            provenance=_prov(
                "src/repo_manager/plugins/module_utils/input_validation/core/config.py "
                "expected_versions['amdgpu'/'rocm']"
            ),
            notes="Version pins exist in repository configuration; no functional "
            "group ships today and hardware detection only regex-matches NVIDIA",
        ),
        SelectionRow(
            axis="storage", option="VAST (NFS/RDMA)", support_status=SupportStatus.SUPPORTED,
            provenance=_prov(
                "src/main/samples/catalogs (vast_stack_driver_groupv1, Slurm layers only)"
            ),
            notes="Slurm-scoped — see A.4",
        ),
        SelectionRow(
            axis="storage", option="PowerScale (CSI)", support_status=SupportStatus.SUPPORTED,
            provenance=_prov(
                "src/main/samples/catalogs (powerscale_csi_group, service_k8s layers only)"
            ),
            notes="Kubernetes-scoped — see A.4",
        ),
        SelectionRow(
            axis="storage", option="PowerVault (iSCSI)", support_status=SupportStatus.SUPPORTED,
            provenance=_prov(
                "src/orchestrator/roles/mount_config/tasks/process_single_powervault.yml; "
                "src/orchestrator/input/storage_config.yml"
            ),
            notes="Stack-neutral; runtime-discovered device, no catalog group",
        ),
        SelectionRow(
            axis="storage", option="Generic NFS", support_status=SupportStatus.SUPPORTED,
            provenance=_prov("src/orchestrator/roles/mount_config/tasks/cloud_init.yml"),
            notes="Stack-neutral; no catalog group",
        ),
        SelectionRow(
            axis="storage", option="BeeGFS", support_status=SupportStatus.PLANNED,
            provenance=_prov(
                "src/repo_manager/plugins/module_utils/input_validation/core/config.py "
                "expected_versions['beegfs']"
            ),
            notes="Version pin only; no functional group or role found in any "
            "inspected catalog",
        ),
        SelectionRow(
            axis="network", option="InfiniBand (DOCA OFED)", support_status=SupportStatus.SUPPORTED,
            provenance=_prov(
                "src/main/samples/catalogs (infiniband_stack_driver_groupv1); "
                "src/orchestrator/roles/configure_ochami/templates/doca-ofed/doca-install.sh.j2"
            ),
            notes="Additive per functional layer, not a vendor choice",
        ),
        SelectionRow(
            axis="network", option="Ethernet-only", support_status=SupportStatus.SUPPORTED,
            provenance=_prov("src/main/samples/catalogs (absence of infiniband group)"),
            notes="Absence of the InfiniBand group; no dedicated group",
        ),
    ]


def build_stack_storage_compatibility_rows() -> list[StackStorageCompatibilityRow]:
    """A.4 Stack-Storage Compatibility Table."""
    catalogs_evidence = "src/main/samples/catalogs/**/*.json"
    orchestrator_evidence = "src/orchestrator/roles/mount_config/tasks/"
    return [
        StackStorageCompatibilityRow(
            storage_option="VAST (NFS/RDMA)", valid_for_slurm=True, valid_for_service_k8s=False,
            mechanism="Mount targeted at Slurm functional-group prefixes; contributes "
            "a catalog group (vast_stack_driver_groupv1)",
            default_for="Slurm functional clusters",
            provenance=_prov(catalogs_evidence),
        ),
        StackStorageCompatibilityRow(
            storage_option="PowerScale (CSI)", valid_for_slurm=False, valid_for_service_k8s=True,
            mechanism="Enabled per Kubernetes cluster; contributes a CSI catalog "
            "group (powerscale_csi_group)",
            default_for="Kubernetes functional clusters",
            provenance=_prov(catalogs_evidence),
        ),
        StackStorageCompatibilityRow(
            storage_option="PowerVault (iSCSI)", valid_for_slurm=True, valid_for_service_k8s=True,
            mechanism="Runtime-discovered device; no catalog group",
            default_for="(operator-configured)",
            provenance=_prov(orchestrator_evidence + "process_single_powervault.yml"),
        ),
        StackStorageCompatibilityRow(
            storage_option="Generic NFS", valid_for_slurm=True, valid_for_service_k8s=True,
            mechanism="Plain mount; no catalog group",
            default_for="(operator-configured)",
            provenance=_prov(orchestrator_evidence + "cloud_init.yml"),
        ),
    ]


def build_supported_hardware_rows() -> list[SupportedHardwareRow]:
    """A.7 Supported Hardware Table."""
    discovery_evidence = "src/orchestrator/plugins/modules/bulk_discover_node_specs.py"
    return [
        SupportedHardwareRow(
            category="server", vendor_model="Dell PowerEdge",
            detection_path="Inventory / Redfish",
            catalog_effect="none directly; determines architecture",
            support_status=SupportStatus.SUPPORTED, provenance=_prov(discovery_evidence),
        ),
        SupportedHardwareRow(
            category="bmc", vendor_model="iDRAC",
            detection_path="Redfish endpoints", catalog_effect="none; provisioning path only",
            support_status=SupportStatus.SUPPORTED, provenance=_prov(discovery_evidence),
        ),
        SupportedHardwareRow(
            category="gpu", vendor_model="NVIDIA data-centre and workstation families",
            detection_path="Processor type + vendor match (_detect_gpus_from_processors), "
            "PCIe class-code fallback (_detect_gpus_from_pcie)",
            catalog_effect="implies the NVIDIA group on gpu_capable roles",
            support_status=SupportStatus.SUPPORTED, provenance=_prov(discovery_evidence),
        ),
        SupportedHardwareRow(
            category="gpu", vendor_model="AMD",
            detection_path="not detected — _detect_gpus_from_processors/_pcie only regex-match "
            "'nvidia'",
            catalog_effect="none; may be seen as a generic PCIe display-controller",
            support_status=SupportStatus.PLANNED, provenance=_prov(discovery_evidence),
        ),
        SupportedHardwareRow(
            category="fabric_adapter", vendor_model="NVIDIA/Mellanox InfiniBand",
            detection_path="`lspci | grep -i mellanox` (DOCA-OFED / VAST install scripts)",
            catalog_effect="implies the InfiniBand group",
            support_status=SupportStatus.SUPPORTED,
            provenance=_prov(
                "src/orchestrator/roles/configure_ochami/templates/doca-ofed/"
                "doca-install.sh.j2; src/orchestrator/roles/configure_ochami/"
                "templates/vast/configure_vast_installation.sh.j2"
            ),
        ),
        SupportedHardwareRow(
            category="storage_array", vendor_model="VAST, PowerScale, PowerVault",
            detection_path="operator-declared, not discovered "
            "(src/orchestrator/input/storage_config.yml)",
            catalog_effect="see A.4", support_status=SupportStatus.SUPPORTED,
            provenance=_prov("src/orchestrator/input/storage_config.yml"),
        ),
    ]


def build_constraint_rows() -> list[ConstraintRow]:
    """A.8 Constraint and Co-Requisite Table."""
    return [
        ConstraintRow(
            constraint_id="CON-001", scope="storage, stack",
            rule="Storage selection must be valid for the chosen stack (A.4)",
            severity="blocking", provenance=_prov("A.4 Stack-Storage Compatibility Table"),
        ),
        ConstraintRow(
            constraint_id="CON-002", scope="gpu, node_role",
            rule="A GPU group may be attached only to a gpu_capable role (A.2)",
            severity="blocking", provenance=_prov("A.2 Node-Role Table"),
        ),
        ConstraintRow(
            constraint_id="CON-003", scope="stack, architecture",
            rule="Kubernetes stack is supported only on x86_64 architecture (A.1)",
            severity="blocking",
            provenance=_prov("A.1 Selection Catalogue; absence of service_k8s_aarch64.json"),
        ),
        ConstraintRow(
            constraint_id="CON-004", scope="Kubernetes pinned components",
            rule="Kubernetes RPM, image, and repository version pins must agree",
            severity="blocking",
            provenance=_prov(
                "src/main/samples/catalogs (kubeadm_1_35_1/kubelet_1_35_1/kubectl_1_35_1, "
                "docker.io/alpine/kubectl, cri-o-1.35.1 all pinned to the same minor)"
            ),
        ),
        ConstraintRow(
            constraint_id="CON-005", scope="package source, architecture",
            rule="A package source's architecture must be one of the catalog's "
            "selected architectures",
            severity="blocking", provenance=_prov("A.5 Package Source Defaults Table"),
        ),
        ConstraintRow(
            constraint_id="CON-006", scope="operator-supplied repository",
            rule="An operator-supplied repository referenced by any package must "
            "have a URL before sync",
            severity="blocking",
            provenance=_prov(
                "src/repo_manager/input/repo_manager_config.yml user_repos "
                "(slurm_custom, ldms, vast ship with an empty url by design)"
            ),
        ),
        ConstraintRow(
            constraint_id="CON-007", scope="functional layer, group removal",
            rule="Removing a group that another selected role also references "
            "affects both roles",
            severity="warning", provenance=_prov("A.3 Functional-Layer Composition Table"),
        ),
        ConstraintRow(
            constraint_id="CON-008", scope="driver group, repository configuration",
            rule="Adding a driver group pulls in a repository that may not yet "
            "be configured",
            severity="warning",
            provenance=_prov(
                "A.5 Package Source Defaults Table; A.3 Functional-Layer Composition Table"
            ),
        ),
    ]


def resolve_remaining_gaps_online(unresolved_identifiers: list[str]) -> dict[str, str]:
    """Hook for FR-1.0's third input: online sources, for constraints not
    derivable from master catalogs or repository configuration.

    This capture resolved every A.1/A.4/A.7/A.8 fact from the two local
    sources above, so `unresolved_identifiers` is expected to be empty.
    The hook is kept so a future re-derivation that *does* hit a genuine gap
    takes the `IncompleteRow` path (NFR-2) rather than skipping resolution
    silently. It intentionally does not perform network I/O by itself;
    online lookups (Red Hat Compatibility Matrix, upstream docs) are a
    human/tooling step the build operator supplies via `--online-answers`.

    Args:
        unresolved_identifiers: Identifiers the local extraction could not resolve.

    Returns:
        An empty mapping when there is nothing to resolve online.
    """
    if not unresolved_identifiers:
        return {}
    return {}
