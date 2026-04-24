"""Tests for _validate_installation_for_update with user scope."""

from lola.cli.install import _validate_installation_for_update
from lola.models import Installation


def test_validate_user_scope_installation_no_project_path_check(
    mock_lola_home, registered_module
):
    """User scope installations should not validate project_path."""
    inst = Installation(
        module_name="sample-module",
        assistant="claude-code",
        scope="user",
        project_path=None,
        skills=["skill1"],
    )

    is_valid, error_msg = _validate_installation_for_update(inst)

    # Should not fail on missing project path for user scope
    assert is_valid, f"User scope validation should pass but got: {error_msg}"
    assert error_msg is None


def test_validate_project_scope_installation_requires_project_path():
    """Project scope installations should validate project_path exists."""
    inst = Installation(
        module_name="test-module",
        assistant="claude-code",
        scope="project",
        project_path="/nonexistent/path",
        skills=["skill1"],
    )

    is_valid, error_msg = _validate_installation_for_update(inst)

    assert not is_valid
    assert error_msg == "project path no longer exists"
