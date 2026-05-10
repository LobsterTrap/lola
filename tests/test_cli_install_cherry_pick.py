"""Tests for cherry-pick install (issue #119): --skill/--command/--agent/--mcp
flags, the interactive picker, and lock-to-original-selection on update.
"""

from __future__ import annotations

import shutil
from unittest.mock import patch

from lola.cli.install import _expand_csv, install_cmd, update_cmd
from lola.models import Installation, InstallationRegistry
from lola.prompts import select_module_items


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
    def test_keep_all_returns_full_lists(self):
        """When the All token is selected, every list is returned in full.

        Leaving the 'All' token selected accepts every item
        regardless of which individual entries the user happened to toggle.
        """
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = ["__all__", "skill:foo"]
        with patch("lola.prompts.inquirer.checkbox", return_value=mock_prompt):
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
        }

    def test_subset_selection(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = ["skill:foo", "cmd:c1"]
        with patch("lola.prompts.inquirer.checkbox", return_value=mock_prompt):
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
        }

    def test_cancel_returns_none(self):
        from unittest.mock import MagicMock

        mock_prompt = MagicMock()
        mock_prompt.execute.return_value = None
        with patch("lola.prompts.inquirer.checkbox", return_value=mock_prompt):
            result = select_module_items(
                skills=["foo"], commands=[], agents=[], mcps=[]
            )
        assert result is None


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
            patch("lola.cli.install.select_module_items") as mock_picker,
        ):
            mock_registry.return_value = InstallationRegistry(installed_file)
            result = cli_runner.invoke(
                install_cmd, ["sample-module", "-a", "claude-code", "-y"]
            )

        assert result.exit_code == 0
        mock_picker.assert_not_called()
        kwargs = mock_install.call_args.kwargs
        assert kwargs["selected_skills"] is None  # full install
        assert kwargs["selected_commands"] is None
        assert kwargs["selected_agents"] is None

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
