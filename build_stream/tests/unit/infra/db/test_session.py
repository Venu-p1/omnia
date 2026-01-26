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

"""Unit tests for database session management."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add build_stream directory to path for imports
build_stream_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(build_stream_dir))

from build_stream.infra.db.session import get_db_session


class TestGetDbSession:
    """Tests for get_db_session context manager."""
    
    @patch("build_stream.infra.db.session.SessionLocal")
    def test_yields_session(self, mock_session_local):
        """Test context manager yields a session."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        with get_db_session() as session:
            assert session is mock_session
    
    @patch("build_stream.infra.db.session.SessionLocal")
    def test_commits_on_success(self, mock_session_local):
        """Test session commits when no exception occurs."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        with get_db_session() as session:
            pass
        
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()
    
    @patch("build_stream.infra.db.session.SessionLocal")
    def test_rollback_on_exception(self, mock_session_local):
        """Test session rolls back when exception occurs."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        with pytest.raises(ValueError):
            with get_db_session() as session:
                raise ValueError("Test error")
        
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()
    
    @patch("build_stream.infra.db.session.SessionLocal")
    def test_closes_session_even_on_exception(self, mock_session_local):
        """Test session is closed even when exception occurs."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        with pytest.raises(RuntimeError):
            with get_db_session() as session:
                raise RuntimeError("Test error")
        
        mock_session.close.assert_called_once()
    
    @patch("build_stream.infra.db.session.SessionLocal")
    def test_multiple_operations_in_session(self, mock_session_local):
        """Test multiple operations can be performed in a single session."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        with get_db_session() as session:
            session.add(MagicMock())
            session.add(MagicMock())
            session.flush()
        
        assert mock_session.add.call_count == 2
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


class TestGetDb:
    """Tests for get_db FastAPI dependency."""
    
    @patch("build_stream.infra.db.session.SessionLocal")
    def test_get_db_is_generator(self, mock_session_local):
        """Test get_db returns a generator."""
        from build_stream.infra.db.session import get_db
        
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        gen = get_db()
        assert hasattr(gen, "__next__")
    
    @patch("build_stream.infra.db.session.SessionLocal")
    def test_get_db_yields_session(self, mock_session_local):
        """Test get_db yields a session."""
        from build_stream.infra.db.session import get_db
        
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        gen = get_db()
        session = next(gen)
        
        assert session is mock_session
    
    @patch("build_stream.infra.db.session.SessionLocal")
    def test_get_db_closes_session_after_yield(self, mock_session_local):
        """Test get_db closes session after yield completes."""
        from build_stream.infra.db.session import get_db
        
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        gen = get_db()
        session = next(gen)
        
        try:
            next(gen)
        except StopIteration:
            pass
        
        mock_session.close.assert_called_once()
    
    @patch("build_stream.infra.db.session.SessionLocal")
    def test_get_db_closes_session_on_exception(self, mock_session_local):
        """Test get_db closes session even when exception occurs."""
        from build_stream.infra.db.session import get_db
        
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        gen = get_db()
        session = next(gen)
        
        try:
            gen.throw(RuntimeError("Test error"))
        except RuntimeError:
            pass
        
        mock_session.close.assert_called_once()
