"""Integration tests to verify completion callbacks are wired correctly."""

import click

from lola.__main__ import main
from lola.cli.completions import (
    complete_module_names,
    complete_marketplace_names,
    complete_installed_module_names,
)


class TestCompletionIntegration:
    """Verify completion callbacks are attached to appropriate CLI arguments."""

    def test_mod_commands_have_module_completion(self):
        """Verify mod commands have module name completion."""
        # Get the 'mod' command group
        mod_group = None
        for cmd in main.commands.values():
            if isinstance(cmd, click.Group) and cmd.name == "mod":
                mod_group = cmd
                break

        assert mod_group is not None, "mod command group not found"

        # Commands that should have module name completion
        commands_with_module_completion = {
            "rm": "module_name",
            "info": "module_name_or_path",
            "update": "module_name",
        }

        for cmd_name, arg_name in commands_with_module_completion.items():
            cmd = mod_group.commands.get(cmd_name)
            assert cmd is not None, f"mod {cmd_name} command not found"

            # Find the argument with the expected name
            arg = None
            for param in cmd.params:
                if isinstance(param, click.Argument) and param.name == arg_name:
                    arg = param
                    break

            assert arg is not None, f"Argument '{arg_name}' not found in mod {cmd_name}"
            # Click stores the callback in _custom_shell_complete
            assert hasattr(arg, "_custom_shell_complete"), (
                f"mod {cmd_name} {arg_name} should have a completion callback"
            )
            assert arg._custom_shell_complete == complete_module_names, (
                f"mod {cmd_name} {arg_name} should have complete_module_names callback"
            )

    def test_market_commands_have_marketplace_completion(self):
        """Verify market commands have marketplace name completion."""
        # Get the 'market' command group
        market_group = None
        for cmd in main.commands.values():
            if isinstance(cmd, click.Group) and cmd.name == "market":
                market_group = cmd
                break

        assert market_group is not None, "market command group not found"

        # Commands that should have marketplace name completion
        commands_with_marketplace_completion = {
            "ls": "name",
            "set": "name",
            "rm": "name",
            "update": "name",
        }

        for cmd_name, arg_name in commands_with_marketplace_completion.items():
            cmd = market_group.commands.get(cmd_name)
            assert cmd is not None, f"market {cmd_name} command not found"

            # Find the argument with the expected name
            arg = None
            for param in cmd.params:
                if isinstance(param, click.Argument) and param.name == arg_name:
                    arg = param
                    break

            assert arg is not None, (
                f"Argument '{arg_name}' not found in market {cmd_name}"
            )
            # Click stores the callback in _custom_shell_complete
            assert hasattr(arg, "_custom_shell_complete"), (
                f"market {cmd_name} {arg_name} should have a completion callback"
            )
            assert arg._custom_shell_complete == complete_marketplace_names, (
                f"market {cmd_name} {arg_name} should have complete_marketplace_names callback"
            )

    def test_install_command_has_module_completion(self):
        """Verify install command has module name completion."""
        install_cmd = main.commands.get("install")
        assert install_cmd is not None, "install command not found"

        # Find the module_name argument
        arg = None
        for param in install_cmd.params:
            if isinstance(param, click.Argument) and param.name == "module_name":
                arg = param
                break

        assert arg is not None, "module_name argument not found in install command"
        # Click stores the callback in _custom_shell_complete
        assert hasattr(arg, "_custom_shell_complete"), (
            "install module_name should have a completion callback"
        )
        assert arg._custom_shell_complete == complete_module_names, (
            "install module_name should have complete_module_names callback"
        )

    def test_uninstall_command_has_installed_module_completion(self):
        """Verify uninstall command has installed module name completion."""
        uninstall_cmd = main.commands.get("uninstall")
        assert uninstall_cmd is not None, "uninstall command not found"

        # Find the module_name argument
        arg = None
        for param in uninstall_cmd.params:
            if isinstance(param, click.Argument) and param.name == "module_name":
                arg = param
                break

        assert arg is not None, "module_name argument not found in uninstall command"
        # Click stores the callback in _custom_shell_complete
        assert hasattr(arg, "_custom_shell_complete"), (
            "uninstall module_name should have a completion callback"
        )
        assert arg._custom_shell_complete == complete_installed_module_names, (
            "uninstall module_name should have complete_installed_module_names callback"
        )

    def test_update_command_has_installed_module_completion(self):
        """Verify update command has installed module name completion."""
        update_cmd = main.commands.get("update")
        assert update_cmd is not None, "update command not found"

        # Find the module_name argument
        arg = None
        for param in update_cmd.params:
            if isinstance(param, click.Argument) and param.name == "module_name":
                arg = param
                break

        assert arg is not None, "module_name argument not found in update command"
        # Click stores the callback in _custom_shell_complete
        assert hasattr(arg, "_custom_shell_complete"), (
            "update module_name should have a completion callback"
        )
        assert arg._custom_shell_complete == complete_installed_module_names, (
            "update module_name should have complete_installed_module_names callback"
        )

    def test_all_completion_callbacks_are_used(self):
        """Verify all defined completion callbacks are actually used in the CLI."""
        # This is a reverse check - ensure we didn't create callbacks that aren't used
        completion_callbacks = {
            complete_module_names,
            complete_marketplace_names,
            complete_installed_module_names,
        }

        used_callbacks = set()

        def collect_callbacks(command):
            """Recursively collect all shell_complete callbacks from a command."""
            for param in command.params:
                # Click stores custom callbacks in _custom_shell_complete
                if hasattr(param, "_custom_shell_complete"):
                    used_callbacks.add(param._custom_shell_complete)

            if isinstance(command, click.Group):
                for subcmd in command.commands.values():
                    collect_callbacks(subcmd)

        collect_callbacks(main)

        # All our completion callbacks should be used
        for callback in completion_callbacks:
            assert callback in used_callbacks, (
                f"{callback.__name__} is defined but not used in CLI"
            )

    def test_completion_callbacks_have_correct_signature(self):
        """Verify all completion callbacks have the correct signature for Click."""
        # Click shell_complete callbacks should accept (ctx, param, incomplete)
        import inspect

        callbacks = [
            complete_module_names,
            complete_marketplace_names,
            complete_installed_module_names,
        ]

        for callback in callbacks:
            sig = inspect.signature(callback)
            params = list(sig.parameters.keys())
            assert len(params) == 3, f"{callback.__name__} should have 3 parameters"
            assert params == [
                "ctx",
                "param",
                "incomplete",
            ], f"{callback.__name__} parameters should be (ctx, param, incomplete)"

    def test_completion_callbacks_return_completion_items(self):
        """Verify completion callbacks return CompletionItem objects."""
        from click.shell_completion import CompletionItem

        # Test with mock data
        result = complete_module_names(None, None, "test")
        assert isinstance(result, list), "Callbacks should return a list"
        # Can be empty if no matches, but if non-empty, should be CompletionItem
        if result:
            assert all(isinstance(item, CompletionItem) for item in result), (
                "All items should be CompletionItem instances"
            )
