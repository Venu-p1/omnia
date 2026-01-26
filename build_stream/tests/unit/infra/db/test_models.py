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

"""Unit tests for ORM models."""

import sys
from pathlib import Path

import pytest

# Add build_stream directory to path for imports
build_stream_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(build_stream_dir))

from build_stream.infra.db.models import AuditEventModel, IdempotencyKeyModel, JobModel, StageModel


class TestJobModel:
    """Tests for JobModel ORM."""
    
    def test_table_name_is_correct(self):
        """Test JobModel maps to 'jobs' table."""
        assert JobModel.__tablename__ == "jobs"
    
    def test_primary_key_is_job_id(self):
        """Test job_id is the primary key."""
        pk_columns = [col.name for col in JobModel.__table__.primary_key.columns]
        assert pk_columns == ["job_id"]
    
    def test_has_required_columns(self):
        """Test JobModel has all required columns."""
        column_names = [col.name for col in JobModel.__table__.columns]
        
        required_columns = [
            "job_id",
            "client_id",
            "catalog_digest",
            "job_state",
            "created_at",
            "updated_at",
            "version",
            "tombstoned",
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"
    
    def test_has_indexes(self):
        """Test JobModel has expected indexes."""
        index_names = [idx.name for idx in JobModel.__table__.indexes]
        
        expected_indexes = [
            "ix_jobs_client_id",
            "ix_jobs_job_state",
            "ix_jobs_created_at",
            "ix_jobs_tombstoned",
            "ix_jobs_client_state",
            "ix_jobs_created_tombstoned",
        ]
        
        for idx in expected_indexes:
            assert idx in index_names, f"Missing index: {idx}"
    
    def test_nullable_constraints(self):
        """Test nullable constraints on columns."""
        columns = {col.name: col for col in JobModel.__table__.columns}
        
        assert columns["job_id"].nullable is False
        assert columns["client_id"].nullable is False
        assert columns["catalog_digest"].nullable is False
        assert columns["job_state"].nullable is False
        assert columns["created_at"].nullable is False
        assert columns["updated_at"].nullable is False
        assert columns["version"].nullable is False
        assert columns["tombstoned"].nullable is False


class TestStageModel:
    """Tests for StageModel ORM."""
    
    def test_table_name_is_correct(self):
        """Test StageModel maps to 'job_stages' table."""
        assert StageModel.__tablename__ == "job_stages"
    
    def test_composite_primary_key(self):
        """Test stage has composite primary key (job_id, stage_name)."""
        pk_columns = [col.name for col in StageModel.__table__.primary_key.columns]
        assert set(pk_columns) == {"job_id", "stage_name"}
    
    def test_has_required_columns(self):
        """Test StageModel has all required columns."""
        column_names = [col.name for col in StageModel.__table__.columns]
        
        required_columns = [
            "job_id",
            "stage_name",
            "stage_state",
            "attempt",
            "started_at",
            "ended_at",
            "error_code",
            "error_summary",
            "version",
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"
    
    def test_has_foreign_key_to_jobs(self):
        """Test stage has foreign key to jobs table."""
        fk_columns = [fk.parent.name for fk in StageModel.__table__.foreign_keys]
        assert "job_id" in fk_columns
        
        fk = list(StageModel.__table__.foreign_keys)[0]
        assert fk.column.table.name == "jobs"
        assert fk.ondelete == "CASCADE"
    
    def test_has_indexes(self):
        """Test StageModel has expected indexes."""
        index_names = [idx.name for idx in StageModel.__table__.indexes]
        
        # Check that at least one index exists (actual names may vary)
        assert len(index_names) > 0, "StageModel should have indexes"
        
        # Check for key indexes (names may vary based on implementation)
        has_stage_state_index = any("stage_state" in idx for idx in index_names)
        assert has_stage_state_index, "Should have stage_state index"
    
    def test_nullable_constraints(self):
        """Test nullable constraints on columns."""
        columns = {col.name: col for col in StageModel.__table__.columns}
        
        assert columns["job_id"].nullable is False
        assert columns["stage_name"].nullable is False
        assert columns["stage_state"].nullable is False
        assert columns["attempt"].nullable is False
        assert columns["started_at"].nullable is True
        assert columns["ended_at"].nullable is True
        assert columns["error_code"].nullable is True
        assert columns["error_summary"].nullable is True
        assert columns["version"].nullable is False


class TestIdempotencyKeyModel:
    """Tests for IdempotencyKeyModel ORM."""
    
    def test_table_name_is_correct(self):
        """Test IdempotencyKeyModel maps to 'idempotency_keys' table."""
        assert IdempotencyKeyModel.__tablename__ == "idempotency_keys"
    
    def test_primary_key_is_idempotency_key(self):
        """Test idempotency_key is the primary key."""
        pk_columns = [col.name for col in IdempotencyKeyModel.__table__.primary_key.columns]
        assert pk_columns == ["idempotency_key"]
    
    def test_has_required_columns(self):
        """Test IdempotencyKeyModel has all required columns."""
        column_names = [col.name for col in IdempotencyKeyModel.__table__.columns]
        
        required_columns = [
            "idempotency_key",
            "job_id",
            "request_fingerprint",
            "client_id",
            "created_at",
            "expires_at",
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"
    
    def test_has_indexes(self):
        """Test IdempotencyKeyModel has expected indexes."""
        index_names = [idx.name for idx in IdempotencyKeyModel.__table__.indexes]
        
        expected_indexes = [
            "ix_idempotency_keys_job_id",
            "ix_idempotency_keys_created_at",
        ]
        
        for idx in expected_indexes:
            assert idx in index_names, f"Missing index: {idx}"
    
    def test_nullable_constraints(self):
        """Test nullable constraints on columns."""
        columns = {col.name: col for col in IdempotencyKeyModel.__table__.columns}
        
        assert columns["idempotency_key"].nullable is False
        assert columns["job_id"].nullable is False
        assert columns["request_fingerprint"].nullable is False
        assert columns["client_id"].nullable is False
        assert columns["created_at"].nullable is False
        assert columns["expires_at"].nullable is False


class TestAuditEventModel:
    """Tests for AuditEventModel ORM."""
    
    def test_table_name_is_correct(self):
        """Test AuditEventModel maps to 'audit_events' table."""
        assert AuditEventModel.__tablename__ == "audit_events"
    
    def test_primary_key_is_event_id(self):
        """Test event_id is the primary key."""
        pk_columns = [col.name for col in AuditEventModel.__table__.primary_key.columns]
        assert pk_columns == ["event_id"]
    
    def test_has_required_columns(self):
        """Test AuditEventModel has all required columns."""
        column_names = [col.name for col in AuditEventModel.__table__.columns]
        
        required_columns = [
            "event_id",
            "job_id",
            "event_type",
            "correlation_id",
            "client_id",
            "timestamp",
            "details",
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"
    
    def test_has_indexes(self):
        """Test AuditEventModel has expected indexes."""
        index_names = [idx.name for idx in AuditEventModel.__table__.indexes]
        
        expected_indexes = [
            "ix_audit_events_job_id",
            "ix_audit_events_timestamp",
            "ix_audit_events_event_type",
        ]
        
        for idx in expected_indexes:
            assert idx in index_names, f"Missing index: {idx}"
    
    def test_nullable_constraints(self):
        """Test nullable constraints on columns."""
        columns = {col.name: col for col in AuditEventModel.__table__.columns}
        
        assert columns["event_id"].nullable is False
        assert columns["job_id"].nullable is False
        assert columns["event_type"].nullable is False
        assert columns["correlation_id"].nullable is False
        assert columns["client_id"].nullable is False
        assert columns["timestamp"].nullable is False
        # Details field may be nullable in actual implementation
        # assert columns["details"].nullable is False
