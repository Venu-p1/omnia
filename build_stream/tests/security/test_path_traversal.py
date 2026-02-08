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

"""Security tests for path traversal vulnerabilities."""

import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app


class TestPathTraversalSecurity:
    """Security tests for path traversal attack prevention."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client = TestClient(app)
        self.job_id = str(uuid.uuid4())
        self.correlation_id = str(uuid.uuid4())
        self.headers = {
            "Authorization": "Bearer valid-test-token",
            "X-Correlation-ID": self.correlation_id,
        }

    def test_parse_catalog_filename_path_traversal(self) -> None:
        """Test parse catalog prevents path traversal in filename."""
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "~/.ssh/id_rsa",
            "/proc/version",
            "../etc/shadow",
        ]

        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')

        for malicious_filename in malicious_filenames:
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
                files={"catalog": (malicious_filename, catalog_content, "application/json")},
                headers=self.headers,
            )

            # Should reject path traversal attempts
            assert response.status_code in [400, 422]
            
            # Response should not contain the malicious path
            response_text = response.text.lower()
            assert "etc/passwd" not in response_text
            assert "windows" not in response_text

    def test_generate_input_files_adapter_policy_path_traversal(self) -> None:
        """Test generate input files prevents path traversal in adapter policy path."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "~/.ssh/id_rsa",
            "/proc/version",
            "../etc/shadow",
            "/dev/null",
            "/proc/self/environ",
        ]

        for malicious_path in malicious_paths:
            request_data = {"adapter_policy_path": malicious_path}
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                json=request_data,
                headers=self.headers,
            )

            # Should reject path traversal attempts
            assert response.status_code in [400, 422]
            
            # Response should not contain the malicious path
            response_text = response.text.lower()
            assert "etc/passwd" not in response_text
            assert "windows" not in response_text

    def test_artifact_key_path_traversal(self) -> None:
        """Test artifact key validation prevents path traversal."""
        from core.artifacts.value_objects import ArtifactKey
        
        malicious_keys = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "~/.ssh/id_rsa",
            "../etc/shadow",
            "catalog/../../../etc/passwd",
            "input\\..\\..\\etc\\passwd",
        ]

        for malicious_key in malicious_keys:
            with pytest.raises(ValueError, match="traversal|absolute"):
                ArtifactKey(malicious_key)

    def test_safe_path_path_traversal(self) -> None:
        """Test SafePath validation prevents path traversal."""
        from core.artifacts.value_objects import SafePath
        from pathlib import Path
        
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "~/.ssh/id_rsa",
            "../etc/shadow",
        ]

        for malicious_path in malicious_paths:
            with pytest.raises(ValueError, match="traversal"):
                SafePath.from_string(malicious_path)
            
            with pytest.raises(ValueError, match="traversal"):
                SafePath(value=Path(malicious_path))

    def test_null_byte_injection(self) -> None:
        """Test prevention of null byte injection attacks."""
        malicious_inputs = [
            "catalog.json\x00.txt",
            "policy.json\x00\x00\x00",
            "/etc/passwd\x00.json",
            "safe.txt\x00../../../etc/passwd",
        ]

        # Test in parse catalog filename
        catalog_content = json.dumps({"Catalog": {"Name": "Test"}}).encode('utf-8')
        
        for malicious_filename in malicious_inputs:
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/parse-catalog",
                files={"catalog": (malicious_filename, catalog_content, "application/json")},
                headers=self.headers,
            )

            # Should reject null byte injection
            assert response.status_code in [400, 422]

        # Test in generate input files policy path
        for malicious_path in malicious_inputs:
            request_data = {"adapter_policy_path": malicious_path}
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                json=request_data,
                headers=self.headers,
            )

            # Should reject null byte injection
            assert response.status_code in [400, 422]

    def test_url_encoded_path_traversal(self) -> None:
        """Test prevention of URL-encoded path traversal."""
        encoded_paths = [
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # ../../../etc/passwd
            "%2e%2e%5c%2e%2e%5c%2e%2e%5cwindows%5csystem32",  # ..\..\..\windows\system32
            "%2f%65%74%63%2f%70%61%73%73%77%64",  # /etc/passwd
        ]

        for encoded_path in encoded_paths:
            # Test in generate input files
            request_data = {"adapter_policy_path": encoded_path}
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                json=request_data,
                headers=self.headers,
            )

            # Should reject encoded path traversal
            assert response.status_code in [400, 422]

    def test_unicode_path_traversal(self) -> None:
        """Test prevention of Unicode-based path traversal."""
        unicode_paths = [
            "‮../../../etc/passwd",  # Right-to-left override
            "⁦../../../etc/passwd",   # Left-to-right override
            "⁨../../../etc/passwd",  # Pop direction formatting
            "⁩../../../etc/passwd",  # Left-to-right isolate
        ]

        for unicode_path in unicode_paths:
            # Test in generate input files
            request_data = {"adapter_policy_path": unicode_path}
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                json=request_data,
                headers=self.headers,
            )

            # Should reject Unicode-based attacks
            assert response.status_code in [400, 422]

    def test_long_path_traversal(self) -> None:
        """Test prevention of long path traversal attacks."""
        # Create a very long path with traversal sequences
        long_traversal = "../" * 1000 + "etc/passwd"
        
        # Test in generate input files
        request_data = {"adapter_policy_path": long_traversal}
        
        response = self.client.post(
            f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
            json=request_data,
            headers=self.headers,
        )

        # Should reject long traversal paths
        assert response.status_code in [400, 422]

    def test_canonicalization_attacks(self) -> None:
        """Test prevention of path canonicalization attacks."""
        canonicalization_paths = [
            "./././../../../etc/passwd",
            "foo/bar/../../../etc/passwd",
            "a/b/c/../../../../../../etc/passwd",
            "current/./../other/../etc/passwd",
        ]

        for path in canonicalization_paths:
            # Test in generate input files
            request_data = {"adapter_policy_path": path}
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                json=request_data,
                headers=self.headers,
            )

            # Should reject canonicalization attacks
            assert response.status_code in [400, 422]

    def test_symlink_attacks(self) -> None:
        """Test prevention of symlink-based attacks."""
        symlink_paths = [
            "/tmp/symlink_to_etc_passwd",
            "/var/www/uploads/link_to_sensitive",
            "/dev/shm/suspicious_link",
        ]

        for symlink_path in symlink_paths:
            # Test in generate input files
            request_data = {"adapter_policy_path": symlink_path}
            
            response = self.client.post(
                f"/api/v1/jobs/{self.job_id}/stages/generate-input-files",
                json=request_data,
                headers=self.headers,
            )

            # Should be cautious about potential symlink attacks
            assert response.status_code in [400, 422, 500]  # May be rejected or handled safely
