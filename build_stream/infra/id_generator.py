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

import time
import uuid

from core.jobs.exceptions import JobDomainError
from core.jobs.repositories import JobIdGenerator
from core.jobs.value_objects import JobId

#TODO: Remove this class once uuid7 is available in the standard library
class UUIDv7Generator(JobIdGenerator):
    def generate(self) -> JobId:
        try:
            return JobId(str(self._uuid7()))
        except ValueError:
            raise
        except Exception as exc:
            raise JobDomainError(f"Failed to generate JobId: {exc}") from exc

    def _uuid7(self) -> uuid.UUID:
        timestamp_ms = int(time.time() * 1000)
        timestamp_bytes = timestamp_ms.to_bytes(6, byteorder='big')
        
        random_bytes = uuid.uuid4().bytes
        
        uuid7_bytes = bytearray(16)
        uuid7_bytes[:6] = timestamp_bytes
        uuid7_bytes[6:] = random_bytes[6:]
        
        uuid7_bytes[6] = (0x07 << 4) | (uuid7_bytes[6] & 0x0f)
        uuid7_bytes[8] = 0x80 | (uuid7_bytes[8] & 0x3f)
        
        return uuid.UUID(bytes=bytes(uuid7_bytes))
