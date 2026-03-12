"""Tests for commit hash detection in parsers."""

from lola.parsers import GitSourceHandler


class TestGitSourceHandlerCommitDetection:
    """Tests for commit hash detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = GitSourceHandler()

    def test_is_commit_hash_short(self):
        """Test detection of short commit hashes (7-12 chars)."""
        assert self.handler._is_commit_hash("abc1234") is True
        assert self.handler._is_commit_hash("1234567") is True
        assert self.handler._is_commit_hash("abcdef123456") is True

    def test_is_commit_hash_full(self):
        """Test detection of full commit hashes (40 chars)."""
        assert (
            self.handler._is_commit_hash("1234567890abcdef1234567890abcdef12345678")
            is True
        )
        assert (
            self.handler._is_commit_hash("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            is True
        )

    def test_is_commit_hash_case_insensitive(self):
        """Test that hash detection is case-insensitive."""
        assert self.handler._is_commit_hash("ABCDEF1") is True
        assert self.handler._is_commit_hash("AbCdEf123") is True

    def test_is_not_commit_hash_branch_names(self):
        """Test that branch names are not detected as commit hashes."""
        assert self.handler._is_commit_hash("main") is False
        assert self.handler._is_commit_hash("develop") is False
        assert self.handler._is_commit_hash("feature/new-stuff") is False
        assert self.handler._is_commit_hash("release-1.0") is False

    def test_is_not_commit_hash_tag_names(self):
        """Test that tag names are not detected as commit hashes."""
        assert self.handler._is_commit_hash("v1.0.0") is False
        assert self.handler._is_commit_hash("v2.1.0") is False
        assert self.handler._is_commit_hash("release-2.0") is False

    def test_is_not_commit_hash_too_short(self):
        """Test that refs shorter than 7 chars are not commit hashes."""
        assert self.handler._is_commit_hash("abc") is False
        assert self.handler._is_commit_hash("123456") is False
        assert self.handler._is_commit_hash("") is False

    def test_is_not_commit_hash_non_hex(self):
        """Test that refs with non-hex characters are not commit hashes."""
        assert self.handler._is_commit_hash("abcdefg123") is False  # 'g' not hex
        assert self.handler._is_commit_hash("xyz1234567") is False  # 'xyz' not hex
        assert self.handler._is_commit_hash("main-branch") is False  # has '-'
