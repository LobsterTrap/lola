"""Tests for src/lola/prompts.py."""

from unittest.mock import MagicMock, patch

from lola.prompts import (
    is_interactive,
    prompt_agent_conflict,
    prompt_command_conflict,
    prompt_skill_conflict,
    select_assistants,
    select_installations,
    select_marketplace,
    select_marketplace_name,
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
# select_installations
# ---------------------------------------------------------------------------


def test_select_installations_returns_selected():
    choices = [
        ("/proj/a", "claude-code", "/proj/a (claude-code)"),
        ("/proj/a", "cursor", "/proj/a (cursor)"),
        ("/proj/b", "claude-code", "/proj/b (claude-code)"),
    ]
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = [
        ("/proj/a", "claude-code", "/proj/a (claude-code)")
    ]
    with patch("lola.prompts.inquirer.checkbox", return_value=mock_prompt):
        result = select_installations(choices)
    assert result == [("/proj/a", "claude-code", "/proj/a (claude-code)")]


def test_select_installations_cancelled_returns_empty():
    choices = [
        ("/proj/a", "claude-code", "/proj/a (claude-code)"),
        ("/proj/b", "cursor", "/proj/b (cursor)"),
    ]
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = None
    with patch("lola.prompts.inquirer.checkbox", return_value=mock_prompt):
        result = select_installations(choices)
    assert result == []


def test_select_installations_empty_selection_returns_empty():
    choices = [
        ("/proj/a", "claude-code", "/proj/a (claude-code)"),
    ]
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = []
    with patch("lola.prompts.inquirer.checkbox", return_value=mock_prompt):
        result = select_installations(choices)
    assert result == []


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


# ---------------------------------------------------------------------------
# select_marketplace_name
# ---------------------------------------------------------------------------


def test_select_marketplace_name_single_item_still_prompts():
    """Single marketplace must still show the picker (destructive-action safety)."""
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = "official"
    with patch("lola.prompts.inquirer.select", return_value=mock_prompt) as mock_select:
        result = select_marketplace_name(["official"])
    mock_select.assert_called_once()
    assert result == "official"


def test_select_marketplace_name_returns_selection():
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = "community"
    with patch("lola.prompts.inquirer.select", return_value=mock_prompt):
        result = select_marketplace_name(["official", "community"])
    assert result == "community"


def test_select_marketplace_name_cancelled_returns_none():
    mock_prompt = MagicMock()
    mock_prompt.execute.return_value = None
    with patch("lola.prompts.inquirer.select", return_value=mock_prompt):
        result = select_marketplace_name(["official", "community"])
    assert result is None


# ---------------------------------------------------------------------------
# conflict prompts (skill / command / agent)
# ---------------------------------------------------------------------------


def _make_inquirer_chain(action_value, rename_value=None):
    """Build a side_effect list for `inquirer.select` then `inquirer.text`."""
    select_mock = MagicMock()
    select_mock.execute.return_value = action_value
    text_mock = MagicMock()
    text_mock.execute.return_value = rename_value
    return select_mock, text_mock


def test_prompt_skill_conflict_overwrite_all():
    select_mock, _ = _make_inquirer_chain("overwrite_all")
    with patch("lola.prompts.inquirer.select", return_value=select_mock):
        action, new_name = prompt_skill_conflict("foo", "mod")
    assert action == "overwrite_all"
    assert new_name == ""


def test_prompt_skill_conflict_rename_uses_underscore_default():
    """Skill rename default is ``module_skill`` (underscore separator)."""
    select_mock, text_mock = _make_inquirer_chain("rename", "mod_foo")
    with (
        patch("lola.prompts.inquirer.select", return_value=select_mock),
        patch("lola.prompts.inquirer.text", return_value=text_mock) as mock_text,
    ):
        action, new_name = prompt_skill_conflict("foo", "mod")
    assert action == "rename"
    assert new_name == "mod_foo"
    # The default passed to inquirer.text should use underscore.
    assert mock_text.call_args.kwargs["default"] == "mod_foo"


def test_prompt_skill_conflict_prefix_all_prompts_for_prefix():
    """Selecting "Prefix All" asks the user for a prefix (defaulting to the
    module name) and returns it; the caller then constructs the final names."""
    select_mock, text_mock = _make_inquirer_chain("prefix_all", "myprefix")
    with (
        patch("lola.prompts.inquirer.select", return_value=select_mock),
        patch("lola.prompts.inquirer.text", return_value=text_mock) as mock_text,
    ):
        action, prefix = prompt_skill_conflict("foo", "mod")
    assert action == "prefix_all"
    assert prefix == "myprefix"
    # Default for the prefix input must be the module name.
    assert mock_text.call_args.kwargs["default"] == "mod"


def test_prompt_command_conflict_prefix_all_prompts_for_prefix():
    """Commands also prompt for the prefix; default is the module name."""
    select_mock, text_mock = _make_inquirer_chain("prefix_all", "myprefix")
    with (
        patch("lola.prompts.inquirer.select", return_value=select_mock),
        patch("lola.prompts.inquirer.text", return_value=text_mock) as mock_text,
    ):
        action, prefix = prompt_command_conflict("foo", "mod")
    assert action == "prefix_all"
    assert prefix == "myprefix"
    assert mock_text.call_args.kwargs["default"] == "mod"


def test_prompt_agent_conflict_prefix_all_prompts_for_prefix():
    """Agents also prompt for the prefix; default is the module name."""
    select_mock, text_mock = _make_inquirer_chain("prefix_all", "myprefix")
    with (
        patch("lola.prompts.inquirer.select", return_value=select_mock),
        patch("lola.prompts.inquirer.text", return_value=text_mock) as mock_text,
    ):
        action, prefix = prompt_agent_conflict("foo", "mod")
    assert action == "prefix_all"
    assert prefix == "myprefix"
    assert mock_text.call_args.kwargs["default"] == "mod"


def test_prompt_conflict_offers_prefix_all_below_overwrite_all():
    """The "Prefix All" choice must appear directly below "Overwrite All"."""
    select_mock, _ = _make_inquirer_chain("skip")
    with patch("lola.prompts.inquirer.select", return_value=select_mock) as mock_select:
        prompt_skill_conflict("foo", "mod")
    choice_values = [c.value for c in mock_select.call_args.kwargs["choices"]]
    assert choice_values[:2] == ["overwrite_all", "prefix_all"]


def test_prompt_command_conflict_offers_overwrite_all():
    select_mock, _ = _make_inquirer_chain("overwrite_all")
    with patch("lola.prompts.inquirer.select", return_value=select_mock) as mock_select:
        action, _ = prompt_command_conflict("foo", "mod")
    assert action == "overwrite_all"
    choice_values = [c.value for c in mock_select.call_args.kwargs["choices"]]
    assert "overwrite_all" in choice_values


def test_prompt_agent_conflict_offers_overwrite_all():
    select_mock, _ = _make_inquirer_chain("overwrite_all")
    with patch("lola.prompts.inquirer.select", return_value=select_mock) as mock_select:
        action, _ = prompt_agent_conflict("foo", "mod")
    assert action == "overwrite_all"
    choice_values = [c.value for c in mock_select.call_args.kwargs["choices"]]
    assert "overwrite_all" in choice_values
