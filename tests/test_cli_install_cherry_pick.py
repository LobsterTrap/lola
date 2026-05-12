"""Tests for cherry-pick install (issue #119): --skill/--command/--agent/--mcp
flags, the interactive picker, and lock-to-original-selection on update.
"""

from __future__ import annotations

import json
import shutil
from unittest.mock import patch

from lola.cli.install import _expand_csv, install_cmd, update_cmd
from lola.models import Installation, InstallationRegistry
from lola.prompts import select_install_mode, select_module_items


class TestExpandCsv:
    def test_empty_tuple(self):
        assert _expand_csv(()) == []

    def test_single_value(self):
        assert _expand_csv(("foo",)) == ["foo"]

    def test_multiple_repeats(self):
        assert _expand_csv(("foo", "bar")) == ["foo", "bar"]

    def test_comma_separated(self):
        assert _expand_csv(("foo,bar,baz",)) == ["foo", "bar", "baz"]

    def test_mixed_repeats_and_comma(self):
        assert _expand_csv(("foo,bar", "baz")) == ["foo", "bar", "baz"]

    def test_strips_whitespace_and_drops_empty(self):
        assert _expand_csv(("  foo , , bar ",)) == ["foo", "bar"]


class TestSelectModuleItems:
    def test_install_mode_all(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = "all"
        with patch("lola.prompts.inquirer.select", return_value=mock_prompt):
            result = select_install_mode()

        assert result == "all"

    def test_install_mode_cherry_pick(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = "cherry-pick"
        with patch("lola.prompts.inquirer.select", return_value=mock_prompt):
            result = select_install_mode()

        assert result == "cherry-pick"

    def test_install_mode_cancel_returns_none(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = None
        with patch("lola.prompts.inquirer.select", return_value=mock_prompt):
            result = select_install_mode()

        assert result is None

    def test_alt_a_select_all_returns_full_lists(self):
        """After Alt-A toggles everything on, the prompt returns every value."""
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = [
            "skill:foo",
            "skill:bar",
            "cmd:c1",
            "agent:a1",
            "mcp:m1",
        ]
        with patch("lola.prompts.inquirer.fuzzy", return_value=mock_prompt):
            result = select_module_items(
                skills=["foo", "bar"],
                commands=["c1"],
                agents=["a1"],
                mcps=["m1"],
            )
        assert result == {
            "skills": ["foo", "bar"],
            "commands": ["c1"],
            "agents": ["a1"],
            "mcps": ["m1"],
            "instructions": [],
        }

    def test_subset_selection(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = ["skill:foo", "cmd:c1"]
        with patch("lola.prompts.inquirer.fuzzy", return_value=mock_prompt):
            result = select_module_items(
                skills=["foo", "bar"],
                commands=["c1", "c2"],
                agents=["a1"],
                mcps=[],
            )
        assert result == {
            "skills": ["foo"],
            "commands": ["c1"],
            "agents": [],
            "mcps": [],
            "instructions": [],
        }

    def test_cancel_returns_none(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = None
        with patch("lola.prompts.inquirer.fuzzy", return_value=mock_prompt):
            result = select_module_items(
                skills=["foo"], commands=[], agents=[], mcps=[]
            )
        assert result is None

    def test_empty_selection_returns_empty_items(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = []
        with patch("lola.prompts.inquirer.fuzzy", return_value=mock_prompt):
            result = select_module_items(
                skills=["foo"],
                commands=["c1"],
                agents=["a1"],
                mcps=["m1"],
            )

        assert result == {
            "skills": [],
            "commands": [],
            "agents": [],
            "mcps": [],
            "instructions": [],
        }

    def test_picker_includes_instructions_when_module_has_them(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = []
        with patch(
            "lola.prompts.inquirer.fuzzy", return_value=mock_prompt
        ) as mock_fuzzy:
            select_module_items(
                skills=["foo"],
                commands=[],
                agents=[],
                mcps=[],
                has_instructions=True,
            )
        choices = mock_fuzzy.call_args.kwargs["choices"]
        values = [c.value for c in choices]
        assert "instructions:" in values
        instr_choice = next(c for c in choices if c.value == "instructions:")
        assert instr_choice.name.startswith("instructions: AGENTS.md")

    def test_picker_omits_instructions_when_module_has_none(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = []
        with patch(
            "lola.prompts.inquirer.fuzzy", return_value=mock_prompt
        ) as mock_fuzzy:
            select_module_items(
                skills=["foo"],
                commands=[],
                agents=[],
                mcps=[],
                has_instructions=False,
            )
        choices = mock_fuzzy.call_args.kwargs["choices"]
        assert all(c.value != "instructions:" for c in choices)

    def test_picker_instructions_pre_selected_when_current_has_them(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = []
        with patch(
            "lola.prompts.inquirer.fuzzy", return_value=mock_prompt
        ) as mock_fuzzy:
            select_module_items(
                skills=["foo"],
                commands=[],
                agents=[],
                mcps=[],
                has_instructions=True,
                current={
                    "skills": [],
                    "commands": [],
                    "agents": [],
                    "mcps": [],
                    "instructions": ["yes"],
                },
            )
        choices = mock_fuzzy.call_args.kwargs["choices"]
        instr_choice = next(c for c in choices if c.value == "instructions:")
        assert instr_choice.name.endswith("(installed)")
        assert instr_choice.enabled is True

    def test_picker_instructions_marked_new_when_current_lacks_them(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = []
        with patch(
            "lola.prompts.inquirer.fuzzy", return_value=mock_prompt
        ) as mock_fuzzy:
            select_module_items(
                skills=["foo"],
                commands=[],
                agents=[],
                mcps=[],
                has_instructions=True,
                current={
                    "skills": ["foo"],
                    "commands": [],
                    "agents": [],
                    "mcps": [],
                    "instructions": [],
                },
            )
        choices = mock_fuzzy.call_args.kwargs["choices"]
        instr_choice = next(c for c in choices if c.value == "instructions:")
        assert instr_choice.name.endswith("(new)")
        assert instr_choice.enabled is False

    def test_picker_returns_instructions_yes_when_selected(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = ["skill:foo", "instructions:"]
        with patch("lola.prompts.inquirer.fuzzy", return_value=mock_prompt):
            result = select_module_items(
                skills=["foo"],
                commands=[],
                agents=[],
                mcps=[],
                has_instructions=True,
            )
        assert result is not None
        assert result["instructions"] == ["yes"]
        assert result["skills"] == ["foo"]

    def test_picker_annotates_current_items(self):
        """When current= is passed, installed items get suffix + pre-select."""
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = []
        with patch(
            "lola.prompts.inquirer.fuzzy", return_value=mock_prompt
        ) as mock_fuzzy:
            select_module_items(
                skills=["foo", "bar"],
                commands=["c1"],
                agents=[],
                mcps=[],
                current={"skills": ["foo"], "commands": [], "agents": [], "mcps": []},
            )

        choices = mock_fuzzy.call_args.kwargs["choices"]
        choice_by_value = {c.value: c for c in choices}
        assert choice_by_value["skill:foo"].name.endswith("(installed)")
        assert choice_by_value["skill:foo"].enabled is True
        assert choice_by_value["skill:bar"].name.endswith("(new)")
        assert choice_by_value["skill:bar"].enabled is False
        assert choice_by_value["cmd:c1"].name.endswith("(new)")
        assert choice_by_value["cmd:c1"].enabled is False

    def test_picker_without_current_has_no_annotations(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = []
        with patch(
            "lola.prompts.inquirer.fuzzy", return_value=mock_prompt
        ) as mock_fuzzy:
            select_module_items(skills=["foo"], commands=[], agents=[], mcps=[])

        choices = mock_fuzzy.call_args.kwargs["choices"]
        assert "(installed)" not in choices[0].name
        assert "(new)" not in choices[0].name


class TestInstallationFullInstallField:
    """The Installation dataclass gained a full_install flag that defaults to True."""

    def test_defaults_to_full(self):
        inst = Installation(module_name="m", assistant="claude-code", scope="project")
        assert inst.full_install is True

    def test_to_dict_omits_full_install_when_true(self):
        inst = Installation(module_name="m", assistant="claude-code", scope="project")
        assert "full_install" not in inst.to_dict()

    def test_to_dict_emits_full_install_when_false(self):
        inst = Installation(
            module_name="m",
            assistant="claude-code",
            scope="project",
            full_install=False,
        )
        assert inst.to_dict()["full_install"] is False

    def test_from_dict_legacy_record_defaults_to_full(self):
        """Existing installed.yml entries without the field load as full installs."""
        inst = Installation.from_dict(
            {"module": "m", "assistant": "claude-code", "scope": "project"}
        )
        assert inst.full_install is True

    def test_round_trip_cherry_picked(self):
        original = Installation(
            module_name="m",
            assistant="claude-code",
            scope="project",
            skills=["only-this-one"],
            full_install=False,
        )
        roundtripped = Installation.from_dict(original.to_dict())
        assert roundtripped.full_install is False
        assert roundtripped.skills == ["only-this-one"]


class TestInstallFlagPicker:
    """Selection flags should drive install_to_assistant's selected_* params."""

    def _setup(self, tmp_path, sample_module):
        modules_dir = tmp_path / ".lola" / "modules"
        modules_dir.mkdir(parents=True)
        installed_file = tmp_path / ".lola" / "installed.yml"
        shutil.copytree(sample_module, modules_dir / "sample-module")
        return modules_dir, installed_file

    def test_no_flags_no_yes_in_noninteractive_installs_everything(
        self, cli_runner, sample_module, tmp_path
    ):
        """Non-interactive + no flags: selected_* are all None (full install)."""
        modules_dir, installed_file = self._setup(tmp_path, sample_module)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.install_to_assistant", return_value=1
            ) as mock_install,
            patch("lola.cli.install.is_interactive", return_value=False),
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd, ["sample-module", "-a", "claude-code"]
            )

        assert result.exit_code == 0
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_skills"] is None
        assert kwargs["selected_commands"] is None
        assert kwargs["selected_agents"] is None
        assert kwargs["selected_mcps"] is None

    def test_yes_flag_skips_picker_in_interactive_mode(
        self, cli_runner, sample_module, tmp_path
    ):
        """`-y` short-circuits the picker even when stdin is a TTY."""
        modules_dir, installed_file = self._setup(tmp_path, sample_module)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.install_to_assistant", return_value=1
            ) as mock_install,
            patch("lola.cli.install.is_interactive", return_value=True),
            patch("lola.cli.install.select_install_mode") as mock_mode,
            patch("lola.cli.install.select_module_items") as mock_picker,
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd, ["sample-module", "-a", "claude-code", "-y"]
            )

        assert result.exit_code == 0
        mock_mode.assert_not_called()
        mock_picker.assert_not_called()
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_skills"] is None  # full install
        assert kwargs["selected_commands"] is None
        assert kwargs["selected_agents"] is None

    def test_interactive_all_mode_installs_everything_without_picker(
        self, cli_runner, sample_module, tmp_path
    ):
        modules_dir, installed_file = self._setup(tmp_path, sample_module)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.install_to_assistant", return_value=1
            ) as mock_install,
            patch("lola.cli.install.is_interactive", return_value=True),
            patch("lola.cli.install.select_install_mode", return_value="all"),
            patch("lola.cli.install.select_module_items") as mock_picker,
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd, ["sample-module", "-a", "claude-code"]
            )

        assert result.exit_code == 0, result.output
        mock_picker.assert_not_called()
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_skills"] is None
        assert kwargs["selected_commands"] is None
        assert kwargs["selected_agents"] is None
        assert kwargs["selected_mcps"] is None

    def test_interactive_cherry_pick_mode_opens_item_picker(
        self, cli_runner, sample_module, tmp_path
    ):
        modules_dir, installed_file = self._setup(tmp_path, sample_module)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.install_to_assistant", return_value=1
            ) as mock_install,
            patch("lola.cli.install.is_interactive", return_value=True),
            patch("lola.cli.install.select_install_mode", return_value="cherry-pick"),
            patch(
                "lola.cli.install.select_module_items",
                return_value={
                    "skills": ["skill1"],
                    "commands": [],
                    "agents": [],
                    "mcps": [],
                    "instructions": [],
                },
            ) as mock_picker,
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd, ["sample-module", "-a", "claude-code"]
            )

        assert result.exit_code == 0, result.output
        mock_picker.assert_called_once()
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_skills"] == {"skill1"}
        assert kwargs["selected_commands"] == set()
        assert kwargs["selected_agents"] == set()
        assert kwargs["selected_mcps"] == set()

    def test_skill_flag_filters_other_categories_to_empty(
        self, cli_runner, sample_module, tmp_path
    ):
        """--skill with no --command means commands install nothing of that type.

        sample_module has skill1, cmd1, agent1. Asking for `--skill skill1`
        should plumb through as ``{skill1}`` for skills and an empty set for
        each of commands/agents/mcps so they're not silently installed too.
        """
        modules_dir, installed_file = self._setup(tmp_path, sample_module)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.install_to_assistant", return_value=1
            ) as mock_install,
            patch("lola.cli.install.is_interactive", return_value=False),
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd,
                ["sample-module", "-a", "claude-code", "--skill", "skill1"],
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_skills"] == {"skill1"}
        assert kwargs["selected_commands"] == set()
        assert kwargs["selected_agents"] == set()
        assert kwargs["selected_mcps"] == set()

    def test_comma_separated_skill_flag(self, cli_runner, sample_module, tmp_path):
        """`--skill foo,bar` is equivalent to `--skill foo --skill bar`."""
        # Add a second skill for this test
        modules_dir, installed_file = self._setup(tmp_path, sample_module)
        skills_dir = modules_dir / "sample-module" / "skills"
        (skills_dir / "skill2").mkdir()
        (skills_dir / "skill2" / "SKILL.md").write_text(
            "---\ndescription: A second test skill\n---\n\n# Skill 2\n"
        )

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.install_to_assistant", return_value=1
            ) as mock_install,
            patch("lola.cli.install.is_interactive", return_value=False),
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd,
                [
                    "sample-module",
                    "-a",
                    "claude-code",
                    "--skill",
                    "skill1,skill2",
                ],
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_skills"] == {"skill1", "skill2"}

    def test_no_flags_full_install_passes_none_for_instructions(
        self, cli_runner, sample_module, tmp_path
    ):
        modules_dir, installed_file = self._setup(tmp_path, sample_module)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.install_to_assistant", return_value=1
            ) as mock_install,
            patch("lola.cli.install.is_interactive", return_value=False),
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd, ["sample-module", "-a", "claude-code"]
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_instructions"] is None

    def test_skill_flag_without_instructions_skips_instructions(
        self, cli_runner, sample_module, tmp_path
    ):
        """--skill alone means cherry-pick mode; instructions default to False."""
        modules_dir, installed_file = self._setup(tmp_path, sample_module)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.install_to_assistant", return_value=1
            ) as mock_install,
            patch("lola.cli.install.is_interactive", return_value=False),
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd,
                ["sample-module", "-a", "claude-code", "--skill", "skill1"],
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_instructions"] is False

    def test_skill_flag_with_instructions_installs_both(
        self, cli_runner, sample_module, tmp_path
    ):
        modules_dir, installed_file = self._setup(tmp_path, sample_module)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.install_to_assistant", return_value=1
            ) as mock_install,
            patch("lola.cli.install.is_interactive", return_value=False),
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd,
                [
                    "sample-module",
                    "-a",
                    "claude-code",
                    "--skill",
                    "skill1",
                    "--instructions",
                ],
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_skills"] == {"skill1"}
        assert kwargs["selected_instructions"] is True

    def test_instructions_flag_alone_is_cherry_pick(
        self, cli_runner, sample_module, tmp_path
    ):
        """`--instructions` alone is a valid cherry-pick: empty sets + instructions."""
        modules_dir, installed_file = self._setup(tmp_path, sample_module)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.install_to_assistant", return_value=1
            ) as mock_install,
            patch("lola.cli.install.is_interactive", return_value=False),
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd,
                ["sample-module", "-a", "claude-code", "--instructions"],
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_skills"] == set()
        assert kwargs["selected_commands"] == set()
        assert kwargs["selected_agents"] == set()
        assert kwargs["selected_mcps"] == set()
        assert kwargs["selected_instructions"] is True

    def test_no_instructions_flag_alone_is_cherry_pick_skipping_instructions(
        self, cli_runner, sample_module, tmp_path
    ):
        modules_dir, installed_file = self._setup(tmp_path, sample_module)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.install_to_assistant", return_value=1
            ) as mock_install,
            patch("lola.cli.install.is_interactive", return_value=False),
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd,
                ["sample-module", "-a", "claude-code", "--no-instructions"],
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_instructions"] is False

    def test_unknown_skill_name_errors(self, cli_runner, sample_module, tmp_path):
        """Asking for a skill that the module doesn't expose is a hard error."""
        modules_dir, installed_file = self._setup(tmp_path, sample_module)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry") as mock_registry,
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch("lola.cli.install.install_to_assistant", return_value=1),
            patch("lola.cli.install.is_interactive", return_value=False),
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd,
                ["sample-module", "-a", "claude-code", "--skill", "no-such-skill"],
            )

        assert result.exit_code == 1
        assert "Unknown items" in result.output


class TestUpdateLockToSelection:
    """`lola update` must NOT silently expand a cherry-picked selection when the
    upstream module gains new items. Items removed upstream are still cleaned up.
    """

    def test_update_skips_new_upstream_skill_for_cherry_pick(
        self, cli_runner, sample_module, tmp_path
    ):
        """A cherry-picked install (full_install=False) locks to its skill list.

        Set up an Installation that originally selected only "skill1", drop a
        brand-new "skill2" into the source module, and confirm `lola update`
        regenerates only skill1.
        """
        modules_dir = tmp_path / ".lola" / "modules"
        modules_dir.mkdir(parents=True)
        installed_file = tmp_path / ".lola" / "installed.yml"
        shutil.copytree(sample_module, modules_dir / "sample-module")

        # Add an upstream skill that was NOT in the original selection.
        skills_dir = modules_dir / "sample-module" / "skills"
        (skills_dir / "new-skill").mkdir()
        (skills_dir / "new-skill" / "SKILL.md").write_text(
            "---\ndescription: A brand new upstream skill\n---\n\n# New\n"
        )

        # Pre-seed the registry with a cherry-picked install of just skill1.
        project_path = tmp_path / "project"
        project_path.mkdir()
        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="sample-module",
                assistant="claude-code",
                scope="project",
                project_path=str(project_path),
                skills=["skill1"],
                commands=[],
                agents=[],
                mcps=[],
                full_install=False,
            )
        )

        # Stub out the file-generating side of update: we only care about which
        # names get fed to it.
        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.targets.install.copy_module_to_local",
                return_value=modules_dir / "sample-module",
            ),
            patch(
                "lola.cli.install.copy_module_to_local",
                return_value=modules_dir / "sample-module",
            ),
        ):
            # Patch the actual generation methods on the AssistantTarget the
            # update flow obtains from the registry.
            from lola.targets import claude_code

            with (
                patch.object(
                    claude_code.ClaudeCodeTarget, "generate_skill", return_value=True
                ) as gen_skill,
                patch.object(
                    claude_code.ClaudeCodeTarget, "generate_command", return_value=True
                ),
                patch.object(
                    claude_code.ClaudeCodeTarget, "generate_agent", return_value=True
                ),
                patch.object(
                    claude_code.ClaudeCodeTarget,
                    "generate_instructions",
                    return_value=False,
                ),
            ):
                result = cli_runner.invoke(update_cmd, ["sample-module"])

        assert result.exit_code == 0, result.output
        # generate_skill should have been called for skill1 only.
        called_names = [c.args[2] for c in gen_skill.call_args_list]
        assert called_names == ["skill1"], called_names

    def test_update_full_install_picks_up_new_upstream_skill(
        self, cli_runner, sample_module, tmp_path
    ):
        """A full install (full_install=True) does pick up new upstream skills."""
        modules_dir = tmp_path / ".lola" / "modules"
        modules_dir.mkdir(parents=True)
        installed_file = tmp_path / ".lola" / "installed.yml"
        shutil.copytree(sample_module, modules_dir / "sample-module")

        skills_dir = modules_dir / "sample-module" / "skills"
        (skills_dir / "new-skill").mkdir()
        (skills_dir / "new-skill" / "SKILL.md").write_text(
            "---\ndescription: A brand new upstream skill\n---\n\n# New\n"
        )

        project_path = tmp_path / "project"
        project_path.mkdir()
        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="sample-module",
                assistant="claude-code",
                scope="project",
                project_path=str(project_path),
                skills=["skill1"],
                commands=[],
                agents=[],
                mcps=[],
                full_install=True,  # original install was full, not cherry-picked
            )
        )

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.targets.install.copy_module_to_local",
                return_value=modules_dir / "sample-module",
            ),
            patch(
                "lola.cli.install.copy_module_to_local",
                return_value=modules_dir / "sample-module",
            ),
        ):
            from lola.targets import claude_code

            with (
                patch.object(
                    claude_code.ClaudeCodeTarget, "generate_skill", return_value=True
                ) as gen_skill,
                patch.object(
                    claude_code.ClaudeCodeTarget, "generate_command", return_value=True
                ),
                patch.object(
                    claude_code.ClaudeCodeTarget, "generate_agent", return_value=True
                ),
                patch.object(
                    claude_code.ClaudeCodeTarget,
                    "generate_instructions",
                    return_value=False,
                ),
            ):
                result = cli_runner.invoke(update_cmd, ["sample-module"])

        assert result.exit_code == 0, result.output
        called_names = [c.args[2] for c in gen_skill.call_args_list]
        assert set(called_names) == {"skill1", "new-skill"}, called_names

    def test_update_preserves_renamed_cherry_picked_command(self, cli_runner, tmp_path):
        """A renamed cherry-picked command tracks source and installed names."""
        modules_dir = tmp_path / ".lola" / "modules"
        commands_dir = modules_dir / "rename-module" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "deploy.md").write_text(
            "---\ndescription: Deploy things\n---\n\n# Deploy\n"
        )
        (commands_dir / "status.md").write_text(
            "---\ndescription: Check status\n---\n\n# Status\n"
        )

        installed_file = tmp_path / ".lola" / "installed.yml"
        project_path = tmp_path / "project"
        project_path.mkdir()
        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="rename-module",
                assistant="claude-code",
                scope="project",
                project_path=str(project_path),
                skills=[],
                commands=["ship"],
                command_sources={"ship": "deploy"},
                agents=[],
                mcps=[],
                full_install=False,
            )
        )

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.targets.install.copy_module_to_local",
                return_value=modules_dir / "rename-module",
            ),
            patch(
                "lola.cli.install.copy_module_to_local",
                return_value=modules_dir / "rename-module",
            ),
        ):
            from lola.targets import claude_code

            with (
                patch.object(
                    claude_code.ClaudeCodeTarget, "generate_command", return_value=True
                ) as gen_command,
                patch.object(
                    claude_code.ClaudeCodeTarget,
                    "generate_instructions",
                    return_value=False,
                ),
            ):
                result = cli_runner.invoke(update_cmd, ["rename-module"])

        assert result.exit_code == 0, result.output
        assert [c.args[0].name for c in gen_command.call_args_list] == ["deploy.md"]
        assert [c.args[2] for c in gen_command.call_args_list] == ["ship"]

        updated_inst = registry.find("rename-module")[0]
        assert updated_inst.commands == ["ship"]
        assert updated_inst.command_sources == {"ship": "deploy"}

    def test_update_preserves_identity_and_renamed_cherry_pick_after_reload(
        self, cli_runner, tmp_path
    ):
        """Compact source maps must not make update drop identity-mapped picks."""
        modules_dir = tmp_path / ".lola" / "modules"
        commands_dir = modules_dir / "mixed-module" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "keep.md").write_text(
            "---\ndescription: Keep things\n---\n\n# Keep\n"
        )
        (commands_dir / "deploy.md").write_text(
            "---\ndescription: Deploy things\n---\n\n# Deploy\n"
        )
        (commands_dir / "new.md").write_text(
            "---\ndescription: New things\n---\n\n# New\n"
        )

        installed_file = tmp_path / ".lola" / "installed.yml"
        project_path = tmp_path / "project"
        project_path.mkdir()
        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="mixed-module",
                assistant="claude-code",
                scope="project",
                project_path=str(project_path),
                commands=["keep", "ship"],
                command_sources={"keep": "keep", "ship": "deploy"},
                full_install=False,
            )
        )
        registry = InstallationRegistry(installed_file)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.copy_module_to_local",
                return_value=modules_dir / "mixed-module",
            ),
        ):
            from lola.targets import claude_code

            with (
                patch.object(
                    claude_code.ClaudeCodeTarget, "generate_command", return_value=True
                ) as gen_command,
                patch.object(
                    claude_code.ClaudeCodeTarget,
                    "generate_instructions",
                    return_value=False,
                ),
            ):
                result = cli_runner.invoke(update_cmd, ["mixed-module"])

        assert result.exit_code == 0, result.output
        assert {c.args[0].name for c in gen_command.call_args_list} == {
            "keep.md",
            "deploy.md",
        }
        assert {c.args[2] for c in gen_command.call_args_list} == {"keep", "ship"}

        updated_inst = registry.find("mixed-module")[0]
        assert set(updated_inst.commands) == {"keep", "ship"}
        assert updated_inst.command_sources == {"keep": "keep", "ship": "deploy"}

    def test_full_update_preserves_renamed_command_registry_name_after_reload(
        self, cli_runner, tmp_path
    ):
        """Full command updates should store installed names, not source names."""
        modules_dir = tmp_path / ".lola" / "modules"
        commands_dir = modules_dir / "full-rename-module" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "deploy.md").write_text(
            "---\ndescription: Deploy things\n---\n\n# Deploy\n"
        )
        (commands_dir / "status.md").write_text(
            "---\ndescription: Check status\n---\n\n# Status\n"
        )

        installed_file = tmp_path / ".lola" / "installed.yml"
        project_path = tmp_path / "project"
        project_path.mkdir()
        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="full-rename-module",
                assistant="claude-code",
                scope="project",
                project_path=str(project_path),
                commands=["ship", "status"],
                command_sources={"ship": "deploy", "status": "status"},
                full_install=True,
            )
        )
        registry = InstallationRegistry(installed_file)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.copy_module_to_local",
                return_value=modules_dir / "full-rename-module",
            ),
        ):
            from lola.targets import claude_code

            with (
                patch.object(
                    claude_code.ClaudeCodeTarget, "generate_command", return_value=True
                ),
                patch.object(
                    claude_code.ClaudeCodeTarget,
                    "generate_instructions",
                    return_value=False,
                ),
            ):
                result = cli_runner.invoke(update_cmd, ["full-rename-module"])

        assert result.exit_code == 0, result.output
        updated_inst = registry.find("full-rename-module")[0]
        assert set(updated_inst.commands) == {"ship", "status"}
        assert updated_inst.command_sources == {"ship": "deploy", "status": "status"}

    def test_full_update_preserves_renamed_agent_registry_name_after_reload(
        self, cli_runner, tmp_path
    ):
        """Full agent updates should store installed names, not source names."""
        modules_dir = tmp_path / ".lola" / "modules"
        agents_dir = modules_dir / "full-agent-module" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "reviewer.md").write_text(
            "---\ndescription: Review code\n---\n\n# Reviewer\n"
        )
        (agents_dir / "helper.md").write_text(
            "---\ndescription: Help with work\n---\n\n# Helper\n"
        )

        installed_file = tmp_path / ".lola" / "installed.yml"
        project_path = tmp_path / "project"
        project_path.mkdir()
        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="full-agent-module",
                assistant="claude-code",
                scope="project",
                project_path=str(project_path),
                agents=["code-reviewer", "helper"],
                agent_sources={"code-reviewer": "reviewer", "helper": "helper"},
                full_install=True,
            )
        )
        registry = InstallationRegistry(installed_file)

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.copy_module_to_local",
                return_value=modules_dir / "full-agent-module",
            ),
        ):
            from lola.targets import claude_code

            with (
                patch.object(
                    claude_code.ClaudeCodeTarget, "generate_agent", return_value=True
                ),
                patch.object(
                    claude_code.ClaudeCodeTarget,
                    "generate_instructions",
                    return_value=False,
                ),
            ):
                result = cli_runner.invoke(update_cmd, ["full-agent-module"])

        assert result.exit_code == 0, result.output
        updated_inst = registry.find("full-agent-module")[0]
        assert set(updated_inst.agents) == {"code-reviewer", "helper"}
        assert updated_inst.agent_sources == {
            "code-reviewer": "reviewer",
            "helper": "helper",
        }

    def test_full_update_preserves_agents_when_target_skips_them(
        self, cli_runner, tmp_path
    ):
        """A full install keeps registered agents if the target cannot update them."""
        modules_dir = tmp_path / ".lola" / "modules"
        agents_dir = modules_dir / "agent-module" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "agent1.md").write_text(
            "---\ndescription: A test agent\n---\n\n# Agent\n"
        )

        installed_file = tmp_path / ".lola" / "installed.yml"
        project_path = tmp_path / "project"
        project_path.mkdir()
        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="agent-module",
                assistant="gemini-cli",
                scope="project",
                project_path=str(project_path),
                agents=["agent1"],
                agent_sources={"agent1": "agent1"},
                full_install=True,
            )
        )

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.copy_module_to_local",
                return_value=modules_dir / "agent-module",
            ),
        ):
            result = cli_runner.invoke(update_cmd, ["agent-module"])

        assert result.exit_code == 0, result.output
        updated_inst = registry.find("agent-module")[0]
        assert updated_inst.agents == ["agent1"]
        assert updated_inst.agent_sources == {"agent1": "agent1"}

    def test_full_update_preserves_mcps_when_target_skips_them(
        self, cli_runner, tmp_path
    ):
        """A full install keeps registered MCPs if the target cannot update them."""
        modules_dir = tmp_path / ".lola" / "modules"
        module_dir = modules_dir / "mcp-module"
        module_dir.mkdir(parents=True)
        (module_dir / "mcps.json").write_text(
            json.dumps({"mcpServers": {"github": {"command": "npx", "args": []}}})
        )

        installed_file = tmp_path / ".lola" / "installed.yml"
        project_path = tmp_path / "project"
        project_path.mkdir()
        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="mcp-module",
                assistant="openclaw",
                scope="project",
                project_path=str(project_path),
                mcps=["github"],
                mcp_sources={"github": "github"},
                full_install=True,
            )
        )

        with (
            patch("lola.cli.install.MODULES_DIR", modules_dir),
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
            patch("lola.cli.install.get_local_modules_path", return_value=modules_dir),
            patch(
                "lola.cli.install.copy_module_to_local",
                return_value=module_dir,
            ),
        ):
            result = cli_runner.invoke(update_cmd, ["mcp-module"])

        assert result.exit_code == 0, result.output
        updated_inst = registry.find("mcp-module")[0]
        assert updated_inst.mcps == ["github"]
        assert updated_inst.mcp_sources == {"github": "github"}
