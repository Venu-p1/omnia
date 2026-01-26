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

"""Unit tests for SQL repository implementations."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from sqlalchemy.exc import IntegrityError

# Add build_stream directory to path for imports
build_stream_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(build_stream_dir))

from build_stream.core.jobs.entities.audit import AuditEvent
from build_stream.core.jobs.entities.idempotency import IdempotencyRecord
from build_stream.core.jobs.entities.job import Job
from build_stream.core.jobs.entities.stage import Stage
from build_stream.core.jobs.exceptions import OptimisticLockError
from build_stream.core.jobs.value_objects import JobId, IdempotencyKey, StageName
from build_stream.infra.db.models import AuditEventModel, IdempotencyKeyModel, JobModel, StageModel
from build_stream.infra.db.repositories import (
    SqlAuditEventRepository,
    SqlIdempotencyRepository,
    SqlJobRepository,
    SqlStageRepository,
)


class TestSqlJobRepository:
    """Tests for SqlJobRepository."""
    
    def test_save_inserts_new_job(self, mock_session, sample_job: Job):
        """Test saving a new job inserts into database."""
        mock_session.get.return_value = None
        
        repo = SqlJobRepository(mock_session)
        repo.save(sample_job)
        
        mock_session.add.assert_called_once()
        added_model = mock_session.add.call_args[0][0]
        assert isinstance(added_model, JobModel)
        assert added_model.job_id == str(sample_job.job_id)
        mock_session.flush.assert_called_once()
    
    def test_save_updates_existing_job(self, mock_session, sample_job: Job, sample_job_model: JobModel):
        """Test saving an existing job updates the record."""
        sample_job_model.version = 1
        sample_job.version = 2
        mock_session.get.return_value = sample_job_model
        
        repo = SqlJobRepository(mock_session)
        repo.save(sample_job)
        
        assert sample_job_model.version == 2
        assert sample_job_model.updated_at == sample_job.updated_at
        mock_session.flush.assert_called_once()
        mock_session.add.assert_not_called()
    
    def test_save_raises_optimistic_lock_error_on_version_conflict(
        self, mock_session, sample_job: Job, sample_job_model: JobModel
    ):
        """Test save raises OptimisticLockError when version conflicts."""
        sample_job_model.version = 5
        sample_job.version = 3
        mock_session.get.return_value = sample_job_model
        
        repo = SqlJobRepository(mock_session)
        
        with pytest.raises(OptimisticLockError) as exc_info:
            repo.save(sample_job)
        
        assert exc_info.value.entity_type == "Job"
        assert exc_info.value.expected_version == 2
        assert exc_info.value.actual_version == 5
    
    def test_save_raises_optimistic_lock_error_on_integrity_error(
        self, mock_session, sample_job: Job
    ):
        """Test save raises OptimisticLockError when IntegrityError occurs."""
        mock_session.get.return_value = None
        mock_session.flush.side_effect = IntegrityError("statement", "params", "orig")
        
        repo = SqlJobRepository(mock_session)
        
        with pytest.raises(OptimisticLockError):
            repo.save(sample_job)
    
    def test_find_by_id_returns_job_when_found(
        self, mock_session, sample_job_id: JobId, sample_job_model: JobModel
    ):
        """Test find_by_id returns Job entity when found."""
        mock_session.get.return_value = sample_job_model
        
        repo = SqlJobRepository(mock_session)
        job = repo.find_by_id(sample_job_id)
        
        assert job is not None
        assert str(job.job_id) == sample_job_model.job_id
        mock_session.get.assert_called_once_with(JobModel, str(sample_job_id))
    
    def test_find_by_id_returns_none_when_not_found(self, mock_session, sample_job_id: JobId):
        """Test find_by_id returns None when job not found."""
        mock_session.get.return_value = None
        
        repo = SqlJobRepository(mock_session)
        job = repo.find_by_id(sample_job_id)
        
        assert job is None
    
    def test_exists_returns_true_when_job_exists(self, mock_session, sample_job_id: JobId):
        """Test exists returns True when job exists."""
        mock_result = MagicMock()
        mock_result.first.return_value = (str(sample_job_id),)
        mock_session.execute.return_value = mock_result
        
        repo = SqlJobRepository(mock_session)
        result = repo.exists(sample_job_id)
        
        assert result is True
    
    def test_exists_returns_false_when_job_not_found(self, mock_session, sample_job_id: JobId):
        """Test exists returns False when job not found."""
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result
        
        repo = SqlJobRepository(mock_session)
        result = repo.exists(sample_job_id)
        
        assert result is False


class TestSqlStageRepository:
    """Tests for SqlStageRepository."""
    
    def test_save_inserts_new_stage(self, mock_session, sample_stage: Stage):
        """Test saving a new stage inserts into database."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        repo = SqlStageRepository(mock_session)
        repo.save(sample_stage)
        
        mock_session.add.assert_called_once()
        added_model = mock_session.add.call_args[0][0]
        assert isinstance(added_model, StageModel)
        assert added_model.job_id == str(sample_stage.job_id)
        assert added_model.stage_name == str(sample_stage.stage_name)
        mock_session.flush.assert_called_once()
    
    def test_save_updates_existing_stage(self, mock_session, sample_stage: Stage, sample_stage_model: StageModel):
        """Test saving an existing stage updates the record."""
        sample_stage_model.version = 1
        sample_stage.version = 2
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_stage_model
        mock_session.execute.return_value = mock_result
        
        repo = SqlStageRepository(mock_session)
        repo.save(sample_stage)
        
        assert sample_stage_model.version == 2
        mock_session.flush.assert_called_once()
        mock_session.add.assert_not_called()
    
    def test_save_raises_optimistic_lock_error_on_version_conflict(
        self, mock_session, sample_stage: Stage, sample_stage_model: StageModel
    ):
        """Test save raises OptimisticLockError when version conflicts."""
        sample_stage_model.version = 5
        sample_stage.version = 3
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_stage_model
        mock_session.execute.return_value = mock_result
        
        repo = SqlStageRepository(mock_session)
        
        with pytest.raises(OptimisticLockError) as exc_info:
            repo.save(sample_stage)
        
        assert exc_info.value.entity_type == "Stage"
        assert exc_info.value.expected_version == 2
        assert exc_info.value.actual_version == 5
    
    def test_save_all_saves_multiple_stages(self, mock_session, sample_stage: Stage):
        """Test save_all persists multiple stages."""
        stages = [sample_stage, sample_stage]
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        repo = SqlStageRepository(mock_session)
        repo.save_all(stages)
        
        assert mock_session.add.call_count == 2
        assert mock_session.flush.call_count == 2
    
    def test_find_by_job_and_name_returns_stage_when_found(
        self, mock_session, sample_job_id: JobId, sample_stage_name: StageName, sample_stage_model: StageModel
    ):
        """Test find_by_job_and_name returns Stage when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_stage_model
        mock_session.execute.return_value = mock_result
        
        repo = SqlStageRepository(mock_session)
        stage = repo.find_by_job_and_name(sample_job_id, sample_stage_name)
        
        assert stage is not None
        assert str(stage.job_id) == sample_stage_model.job_id
        assert str(stage.stage_name) == sample_stage_model.stage_name
    
    def test_find_by_job_and_name_returns_none_when_not_found(
        self, mock_session, sample_job_id: JobId, sample_stage_name: StageName
    ):
        """Test find_by_job_and_name returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        repo = SqlStageRepository(mock_session)
        stage = repo.find_by_job_and_name(sample_job_id, sample_stage_name)
        
        assert stage is None
    
    def test_find_all_by_job_returns_stages(
        self, mock_session, sample_job_id: JobId, sample_stage_model: StageModel
    ):
        """Test find_all_by_job returns list of stages."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_stage_model, sample_stage_model]
        mock_session.execute.return_value = mock_result
        
        repo = SqlStageRepository(mock_session)
        stages = repo.find_all_by_job(sample_job_id)
        
        assert len(stages) == 2
        assert all(isinstance(s, Stage) for s in stages)
    
    def test_find_all_by_job_returns_empty_list_when_none_found(
        self, mock_session, sample_job_id: JobId
    ):
        """Test find_all_by_job returns empty list when no stages found."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        repo = SqlStageRepository(mock_session)
        stages = repo.find_all_by_job(sample_job_id)
        
        assert stages == []


class TestSqlIdempotencyRepository:
    """Tests for SqlIdempotencyRepository."""
    
    def test_save_persists_record(self, mock_session, sample_idempotency_record: IdempotencyRecord):
        """Test save persists idempotency record."""
        repo = SqlIdempotencyRepository(mock_session)
        repo.save(sample_idempotency_record)
        
        mock_session.merge.assert_called_once()
        merged_model = mock_session.merge.call_args[0][0]
        assert isinstance(merged_model, IdempotencyKeyModel)
        assert merged_model.idempotency_key == str(sample_idempotency_record.idempotency_key)
        mock_session.flush.assert_called_once()
    
    def test_find_by_key_returns_record_when_found(
        self, mock_session, sample_idempotency_key: IdempotencyKey, sample_idempotency_model: IdempotencyKeyModel
    ):
        """Test find_by_key returns IdempotencyRecord when found."""
        mock_session.get.return_value = sample_idempotency_model
        
        repo = SqlIdempotencyRepository(mock_session)
        record = repo.find_by_key(sample_idempotency_key)
        
        assert record is not None
        assert str(record.idempotency_key) == sample_idempotency_model.idempotency_key
        mock_session.get.assert_called_once_with(IdempotencyKeyModel, str(sample_idempotency_key))
    
    def test_find_by_key_returns_none_when_not_found(
        self, mock_session, sample_idempotency_key: IdempotencyKey
    ):
        """Test find_by_key returns None when not found."""
        mock_session.get.return_value = None
        
        repo = SqlIdempotencyRepository(mock_session)
        record = repo.find_by_key(sample_idempotency_key)
        
        assert record is None


class TestSqlAuditEventRepository:
    """Tests for SqlAuditEventRepository."""
    
    def test_save_persists_event(self, mock_session, sample_audit_event: AuditEvent):
        """Test save persists audit event."""
        repo = SqlAuditEventRepository(mock_session)
        repo.save(sample_audit_event)
        
        mock_session.add.assert_called_once()
        added_model = mock_session.add.call_args[0][0]
        assert isinstance(added_model, AuditEventModel)
        assert added_model.job_id == str(sample_audit_event.job_id)
        assert added_model.event_type == sample_audit_event.event_type
        mock_session.flush.assert_called_once()
    
    def test_find_by_job_returns_events(
        self, mock_session, sample_job_id: JobId, sample_audit_model: AuditEventModel
    ):
        """Test find_by_job returns list of audit events."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_audit_model, sample_audit_model]
        mock_session.execute.return_value = mock_result
        
        repo = SqlAuditEventRepository(mock_session)
        events = repo.find_by_job(sample_job_id)
        
        assert len(events) == 2
        assert all(isinstance(e, AuditEvent) for e in events)
    
    def test_find_by_job_returns_empty_list_when_none_found(
        self, mock_session, sample_job_id: JobId
    ):
        """Test find_by_job returns empty list when no events found."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        repo = SqlAuditEventRepository(mock_session)
        events = repo.find_by_job(sample_job_id)
        
        assert events == []
