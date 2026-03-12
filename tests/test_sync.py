"""Tests for sync module parsing logic."""

import pytest

from lola.sync import (
    ModuleSpec,
    parse_lolareq_line,
    load_lolareq,
    convert_tilde_spec,
    convert_caret_spec,
)


class TestParseLolareqLine:
    """Tests for parse_lolareq_line function."""

    def test_parse_simple_module(self):
        """Test parsing a simple module name."""
        spec = parse_lolareq_line("my-skill", 1)
        assert spec is not None
        assert spec.module_ref == "my-skill"
        assert spec.version_spec is None
        assert spec.assistant is None

    def test_parse_version_exact(self):
        """Test parsing module with exact version."""
        spec = parse_lolareq_line("my-skill==1.2.0", 1)
        assert spec is not None
        assert spec.module_ref == "my-skill"
        assert spec.version_spec == "==1.2.0"
        assert spec.assistant is None

    def test_parse_version_gte(self):
        """Test parsing module with >= version."""
        spec = parse_lolareq_line("my-skill>=1.0.0", 1)
        assert spec is not None
        assert spec.module_ref == "my-skill"
        assert spec.version_spec == ">=1.0.0"

    def test_parse_version_tilde(self):
        """Test parsing module with ~ version."""
        spec = parse_lolareq_line("my-skill~1.2", 1)
        assert spec is not None
        assert spec.module_ref == "my-skill"
        # Should be converted to >=1.2,<1.3
        assert spec.version_spec is not None
        assert ">=1.2" in spec.version_spec
        assert "<1.3" in spec.version_spec

    def test_parse_version_caret(self):
        """Test parsing module with ^ version."""
        spec = parse_lolareq_line("my-skill^1.2", 1)
        assert spec is not None
        assert spec.module_ref == "my-skill"
        # Should be converted to >=1.2,<2.0
        assert spec.version_spec is not None
        assert ">=1.2" in spec.version_spec
        assert "<2" in spec.version_spec

    def test_parse_with_assistant(self):
        """Test parsing module with assistant specification."""
        spec = parse_lolareq_line("my-skill>>claude-code", 1)
        assert spec is not None
        assert spec.module_ref == "my-skill"
        assert spec.assistant == "claude-code"

    def test_parse_with_assistant_space(self):
        """Test parsing module with assistant specification (with space)."""
        spec = parse_lolareq_line("my-skill>> claude-code", 1)
        assert spec is not None
        assert spec.module_ref == "my-skill"
        assert spec.assistant == "claude-code"

    def test_parse_version_and_assistant(self):
        """Test parsing module with version and assistant."""
        spec = parse_lolareq_line("my-skill>=1.0.0>>cursor", 1)
        assert spec is not None
        assert spec.module_ref == "my-skill"
        assert spec.version_spec == ">=1.0.0"
        assert spec.assistant == "cursor"

    def test_parse_marketplace_ref(self):
        """Test parsing marketplace reference."""
        spec = parse_lolareq_line("@official/python-tools", 1)
        assert spec is not None
        assert spec.module_ref == "@official/python-tools"

    def test_parse_marketplace_with_version(self):
        """Test parsing marketplace reference with version."""
        spec = parse_lolareq_line("@official/python-tools~1.2", 1)
        assert spec is not None
        assert spec.module_ref == "@official/python-tools"
        assert spec.version_spec is not None

    def test_parse_url(self):
        """Test parsing git URL."""
        spec = parse_lolareq_line("https://github.com/user/repo.git", 1)
        assert spec is not None
        assert spec.module_ref == "https://github.com/user/repo.git"

    def test_parse_url_with_assistant(self):
        """Test parsing git URL with assistant."""
        spec = parse_lolareq_line("https://github.com/user/repo.git>>claude-code", 1)
        assert spec is not None
        assert spec.module_ref == "https://github.com/user/repo.git"
        assert spec.assistant == "claude-code"

    def test_parse_git_plus_https_url(self):
        """Test parsing git+https:// URL."""
        spec = parse_lolareq_line("git+https://github.com/user/repo.git", 1)
        assert spec is not None
        assert spec.module_ref == "git+https://github.com/user/repo.git"

    def test_parse_git_plus_http_url(self):
        """Test parsing git+http:// URL."""
        spec = parse_lolareq_line("git+http://example.com/repo.git", 1)
        assert spec is not None
        assert spec.module_ref == "git+http://example.com/repo.git"

    def test_parse_git_plus_ssh_url(self):
        """Test parsing git+ssh:// URL."""
        spec = parse_lolareq_line("git+ssh://git@github.com/user/repo.git", 1)
        assert spec is not None
        assert spec.module_ref == "git+ssh://git@github.com/user/repo.git"

    def test_parse_git_plus_url_with_assistant(self):
        """Test parsing git+ URL with assistant."""
        spec = parse_lolareq_line("git+https://github.com/user/repo.git>>cursor", 1)
        assert spec is not None
        assert spec.module_ref == "git+https://github.com/user/repo.git"
        assert spec.assistant == "cursor"

    def test_parse_url_with_ref(self):
        """Test parsing URL with @ref (branch/tag)."""
        spec = parse_lolareq_line("https://github.com/user/repo.git@v1.0.0", 1)
        assert spec is not None
        assert spec.module_ref == "https://github.com/user/repo.git@v1.0.0"

    def test_parse_git_plus_url_with_ref(self):
        """Test parsing git+ URL with @ref."""
        spec = parse_lolareq_line("git+https://github.com/user/repo.git@main", 1)
        assert spec is not None
        assert spec.module_ref == "git+https://github.com/user/repo.git@main"

    def test_parse_url_with_ref_and_assistant(self):
        """Test parsing URL with @ref and assistant."""
        spec = parse_lolareq_line(
            "https://github.com/user/repo.git@develop>>claude-code", 1
        )
        assert spec is not None
        assert spec.module_ref == "https://github.com/user/repo.git@develop"
        assert spec.assistant == "claude-code"

    def test_parse_url_with_commit_hash(self):
        """Test parsing URL with commit hash."""
        spec = parse_lolareq_line("https://github.com/user/repo.git@abc123def", 1)
        assert spec is not None
        assert spec.module_ref == "https://github.com/user/repo.git@abc123def"

    def test_parse_url_with_full_commit_hash(self):
        """Test parsing URL with full 40-char commit hash."""
        spec = parse_lolareq_line(
            "https://github.com/user/repo.git@1234567890abcdef1234567890abcdef12345678",
            1,
        )
        assert spec is not None
        assert (
            spec.module_ref
            == "https://github.com/user/repo.git@1234567890abcdef1234567890abcdef12345678"
        )

    def test_parse_git_plus_url_with_commit_hash(self):
        """Test parsing git+ URL with commit hash."""
        spec = parse_lolareq_line("git+https://github.com/user/repo.git@abc1234", 1)
        assert spec is not None
        assert spec.module_ref == "git+https://github.com/user/repo.git@abc1234"

    def test_parse_blank_line(self):
        """Test that blank lines return None."""
        assert parse_lolareq_line("", 1) is None
        assert parse_lolareq_line("   ", 1) is None

    def test_parse_comment(self):
        """Test that comments return None."""
        assert parse_lolareq_line("# This is a comment", 1) is None

    def test_parse_empty_module_ref(self):
        """Test that empty module ref raises error."""
        with pytest.raises(ValueError, match="Empty module reference"):
            parse_lolareq_line(">>claude-code", 1)


class TestModuleSpec:
    """Tests for ModuleSpec dataclass."""

    def test_module_name_only(self):
        """Test extracting module name without version."""
        spec = ModuleSpec(
            raw_line="my-skill>=1.0.0",
            module_ref="my-skill",
            version_spec=">=1.0.0",
        )
        assert spec.module_name_only == "my-skill"

    def test_matches_version_no_constraint(self):
        """Test version matching with no constraint."""
        spec = ModuleSpec(
            raw_line="my-skill",
            module_ref="my-skill",
        )
        assert spec.matches_version("1.0.0") is True
        assert spec.matches_version("2.5.3") is True

    def test_matches_version_exact(self):
        """Test version matching with exact constraint."""
        spec = ModuleSpec(
            raw_line="my-skill==1.2.0",
            module_ref="my-skill",
            version_spec="==1.2.0",
        )
        assert spec.matches_version("1.2.0") is True
        assert spec.matches_version("1.2.1") is False
        assert spec.matches_version("1.1.0") is False

    def test_matches_version_gte(self):
        """Test version matching with >= constraint."""
        spec = ModuleSpec(
            raw_line="my-skill>=1.0.0",
            module_ref="my-skill",
            version_spec=">=1.0.0",
        )
        assert spec.matches_version("1.0.0") is True
        assert spec.matches_version("1.2.0") is True
        assert spec.matches_version("2.0.0") is True
        assert spec.matches_version("0.9.0") is False

    def test_matches_version_range(self):
        """Test version matching with range constraint."""
        spec = ModuleSpec(
            raw_line="my-skill>=1.0.0,<2.0.0",
            module_ref="my-skill",
            version_spec=">=1.0.0,<2.0.0",
        )
        assert spec.matches_version("1.0.0") is True
        assert spec.matches_version("1.5.0") is True
        assert spec.matches_version("2.0.0") is False
        assert spec.matches_version("0.9.0") is False


class TestConvertVersionSpecs:
    """Tests for version spec conversion functions."""

    def test_convert_tilde_major_minor(self):
        """Test tilde conversion with major.minor."""
        result = convert_tilde_spec("1.2")
        assert ">=1.2" in result
        assert "<1.3" in result

    def test_convert_tilde_full(self):
        """Test tilde conversion with full version."""
        result = convert_tilde_spec("1.2.3")
        assert ">=1.2.3" in result
        assert "<1.3" in result

    def test_convert_caret_normal(self):
        """Test caret conversion for 1.x and above."""
        result = convert_caret_spec("1.2")
        assert ">=1.2" in result
        assert "<2" in result

    def test_convert_caret_zero_major(self):
        """Test caret conversion for 0.x versions."""
        result = convert_caret_spec("0.2.3")
        assert ">=0.2.3" in result
        assert "<0.3" in result

    def test_convert_caret_full(self):
        """Test caret conversion with full version."""
        result = convert_caret_spec("2.5.1")
        assert ">=2.5.1" in result
        assert "<3" in result


class TestLoadLolareq:
    """Tests for load_lolareq function."""

    def test_load_simple_file(self, tmp_path):
        """Test loading a simple .lola-req."""
        lolareq = tmp_path / ".lola-req"
        lolareq.write_text("my-skill\nanother-skill>=1.0.0\n")

        specs = load_lolareq(lolareq)
        assert len(specs) == 2
        assert specs[0].module_ref == "my-skill"
        assert specs[1].module_ref == "another-skill"
        assert specs[1].version_spec == ">=1.0.0"

    def test_load_with_comments_and_blanks(self, tmp_path):
        """Test loading file with comments and blank lines."""
        lolareq = tmp_path / ".lola-req"
        lolareq.write_text(
            """
# This is a comment
my-skill

# Another comment
another-skill>=1.0.0
"""
        )

        specs = load_lolareq(lolareq)
        assert len(specs) == 2
        assert specs[0].module_ref == "my-skill"
        assert specs[1].module_ref == "another-skill"

    def test_load_with_assistants(self, tmp_path):
        """Test loading file with assistant specifications."""
        lolareq = tmp_path / ".lola-req"
        lolareq.write_text(
            """
skill1>>claude-code
skill2>> cursor
skill3
"""
        )

        specs = load_lolareq(lolareq)
        assert len(specs) == 3
        assert specs[0].assistant == "claude-code"
        assert specs[1].assistant == "cursor"
        assert specs[2].assistant is None

    def test_load_missing_file(self, tmp_path):
        """Test loading non-existent file raises error."""
        lolareq = tmp_path / ".lola-req"

        with pytest.raises(FileNotFoundError):
            load_lolareq(lolareq)

    def test_load_invalid_line(self, tmp_path):
        """Test that invalid line raises error."""
        lolareq = tmp_path / ".lola-req"
        lolareq.write_text("my-skill\n>>claude-code\n")

        with pytest.raises(ValueError, match="Empty module reference"):
            load_lolareq(lolareq)
