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

"""Shared fixtures for infra.db unit tests."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add build_stream directory to path for imports
build_stream_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(build_stream_dir))

from build_stream.core.jobs.entities.audit import AuditEvent
from build_stream.core.jobs.entities.idempotency import IdempotencyRecord
from build_stream.core.jobs.entities.job import Job
from build_stream.core.jobs.entities.stage import Stage
from build_stream.core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    IdempotencyKey,
    JobId,
    JobState,
    RequestFingerprint,
    StageName,
    StageState,
)
from build_stream.infra.db.models import AuditEventModel, IdempotencyKeyModel, JobModel, StageModel


@pytest.fixture
def sample_job_id() -> JobId:
    """Sample JobId for testing."""
    return JobId("01234567-89ab-7def-8123-456789abcdef")


@pytest.fixture
def sample_client_id() -> ClientId:
    """Sample ClientId for testing."""
    return ClientId("test-client-123")


@pytest.fixture
def sample_correlation_id() -> CorrelationId:
    """Sample CorrelationId for testing."""
    return CorrelationId("01234567-89ab-7def-9123-456789abcdef")


@pytest.fixture
def sample_stage_name() -> StageName:
    """Sample StageName for testing."""
    return StageName("parse-catalog")


@pytest.fixture
def sample_idempotency_key() -> IdempotencyKey:
    """Sample IdempotencyKey for testing."""
    return IdempotencyKey("test-idempotency-key-123")


@pytest.fixture
def sample_timestamp() -> datetime:
    """Sample timestamp for testing."""
    return datetime(2026, 1, 26, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_job(sample_job_id: JobId, sample_client_id: ClientId, sample_timestamp: datetime) -> Job:
    """Sample Job entity for testing."""
    return Job(
        job_id=sample_job_id,
        client_id=sample_client_id,
        catalog_digest="sha256:abcdef1234567890",
        job_state=JobState.CREATED,
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        version=1,
        tombstoned=False,
    )


@pytest.fixture
def sample_stage(
    sample_job_id: JobId,
    sample_stage_name: StageName,
    sample_timestamp: datetime,
) -> Stage:
    """Sample Stage entity for testing."""
    return Stage(
        job_id=sample_job_id,
        stage_name=sample_stage_name,
        stage_state=StageState.PENDING,
        attempt=0,
        started_at=None,
        ended_at=None,
        error_code=None,
        error_summary=None,
        version=1,
    )


@pytest.fixture
def sample_idempotency_record(
    sample_idempotency_key: IdempotencyKey,
    sample_job_id: JobId,
    sample_client_id: ClientId,
    sample_timestamp: datetime,
) -> IdempotencyRecord:
    """Sample IdempotencyRecord entity for testing."""
    from datetime import timedelta
    return IdempotencyRecord(
        idempotency_key=sample_idempotency_key,
        job_id=sample_job_id,
        request_fingerprint=RequestFingerprint("a" * 64),  # Valid SHA-256 hex
        client_id=sample_client_id,
        created_at=sample_timestamp,
        expires_at=sample_timestamp + timedelta(hours=24),
    )


@pytest.fixture
def sample_audit_event(
    sample_job_id: JobId,
    sample_client_id: ClientId,
    sample_correlation_id: CorrelationId,
    sample_timestamp: datetime,
) -> AuditEvent:
    """Sample AuditEvent entity for testing."""
    return AuditEvent(
        event_id="01234567-89ab-7def-9999-456789abcdef",
        job_id=sample_job_id,
        event_type="JOB_CREATED",
        correlation_id=sample_correlation_id,
        client_id=sample_client_id,
        timestamp=sample_timestamp,
        details={"catalog_digest": "sha256:abcdef1234567890"},
    )


@pytest.fixture
def sample_job_model(sample_timestamp: datetime) -> JobModel:
    """Sample JobModel ORM instance for testing."""
    return JobModel(
        job_id="01234567-89ab-7def-8123-456789abcdef",
        client_id="test-client-123",
        catalog_digest="sha256:abcdef1234567890",
        job_state="CREATED",
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        version=1,
        tombstoned=False,
    )


@pytest.fixture
def sample_stage_model(sample_timestamp: datetime) -> StageModel:
    """Sample StageModel ORM instance for testing."""
    return StageModel(
        job_id="01234567-89ab-7def-8123-456789abcdef",
        stage_name="parse-catalog",
        stage_state="PENDING",
        attempt=0,
        started_at=None,
        ended_at=None,
        error_code=None,
        error_summary=None,
        version=1,
    )


@pytest.fixture
def sample_idempotency_model(sample_timestamp: datetime) -> IdempotencyKeyModel:
    """Sample IdempotencyKeyModel ORM instance for testing."""
    from datetime import timedelta
    return IdempotencyKeyModel(
        idempotency_key="test-idempotency-key-123",
        job_id="01234567-89ab-7def-8123-456789abcdef",
        request_fingerprint="a" * 64,  # Valid SHA-256 hex
        client_id="test-client-123",
        created_at=sample_timestamp,
        expires_at=sample_timestamp + timedelta(hours=24),
    )


@pytest.fixture
def sample_audit_model(sample_timestamp: datetime) -> AuditEventModel:
    """Sample AuditEventModel ORM instance for testing."""
    return AuditEventModel(
        event_id="01234567-89ab-7def-9999-456789abcdef",
        job_id="01234567-89ab-7def-8123-456789abcdef",
        event_type="JOB_CREATED",
        correlation_id="01234567-89ab-7def-9123-456789abcdef",
        client_id="test-client-123",
        timestamp=sample_timestamp,
        details='{"catalog_digest": "sha256:abcdef1234567890"}',
    )


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session for testing."""
    session = MagicMock()
    session.get.return_value = None
    session.execute.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value.scalars.return_value.all.return_value = []
    session.execute.return_value.first.return_value = None
    return session
