"""Tests for src/lola/prompts.py."""

from unittest.mock import MagicMock, patch

from lola.prompts import (
    is_interactive,
    select_assistants,
    select_marketplace,
    select_module,
)


# ---------------------------------------------------------------------------
# is_interactive
# ---------------------------------------------------------------------------


def test_is_interactive_tty(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    assert is_interactive() is True


def test_is_interactive_not_tty(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert is_interactive() is False


# ---------------------------------------------------------------------------
# select_assistants
# ---------------------------------------------------------------------------


def test_select_assistants_single_item_no_prompt():
    """Single-item list should auto-select without prompting."""
    with patch("lola.prompts.inquirer") as mock_inquirer:
        result = select_assistants(["claude-code"])
    mock_inquirer.checkbox.assert_not_called()
    assert result == ["claude-code"]


def test_select_assistants_returns_selection():
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = ["claude-code", "cursor"]
    with patch("lola.prompts.inquirer.checkbox", return_value=mock_prompt):
        result = select_assistants(["claude-code", "cursor", "gemini-cli", "opencode"])
    assert result == ["claude-code", "cursor"]


def test_select_assistants_cancelled_returns_empty():
    """User cancels (execute returns None) → empty list."""
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = None
    with patch("lola.prompts.inquirer.checkbox", return_value=mock_prompt):
        result = select_assistants(["claude-code", "cursor"])
    assert result == []


def test_select_assistants_empty_selection_returns_empty():
    """User confirms with nothing selected → empty list."""
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = []
    with patch("lola.prompts.inquirer.checkbox", return_value=mock_prompt):
        result = select_assistants(["claude-code", "cursor"])
    assert result == []


# ---------------------------------------------------------------------------
# select_module
# ---------------------------------------------------------------------------


def test_select_module_single_item_no_prompt():
    """Single module should be returned without prompting."""
    with patch("lola.prompts.inquirer") as mock_inquirer:
        result = select_module(["my-module"])
    mock_inquirer.select.assert_not_called()
    assert result == "my-module"


def test_select_module_returns_selection():
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = "my-module"
    with patch("lola.prompts.inquirer.select", return_value=mock_prompt):
        result = select_module(["my-module", "other-module"])
    assert result == "my-module"


def test_select_module_cancelled_returns_none():
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = None
    with patch("lola.prompts.inquirer.select", return_value=mock_prompt):
        result = select_module(["my-module", "other-module"])
    assert result is None


# ---------------------------------------------------------------------------
# select_marketplace
# ---------------------------------------------------------------------------


def test_select_marketplace_returns_chosen_name():
    matches = [
        ({"name": "mod", "version": "1.0", "description": "desc a"}, "market-a"),
        ({"name": "mod", "version": "2.0", "description": "desc b"}, "market-b"),
    ]
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = "market-b"
    with patch("lola.prompts.inquirer.select", return_value=mock_prompt) as mock_select:
        result = select_marketplace(matches)

    assert result == "market-b"
    # Verify the choices contain marketplace names as values
    call_kwargs = mock_select.call_args
    choices = call_kwargs[1]["choices"] if call_kwargs[1] else call_kwargs[0][1]
    assert any(c.value == "market-a" for c in choices)
    assert any(c.value == "market-b" for c in choices)


def test_select_marketplace_display_includes_version_and_description():
    """Choice labels must include version and description for US3 acceptance scenario 1."""
    matches = [
        (
            {"name": "mod", "version": "1.2.3", "description": "A great tool"},
            "market-a",
        ),
    ]
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = "market-a"
    with patch("lola.prompts.inquirer.select", return_value=mock_prompt) as mock_select:
        select_marketplace(matches)

    choices = mock_select.call_args[1]["choices"]
    label = choices[0].name
    assert "1.2.3" in label
    assert "A great tool" in label
    assert "market-a" in label


def test_select_marketplace_cancelled_returns_none():
    matches = [
        ({"name": "mod", "version": "1.0", "description": "desc"}, "market-a"),
        ({"name": "mod", "version": "1.0", "description": "desc"}, "market-b"),
    ]
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = None
    with patch("lola.prompts.inquirer.select", return_value=mock_prompt):
        result = select_marketplace(matches)
    assert result is None
