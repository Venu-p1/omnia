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

"""Unit tests for domain-ORM mappers."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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
from build_stream.infra.db.mappers import (
    AuditEventMapper,
    IdempotencyRecordMapper,
    JobMapper,
    StageMapper,
)
from build_stream.infra.db.models import AuditEventModel, IdempotencyKeyModel, JobModel, StageModel


class TestJobMapper:
    """Tests for JobMapper."""
    
    def test_to_orm_converts_job_to_model(self, sample_job: Job):
        """Test converting Job entity to JobModel ORM."""
        model = JobMapper.to_orm(sample_job)
        
        assert isinstance(model, JobModel)
        assert model.job_id == str(sample_job.job_id)
        assert model.client_id == str(sample_job.client_id)
        assert model.catalog_digest == sample_job.catalog_digest
        assert model.job_state == sample_job.job_state.value
        assert model.created_at == sample_job.created_at
        assert model.updated_at == sample_job.updated_at
        assert model.version == sample_job.version
        assert model.tombstoned == sample_job.tombstoned
    
    def test_to_domain_converts_model_to_job(self, sample_job_model: JobModel):
        """Test converting JobModel ORM to Job entity."""
        job = JobMapper.to_domain(sample_job_model)
        
        assert isinstance(job, Job)
        assert str(job.job_id) == sample_job_model.job_id
        assert str(job.client_id) == sample_job_model.client_id
        assert job.catalog_digest == sample_job_model.catalog_digest
        assert job.job_state.value == sample_job_model.job_state
        assert job.created_at == sample_job_model.created_at
        assert job.updated_at == sample_job_model.updated_at
        assert job.version == sample_job_model.version
        assert job.tombstoned == sample_job_model.tombstoned
    
    def test_roundtrip_conversion_preserves_data(self, sample_job: Job):
        """Test that Job -> Model -> Job preserves all data."""
        model = JobMapper.to_orm(sample_job)
        restored_job = JobMapper.to_domain(model)
        
        assert str(restored_job.job_id) == str(sample_job.job_id)
        assert str(restored_job.client_id) == str(sample_job.client_id)
        assert restored_job.catalog_digest == sample_job.catalog_digest
        assert restored_job.job_state == sample_job.job_state
        assert restored_job.created_at == sample_job.created_at
        assert restored_job.updated_at == sample_job.updated_at
        assert restored_job.version == sample_job.version
        assert restored_job.tombstoned == sample_job.tombstoned
    
    def test_to_orm_handles_different_job_states(self, sample_job: Job):
        """Test mapper handles all job states correctly."""
        for state in JobState:
            job = Job(
                job_id=sample_job.job_id,
                client_id=sample_job.client_id,
                catalog_digest=sample_job.catalog_digest,
                job_state=state,
                created_at=sample_job.created_at,
                updated_at=sample_job.updated_at,
                version=sample_job.version,
                tombstoned=sample_job.tombstoned,
            )
            model = JobMapper.to_orm(job)
            assert model.job_state == state.value


class TestStageMapper:
    """Tests for StageMapper."""
    
    def test_to_orm_converts_stage_to_model(self, sample_stage: Stage):
        """Test converting Stage entity to StageModel ORM."""
        model = StageMapper.to_orm(sample_stage)
        
        assert isinstance(model, StageModel)
        assert model.job_id == str(sample_stage.job_id)
        assert model.stage_name == str(sample_stage.stage_name)
        assert model.stage_state == sample_stage.stage_state.value
        assert model.attempt == sample_stage.attempt
        assert model.started_at == sample_stage.started_at
        assert model.ended_at == sample_stage.ended_at
        assert model.error_code == sample_stage.error_code
        assert model.error_summary == sample_stage.error_summary
        assert model.version == sample_stage.version
    
    def test_to_domain_converts_model_to_stage(self, sample_stage_model: StageModel):
        """Test converting StageModel ORM to Stage entity."""
        stage = StageMapper.to_domain(sample_stage_model)
        
        assert isinstance(stage, Stage)
        assert str(stage.job_id) == sample_stage_model.job_id
        assert str(stage.stage_name) == sample_stage_model.stage_name
        assert stage.stage_state.value == sample_stage_model.stage_state
        assert stage.attempt == sample_stage_model.attempt
        assert stage.started_at == sample_stage_model.started_at
        assert stage.ended_at == sample_stage_model.ended_at
        assert stage.error_code == sample_stage_model.error_code
        assert stage.error_summary == sample_stage_model.error_summary
        assert stage.version == sample_stage_model.version
    
    def test_roundtrip_conversion_preserves_data(self, sample_stage: Stage):
        """Test that Stage -> Model -> Stage preserves all data."""
        model = StageMapper.to_orm(sample_stage)
        restored_stage = StageMapper.to_domain(model)
        
        assert str(restored_stage.job_id) == str(sample_stage.job_id)
        assert str(restored_stage.stage_name) == str(sample_stage.stage_name)
        assert restored_stage.stage_state == sample_stage.stage_state
        assert restored_stage.attempt == sample_stage.attempt
        assert restored_stage.version == sample_stage.version
    
    def test_to_orm_handles_optional_fields(self, sample_stage: Stage, sample_timestamp: datetime):
        """Test mapper handles optional fields (started_at, ended_at, error_code, error_summary)."""
        stage_with_optionals = Stage(
            job_id=sample_stage.job_id,
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.FAILED,
            attempt=3,
            started_at=sample_timestamp,
            ended_at=sample_timestamp,
            error_code="VALIDATION_ERROR",
            error_summary="Catalog validation failed",
            version=1,
        )
        
        model = StageMapper.to_orm(stage_with_optionals)
        
        assert model.started_at == sample_timestamp
        assert model.ended_at == sample_timestamp
        assert model.error_code == "VALIDATION_ERROR"
        assert model.error_summary == "Catalog validation failed"


class TestIdempotencyRecordMapper:
    """Tests for IdempotencyRecordMapper."""
    
    def test_to_orm_converts_record_to_model(self, sample_idempotency_record: IdempotencyRecord):
        """Test converting IdempotencyRecord entity to IdempotencyKeyModel ORM."""
        model = IdempotencyRecordMapper.to_orm(sample_idempotency_record)
        
        assert isinstance(model, IdempotencyKeyModel)
        assert model.idempotency_key == str(sample_idempotency_record.idempotency_key)
        assert model.job_id == str(sample_idempotency_record.job_id)
        assert model.request_fingerprint == str(sample_idempotency_record.request_fingerprint)
        assert model.client_id == str(sample_idempotency_record.client_id)
        assert model.created_at == sample_idempotency_record.created_at
        assert model.expires_at == sample_idempotency_record.expires_at
    
    def test_to_domain_converts_model_to_record(self, sample_idempotency_model: IdempotencyKeyModel):
        """Test converting IdempotencyKeyModel ORM to IdempotencyRecord entity."""
        record = IdempotencyRecordMapper.to_domain(sample_idempotency_model)
        
        assert isinstance(record, IdempotencyRecord)
        assert str(record.idempotency_key) == sample_idempotency_model.idempotency_key
        assert str(record.job_id) == sample_idempotency_model.job_id
        assert str(record.request_fingerprint) == sample_idempotency_model.request_fingerprint
        assert str(record.client_id) == sample_idempotency_model.client_id
        assert record.created_at == sample_idempotency_model.created_at
        assert record.expires_at == sample_idempotency_model.expires_at
    
    def test_roundtrip_conversion_preserves_data(self, sample_idempotency_record: IdempotencyRecord):
        """Test that IdempotencyRecord -> Model -> IdempotencyRecord preserves all data."""
        model = IdempotencyRecordMapper.to_orm(sample_idempotency_record)
        restored_record = IdempotencyRecordMapper.to_domain(model)
        
        assert str(restored_record.idempotency_key) == str(sample_idempotency_record.idempotency_key)
        assert str(restored_record.job_id) == str(sample_idempotency_record.job_id)
        assert str(restored_record.request_fingerprint) == str(sample_idempotency_record.request_fingerprint)
        assert str(restored_record.client_id) == str(sample_idempotency_record.client_id)
        assert restored_record.created_at == sample_idempotency_record.created_at
        assert restored_record.expires_at == sample_idempotency_record.expires_at


class TestAuditEventMapper:
    """Tests for AuditEventMapper."""
    
    def test_to_orm_converts_event_to_model(self, sample_audit_event: AuditEvent):
        """Test converting AuditEvent entity to AuditEventModel ORM."""
        model = AuditEventMapper.to_orm(sample_audit_event)
        
        assert isinstance(model, AuditEventModel)
        assert model.event_id == sample_audit_event.event_id
        assert model.job_id == str(sample_audit_event.job_id)
        assert model.event_type == sample_audit_event.event_type
        assert model.correlation_id == str(sample_audit_event.correlation_id)
        assert model.client_id == str(sample_audit_event.client_id)
        assert model.timestamp == sample_audit_event.timestamp
        
        details_dict = json.loads(model.details)
        assert details_dict == sample_audit_event.details
    
    def test_to_domain_converts_model_to_event(self, sample_audit_model: AuditEventModel):
        """Test converting AuditEventModel ORM to AuditEvent entity."""
        event = AuditEventMapper.to_domain(sample_audit_model)
        
        assert isinstance(event, AuditEvent)
        assert event.event_id == sample_audit_model.event_id
        assert str(event.job_id) == sample_audit_model.job_id
        assert event.event_type == sample_audit_model.event_type
        assert str(event.correlation_id) == sample_audit_model.correlation_id
        assert str(event.client_id) == sample_audit_model.client_id
        assert event.timestamp == sample_audit_model.timestamp
        
        expected_details = json.loads(sample_audit_model.details)
        assert event.details == expected_details
    
    def test_roundtrip_conversion_preserves_data(self, sample_audit_event: AuditEvent):
        """Test that AuditEvent -> Model -> AuditEvent preserves all data."""
        model = AuditEventMapper.to_orm(sample_audit_event)
        restored_event = AuditEventMapper.to_domain(model)
        
        assert restored_event.event_id == sample_audit_event.event_id
        assert str(restored_event.job_id) == str(sample_audit_event.job_id)
        assert restored_event.event_type == sample_audit_event.event_type
        assert str(restored_event.correlation_id) == str(sample_audit_event.correlation_id)
        assert str(restored_event.client_id) == str(sample_audit_event.client_id)
        assert restored_event.timestamp == sample_audit_event.timestamp
        assert restored_event.details == sample_audit_event.details
    
    def test_to_orm_handles_complex_details(self, sample_audit_event: AuditEvent):
        """Test mapper handles complex nested details dictionary."""
        complex_event = AuditEvent(
            event_id=sample_audit_event.event_id,
            job_id=sample_audit_event.job_id,
            event_type="STAGE_TRANSITION",
            correlation_id=sample_audit_event.correlation_id,
            client_id=sample_audit_event.client_id,
            timestamp=sample_audit_event.timestamp,
            details={
                "stage": "parse-catalog",
                "from_state": "PENDING",
                "to_state": "IN_PROGRESS",
                "metadata": {
                    "attempt": 1,
                    "worker_id": "worker-123",
                },
            },
        )
        
        model = AuditEventMapper.to_orm(complex_event)
        details_dict = json.loads(model.details)
        
        assert details_dict["stage"] == "parse-catalog"
        assert details_dict["metadata"]["attempt"] == 1
        assert details_dict["metadata"]["worker_id"] == "worker-123"
    
    def test_to_orm_handles_empty_details(self, sample_audit_event: AuditEvent):
        """Test mapper handles empty details dictionary."""
        event_with_empty_details = AuditEvent(
            event_id=sample_audit_event.event_id,
            job_id=sample_audit_event.job_id,
            event_type="JOB_DELETED",
            correlation_id=sample_audit_event.correlation_id,
            client_id=sample_audit_event.client_id,
            timestamp=sample_audit_event.timestamp,
            details={},
        )
        
        model = AuditEventMapper.to_orm(event_with_empty_details)
        # Ensure details is not None before parsing
        assert model.details is not None
        details_dict = json.loads(model.details)
        
        assert details_dict == {}
