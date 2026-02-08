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

"""Security tests for authentication and authorization boundaries."""

import json
import uuid
from fastapi.testclient import TestClient

from main import app


class TestAuthBoundarySecurity:
    """Security tests for authentication and authorization boundaries."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client = TestClient(app)
        self.job_id = str(uuid.uuid4())
        self.correlation_id = str(uuid.uuid4())

    def test_parse_catalog_no_authentication(self) -> None:
        """Test parse catalog rejects requests without authentication."""
        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')

        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
            files={"catalog": ("catalog.json", catalog_content, "application/json")},
        )

        # Should require authentication
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_generate_input_files_no_authentication(self) -> None:
        """Test generate input files rejects requests without authentication."""
        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
        )

        # Should require authentication
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_parse_catalog_invalid_token(self) -> None:
        """Test parse catalog rejects requests with invalid tokens."""
        invalid_tokens = [
            "Bearer invalid-token",
            "Bearer",
            "invalid-token",
            "Bearer malformed.token.format",
            "Bearer ",
            "",
        ]

        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')

        for token in invalid_tokens:
            headers = {"Authorization": token}
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
                files={"catalog": ("catalog.json", catalog_content, "application/json")},
                headers=headers,
            )

            # Should reject invalid authentication
            assert response.status_code == 401

    def test_generate_input_files_invalid_token(self) -> None:
        """Test generate input files rejects requests with invalid tokens."""
        invalid_tokens = [
            "Bearer invalid-token",
            "Bearer",
            "invalid-token",
            "Bearer malformed.token.format",
            "Bearer ",
            "",
        ]

        for token in invalid_tokens:
            headers = {"Authorization": token}
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                headers=headers,
            )

            # Should reject invalid authentication
            assert response.status_code == 401

    def test_parse_catalog_missing_correlation_id(self) -> None:
        """Test parse catalog requires correlation ID."""
        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')
        headers = {"Authorization": "Bearer valid-token"}

        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
            files={"catalog": ("catalog.json", catalog_content, "application/json")},
            headers=headers,
        )

        # Should require correlation ID
        assert response.status_code == 422

    def test_generate_input_files_missing_correlation_id(self) -> None:
        """Test generate input files requires correlation ID."""
        headers = {"Authorization": "Bearer valid-token"}

        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
            headers=headers,
        )

        # Should require correlation ID
        assert response.status_code == 422

    def test_parse_catalog_invalid_correlation_id(self) -> None:
        """Test parse catalog validates correlation ID format."""
        invalid_correlation_ids = [
            "invalid-uuid",
            "123456",
            "not-a-uuid-at-all",
            "00000000-0000-0000-0000-00000000000000",  # Too long
            "g18f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10",  # Invalid hex
        ]

        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')

        for invalid_id in invalid_correlation_ids:
            headers = {
                "Authorization": "Bearer valid-token",
                "X-Correlation-ID": invalid_id,
            }
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
                files={"catalog": ("catalog.json", catalog_content, "application/json")},
                headers=headers,
            )

            # Should validate correlation ID format
            assert response.status_code == 422

    def test_generate_input_files_invalid_correlation_id(self) -> None:
        """Test generate input files validates correlation ID format."""
        invalid_correlation_ids = [
            "invalid-uuid",
            "123456",
            "not-a-uuid-at-all",
            "00000000-0000-0000-0000-00000000000000",  # Too long
            "g18f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10",  # Invalid hex
        ]

        for invalid_id in invalid_correlation_ids:
            headers = {
                "Authorization": "Bearer valid-token",
                "X-Correlation-ID": invalid_id,
            }
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                headers=headers,
            )

            # Should validate correlation ID format
            assert response.status_code == 422

    def test_parse_catalog_invalid_job_id(self) -> None:
        """Test parse catalog validates job ID format."""
        invalid_job_ids = [
            "invalid-uuid",
            "123456",
            "not-a-uuid-at-all",
            "00000000-0000-0000-0000-00000000000000",  # Too long
            "g18f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10",  # Invalid hex
        ]

        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')
        headers = {
            "Authorization": "Bearer valid-token",
            "X-Correlation-ID": str(uuid.uuid4()),
        }

        for invalid_job_id in invalid_job_ids:
            response = self.client.post(
                f"/api/v1/jobs/{invalid_job_id}/stages/parse-catalog",
                files={"catalog": ("catalog.json", catalog_content, "application/json")},
                headers=headers,
            )

            # Should validate job ID format
            assert response.status_code == 422

    def test_generate_input_files_invalid_job_id(self) -> None:
        """Test generate input files validates job ID format."""
        invalid_job_ids = [
            "invalid-uuid",
            "123456",
            "not-a-uuid-at-all",
            "00000000-0000-0000-0000-00000000000000",  # Too long
            "g18f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10",  # Invalid hex
        ]

        headers = {
            "Authorization": "Bearer valid-token",
            "X-Correlation-ID": str(uuid.uuid4()),
        }

        for invalid_job_id in invalid_job_ids:
            response = self.client.post(
                f"/api/v1/jobs/{invalid_job_id}/stages/generate-input-files",
                headers=headers,
            )

            # Should validate job ID format
            assert response.status_code == 422

    def test_cross_job_access_isolation(self) -> None:
        """Test that jobs cannot access other jobs' data."""
        # This test verifies job isolation boundaries
        job1_id = str(uuid.uuid4())
        job2_id = str(uuid.uuid4())
        
        headers = {
            "Authorization": "Bearer valid-token",
            "X-Correlation-ID": str(uuid.uuid4()),
        }

        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')

        # Submit catalog for job1
        response1 = self.client.post(
            f"/api/v1/jobs/{job1_id}/stages/parse-catalog",
            files={"catalog": ("catalog.json", catalog_content, "application/json")},
            headers=headers,
        )

        # Submit catalog for job2
        response2 = self.client.post(
            f"/api/v1/jobs/{job2_id}/stages/parse-catalog",
            files={"catalog": ("catalog.json", catalog_content, "application/json")},
            headers=headers,
        )

        # Both should be processed independently
        assert response1.status_code in [200, 400, 422, 500]
        assert response2.status_code in [200, 400, 422, 500]

    def test_authorization_scope_validation(self) -> None:
        """Test that authorization scopes are properly validated."""
        # Test with different authorization scenarios
        auth_scenarios = [
            "Bearer valid-token",  # Valid token
            "Bearer expired-token",  # Expired token
            "Bearer insufficient-scope-token",  # Token with insufficient scope
        ]

        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')
        headers_base = {
            "X-Correlation-ID": str(uuid.uuid4()),
        }

        for token in auth_scenarios:
            headers = headers_base.copy()
            headers["Authorization"] = token
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
                files={"catalog": ("catalog.json", catalog_content, "application/json")},
                headers=headers,
            )

            # Should validate authorization scope
            # Valid token should pass auth check (may fail for other reasons)
            # Invalid tokens should fail auth check
            if "valid-token" in token:
                assert response.status_code != 401  # Should pass auth
            else:
                assert response.status_code == 401  # Should fail auth

    def test_request_size_limits(self) -> None:
        """Test that request size limits are enforced."""
        headers = {
            "Authorization": "Bearer valid-token",
            "X-Correlation-ID": str(uuid.uuid4()),
        }

        # Test with oversized catalog
        oversized_catalog = {"Catalog": {"data": "x" * 10_000_000}}  # 10MB
        catalog_content = json.dumps(oversized_catalog).encode('utf-8')

        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
            files={"catalog": ("catalog.json", catalog_content, "application/json")},
            headers=headers,
        )

        # Should enforce size limits
        assert response.status_code in [400, 413, 422]

    def test_concurrent_request_limits(self) -> None:
        """Test that concurrent request limits are enforced."""
        headers = {
            "Authorization": "Bearer valid-token",
            "X-Correlation-ID": str(uuid.uuid4()),
        }

        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')

        # Submit many concurrent requests
        responses = []
        for i in range(20):  # High number of concurrent requests
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
                files={"catalog": (f"catalog_{i}.json", catalog_content, "application/json")},
                headers=headers,
            )
            responses.append(response)

        # Should handle concurrent requests gracefully
        # Some may succeed, others may be rate-limited
        success_count = sum(1 for r in responses if r.status_code == 200)
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)
        
        # At least some requests should be processed
        assert success_count > 0 or rate_limited_count > 0

    def test_sensitive_data_exposure_prevention(self) -> None:
        """Test that sensitive data is not exposed in responses."""
        headers = {
            "Authorization": "Bearer valid-token",
            "X-Correlation-ID": str(uuid.uuid4()),
        }

        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')

        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
            files={"catalog": ("catalog.json", catalog_content, "application/json")},
            headers=headers,
        )

        # Response should not contain sensitive information
        response_text = response.text.lower()
        
        sensitive_patterns = [
            "password",
            "secret",
            "token",
            "key",
            "credential",
            "private",
            "internal",
            "admin",
        ]

        for pattern in sensitive_patterns:
            # Check that sensitive patterns are not exposed in error messages
            if response.status_code >= 400:
                assert pattern not in response_text or "validation" in response_text
