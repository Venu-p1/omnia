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

"""The shared Selection Catalogue `support_status` gate (FR-2 / AC-005).

Every catalog-authoring skill (Catalog Generation, Catalog Editing via the
Pre-Edit Gate, Analysis skills) calls `evaluate_selection` before emitting a
functional group or package set for an operator's requested selection.

Per the Story's resolved Open Question (see `spec.md` Section 8), a
consuming skill reads `master_reference_file.md` directly via model
context rather than calling a typed table-lookup function; this module is
the one piece of that flow that stays a deterministic function. It takes
the Selection Catalogue rows the caller already read from the file — it
does not parse the Markdown itself — and returns an allow/refuse decision.
This keeps the gate itself unit-testable while the table lookup around it
is exercised only at the FVT level (skill/model transcript).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .reference_tables import SelectionRow, SupportStatus


class GateDecision(str, Enum):
    """Outcome of evaluating one requested selection against the catalogue."""

    ALLOW = "allow"
    REFUSE = "refuse"


@dataclass(frozen=True)
class GateResult:
    """Result of `evaluate_selection`.

    Attributes:
        decision: `ALLOW` for a `supported` selection, `REFUSE` otherwise.
        support_status: The recorded status of the requested selection, or
            `None` if the axis/option pair is not in the catalogue at all.
        message: Operator-facing explanation. States the recorded
            support_status and supported alternatives on refusal.
        alternatives: Every `supported` option on the same axis.
    """

    decision: GateDecision
    support_status: SupportStatus | None
    message: str
    alternatives: tuple[str, ...]


def evaluate_selection(
    catalogue_rows: Iterable[SelectionRow], axis: str, option: str
) -> GateResult:
    """Allow a `supported` selection; refuse `planned`/`unsupported` or unknown ones.

    Never silently substitutes a similar supported option — a refusal
    states the alternatives but does not choose one on the operator's
    behalf (FR-2).

    Args:
        catalogue_rows: The A.1 Selection Catalogue rows the caller read
            from the master reference file (typically all rows, or at
            least every row on `axis`).
        axis: Decision axis, e.g. "os_version", "stack", "gpu", "storage".
        option: The requested option, e.g. "AMD / ROCm".

    Returns:
        A `GateResult` describing whether the selection is allowed.
    """
    rows = list(catalogue_rows)
    axis_norm = axis.strip().lower()
    option_norm = option.strip().lower()

    matched: SelectionRow | None = None
    for row in rows:
        if row.axis.strip().lower() == axis_norm and row.option.strip().lower() == option_norm:
            matched = row
            break

    alternatives = tuple(
        row.option
        for row in rows
        if row.axis.strip().lower() == axis_norm and row.support_status == SupportStatus.SUPPORTED
    )

    if matched is None:
        return GateResult(
            decision=GateDecision.REFUSE,
            support_status=None,
            message=(
                f"'{option}' is not recorded on axis '{axis}' in the master reference "
                "file. This request is not available offline; flag it for manual "
                "review or online resolution rather than fabricating a decision."
            ),
            alternatives=alternatives,
        )

    if matched.support_status == SupportStatus.SUPPORTED:
        return GateResult(
            decision=GateDecision.ALLOW,
            support_status=matched.support_status,
            message=f"'{option}' is supported for axis '{axis}'.",
            alternatives=alternatives,
        )

    return GateResult(
        decision=GateDecision.REFUSE,
        support_status=matched.support_status,
        message=(
            f"'{option}' is {matched.support_status.value} for axis '{axis}' and "
            f"was refused. Supported alternatives on this axis: "
            f"{', '.join(alternatives) if alternatives else '(none recorded)'}. "
            "The skill does not substitute a similar supported option without "
            "explicit operator confirmation."
        ),
        alternatives=alternatives,
    )
