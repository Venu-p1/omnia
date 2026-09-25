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

"""Master Reference File creation tooling and the Selection Catalogue gate.

`build_master_reference.py` is a development-time tool run by the Build
Stream team as part of the build/release process. It is not invoked by an
operator and is not imported by the BSM FastAPI application.
`master_reference_file.md` is the packaged deliverable it produces.
`selection_gate.py` is the one runtime-usable module in this package: the
shared `support_status` decision function every catalog-authoring skill
calls after reading the master reference file.
"""
