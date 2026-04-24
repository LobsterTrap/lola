"""Tests for --scope option in install command."""

from click.testing import CliRunner

from lola.cli.install import install_cmd


def test_install_user_scope_with_explicit_path_fails():
    """User scope with explicit project path should fail."""
    runner = CliRunner()
    result = runner.invoke(
        install_cmd,
        ["test-module", "--scope", "user", "/some/path"],
    )
    assert result.exit_code == 1
    assert "cannot be used with a project path argument" in result.output


def test_install_user_scope_without_path_succeeds(
    mock_lola_home, registered_module, monkeypatch
):
    """User scope without explicit path should succeed."""
    # Set HOME to a temp path to avoid polluting real home
    monkeypatch.setenv("HOME", str(mock_lola_home["home"].parent / "fakehome"))

    runner = CliRunner()
    result = runner.invoke(
        install_cmd,
        ["sample-module", "--scope", "user", "-a", "claude-code"],
        catch_exceptions=False,
    )

    # Should succeed - validation passes for user scope without explicit path
    assert result.exit_code == 0
    # Should show success message
    assert "Installed to" in result.output
