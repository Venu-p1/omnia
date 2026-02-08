"""
ParseCatalog API Integration Tests

Tests the complete API endpoint behavior including:
- File upload via multipart/form-data
- Successful parsing with artifact storage
- Error responses (invalid JSON, schema validation)
- Authentication/authorization
- Cross-stage artifact lookup
"""

import json
import pytest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock

from fastapi.testclient import TestClient
from httpx import Response

from main import app
from core.jobs.entities import Job, Stage
from core.jobs.value_objects import StageName, CorrelationId, ClientId, JobState, StageState
from container import DevContainer


class TestParseCatalogAPI:
    """Integration tests for ParseCatalog API endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client with in-memory stores."""
        container = DevContainer()
        container.wire(modules=["api.parse_catalog.routes"])
        
        with TestClient(app) as client:
            yield client

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Create authentication headers."""
        return {
            "Authorization": "Bearer test-token",
            "X-Correlation-ID": str(uuid.uuid4()),
        }

    @pytest.fixture
    def valid_catalog_json(self) -> Dict[str, Any]:
        """Valid catalog JSON for testing."""
        return {
            "catalog_version": "1.0",
            "description": "Test catalog",
            "packages": [
                {
                    "name": "test-package",
                    "version": "1.0.0",
                    "architecture": "x86_64",
                    "os": "rhel",
                    "os_version": "9.5",
                    "category": "functional",
                    "dependencies": [],
                    "description": "Test package"
                }
            ],
            "metadata": {
                "created_at": "2026-02-04T10:00:00Z",
                "created_by": "test-user"
            }
        }

    @pytest.fixture
    def created_job(self, client: TestClient, auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """Create a job for testing."""
        response = client.post(
            "/api/v1/jobs",
            json={"client_id": "test-client"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        return response.json()

    def test_parse_catalog_success_happy_path(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
        valid_catalog_json: Dict[str, Any],
    ) -> None:
        """Test successful catalog parsing with artifact storage."""
        job_id = created_job["job_id"]
        
        # Upload catalog file
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test_catalog.json", json.dumps(valid_catalog_json), "application/json")},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["job_id"] == job_id
        assert data["stage_name"] == "parse-catalog"
        assert data["stage_state"] == "COMPLETED"
        assert data["message"] == "Catalog parsed successfully"
        assert "artifacts" in data
        assert "catalog_ref" in data["artifacts"]
        assert "root_jsons_ref" in data["artifacts"]
        assert data["artifacts"]["root_json_count"] > 0
        assert len(data["artifacts"]["arch_os_combinations"]) > 0
        assert "correlation_id" in data
        assert "timestamp" in data

    def test_parse_catalog_with_custom_filename(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
        valid_catalog_json: Dict[str, Any],
    ) -> None:
        """Test parsing with custom filename."""
        job_id = created_job["job_id"]
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("custom_catalog_name.json", json.dumps(valid_catalog_json), "application/json")},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["artifacts"]["catalog_filename"] == "custom_catalog_name.json"

    def test_parse_catalog_invalid_json_format(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
    ) -> None:
        """Test parsing with invalid JSON format."""
        job_id = created_job["job_id"]
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test.txt", "not valid json", "text/plain")},
            headers=auth_headers,
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "INVALID_FILE_FORMAT"
        assert "Only JSON files are accepted" in data["message"]

    def test_parse_catalog_malformed_json(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
    ) -> None:
        """Test parsing with malformed JSON."""
        job_id = created_job["job_id"]
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test.json", '{"invalid": json}', "application/json")},
            headers=auth_headers,
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "INVALID_JSON"
        assert "Invalid JSON data" in data["message"]

    def test_parse_catalog_schema_validation_error(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
    ) -> None:
        """Test parsing with catalog that fails schema validation."""
        job_id = created_job["job_id"]
        
        invalid_catalog = {
            "invalid_field": "this should fail validation",
            "missing_required": True
        }
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test.json", json.dumps(invalid_catalog), "application/json")},
            headers=auth_headers,
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "CATALOG_SCHEMA_VALIDATION_ERROR"
        assert "validation failed" in data["message"].lower()

    def test_parse_catalog_file_too_large(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
    ) -> None:
        """Test parsing with file exceeding size limit."""
        job_id = created_job["job_id"]
        
        # Create a large JSON file (larger than 5MB limit)
        large_catalog = {
            "catalog_version": "1.0",
            "description": "Large catalog",
            "packages": [{"name": f"pkg{i}", "version": "1.0"} for i in range(100000)]
        }
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("large.json", json.dumps(large_catalog), "application/json")},
            headers=auth_headers,
        )
        
        assert response.status_code == 413
        data = response.json()
        assert data["error_code"] == "FILE_TOO_LARGE"

    def test_parse_catalog_job_not_found(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        valid_catalog_json: Dict[str, Any],
    ) -> None:
        """Test parsing with non-existent job ID."""
        fake_job_id = "019bf590-1234-7890-abcd-ef1234567890"
        
        response = client.post(
            f"/api/v1/jobs/{fake_job_id}/stages/parse-catalog",
            files={"catalog": ("test.json", json.dumps(valid_catalog_json), "application/json")},
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "JOB_NOT_FOUND"

    def test_parse_catalog_already_completed(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
        valid_catalog_json: Dict[str, Any],
    ) -> None:
        """Test parsing when stage already completed."""
        job_id = created_job["job_id"]
        
        # First successful parse
        response1 = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test.json", json.dumps(valid_catalog_json), "application/json")},
            headers=auth_headers,
        )
        assert response1.status_code == 200
        
        # Second attempt should fail
        response2 = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test2.json", json.dumps(valid_catalog_json), "application/json")},
            headers=auth_headers,
        )
        
        assert response2.status_code == 409
        data = response2.json()
        assert data["error_code"] == "STAGE_ALREADY_COMPLETED"

    def test_parse_catalog_job_in_terminal_state(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
    ) -> None:
        """Test parsing when job is in terminal state."""
        job_id = created_job["job_id"]
        
        # Cancel the job first
        response = client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            headers=auth_headers,
        )
        assert response.status_code == 200
        
        # Now try to parse catalog
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test.json", "{}", "application/json")},
            headers=auth_headers,
        )
        
        assert response.status_code == 412
        data = response.json()
        assert data["error_code"] == "PRECONDITION_FAILED"

    def test_parse_catalog_no_authentication(
        self,
        client: TestClient,
        created_job: Dict[str, Any],
        valid_catalog_json: Dict[str, Any],
    ) -> None:
        """Test parsing without authentication header."""
        job_id = created_job["job_id"]
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test.json", json.dumps(valid_catalog_json), "application/json")},
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "UNAUTHORIZED"

    def test_parse_catalog_invalid_token(
        self,
        client: TestClient,
        created_job: Dict[str, Any],
        valid_catalog_json: Dict[str, Any],
    ) -> None:
        """Test parsing with invalid authentication token."""
        job_id = created_job["job_id"]
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test.json", json.dumps(valid_catalog_json), "application/json")},
            headers={"Authorization": "Bearer invalid-token"},
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "UNAUTHORIZED"

    def test_parse_catalog_invalid_job_id_format(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        valid_catalog_json: Dict[str, Any],
    ) -> None:
        """Test parsing with invalid job ID format."""
        response = client.post(
            "/api/v1/jobs/not-a-uuid/stages/parse-catalog",
            files={"catalog": ("test.json", json.dumps(valid_catalog_json), "application/json")},
            headers=auth_headers,
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"

    def test_parse_catalog_no_file_uploaded(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
    ) -> None:
        """Test parsing without uploading a file."""
        job_id = created_job["job_id"]
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            headers=auth_headers,
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"

    def test_parse_catalog_artifact_storage_verification(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
        valid_catalog_json: Dict[str, Any],
    ) -> None:
        """Test that artifacts are properly stored and can be retrieved."""
        job_id = created_job["job_id"]
        
        # Parse catalog
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test.json", json.dumps(valid_catalog_json), "application/json")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        
        data = response.json()
        catalog_ref = data["artifacts"]["catalog_ref"]
        root_jsons_ref = data["artifacts"]["root_jsons_ref"]
        
        # Verify artifact references
        assert catalog_ref["key"]
        assert catalog_ref["digest"]
        assert catalog_ref["size_bytes"] > 0
        assert catalog_ref["uri"]
        assert catalog_ref["kind"] == "file"
        
        assert root_jsons_ref["key"]
        assert root_jsons_ref["digest"]
        assert root_jsons_ref["size_bytes"] > 0
        assert root_jsons_ref["uri"]
        assert root_jsons_ref["kind"] == "archive"

    def test_parse_catalog_cross_stage_lookup(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
        valid_catalog_json: Dict[str, Any],
    ) -> None:
        """Test that artifacts can be found by cross-stage lookup."""
        job_id = created_job["job_id"]
        
        # Parse catalog
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test.json", json.dumps(valid_catalog_json), "application/json")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        
        # Query artifacts by job and stage
        response = client.get(
            f"/api/v1/jobs/{job_id}/artifacts?stage_name=parse-catalog",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        artifacts = response.json()
        assert len(artifacts) >= 2  # catalog + root-jsons
        
        # Verify specific artifacts
        labels = [artifact["label"] for artifact in artifacts]
        assert "catalog-file" in labels
        assert "root-jsons" in labels

    def test_parse_catalog_error_sanitization(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
    ) -> None:
        """Test that error responses don't expose internal details."""
        job_id = created_job["job_id"]
        
        # Send malformed JSON that would cause internal parsing errors
        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={"catalog": ("test.json", '{"unclosed": "string"', "application/json")},
            headers=auth_headers,
        )
        
        assert response.status_code == 400
        data = response.json()
        
        # Should not expose stack traces or internal paths
        assert "traceback" not in data["message"].lower()
        assert ".py" not in data["message"]
        assert "/" not in data["message"] or data["message"].startswith("/")
        
        # Should include correlation ID
        assert "correlation_id" in data

    def test_parse_catalog_concurrent_requests(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
        valid_catalog_json: Dict[str, Any],
    ) -> None:
        """Test that concurrent requests to the same job are handled correctly."""
        job_id = created_job["job_id"]
        
        import threading
        import time
        
        results = []
        
        def parse_catalog():
            response = client.post(
                f"/api/v1/jobs/{job_id}/stages/parse-catalog",
                files={"catalog": ("test.json", json.dumps(valid_catalog_json), "application/json")},
                headers=auth_headers,
            )
            results.append(response.status_code)
        
        # Start two concurrent requests
        thread1 = threading.Thread(target=parse_catalog)
        thread2 = threading.Thread(target=parse_catalog)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # One should succeed (200), one should fail (409)
        assert 200 in results
        assert 409 in results
        assert len(results) == 2
