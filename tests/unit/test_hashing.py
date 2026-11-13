"""Tests for hashing utilities."""

import pytest

from llmops_governance.utils.hashing import compute_file_hash, sticky_hash


class TestStickyHash:
    """Test deterministic sticky routing hash."""

    def test_deterministic(self):
        """Same input always gives same result."""
        result1 = sticky_hash("user-123", 100)
        result2 = sticky_hash("user-123", 100)
        assert result1 == result2

    def test_different_users_different_buckets(self):
        """Different users should generally map to different buckets."""
        buckets = {sticky_hash(f"user-{i}", 100) for i in range(100)}
        # With 100 users and 100 buckets, we expect significant spread
        assert len(buckets) > 10

    def test_range_valid(self):
        """Result should be in [0, num_buckets)."""
        for i in range(200):
            result = sticky_hash(f"user-{i}", 100)
            assert 0 <= result < 100

    def test_different_bucket_sizes(self):
        """Works with different bucket counts."""
        result = sticky_hash("test-user", 2)
        assert result in (0, 1)

        result = sticky_hash("test-user", 10)
        assert 0 <= result < 10


class TestFileHash:
    """Test file hashing."""

    def test_hash_file(self, tmp_path):
        """Test SHA-256 hash of a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        h = compute_file_hash(str(test_file))
        assert len(h) == 64  # SHA-256 hex digest

    def test_same_content_same_hash(self, tmp_path):
        """Same content produces same hash."""
        f1 = tmp_path / "file1.txt"
        f2 = tmp_path / "file2.txt"
        f1.write_text("identical content")
        f2.write_text("identical content")
        assert compute_file_hash(str(f1)) == compute_file_hash(str(f2))

    def test_different_content_different_hash(self, tmp_path):
        """Different content produces different hash."""
        f1 = tmp_path / "file1.txt"
        f2 = tmp_path / "file2.txt"
        f1.write_text("content A")
        f2.write_text("content B")
        assert compute_file_hash(str(f1)) != compute_file_hash(str(f2))

