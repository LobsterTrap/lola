"""Step definitions for CLI invocation and output assertions."""

import shlex

from behave import when, then

from support.cli import resolve_path


@when('I run lola "{command}"')
def step_run_lola(context, command):
    """Invoke lola as a subprocess with the given command string."""
    command = resolve_path(context, command)
    args = shlex.split(command)
    context.last_result = context.cli.run(*args)


@then("the exit code should be {code:d}")
def step_exit_code(context, code):
    """Assert the exit code of the last lola invocation."""
    assert context.last_result.exit_code == code, (
        f"Expected exit code {code}, got {context.last_result.exit_code}.\n"
        f"stdout: {context.last_result.stdout}\n"
        f"stderr: {context.last_result.stderr}"
    )


@then('the output should contain "{text}"')
def step_output_contains(context, text):
    """Assert that stdout or stderr contains the given text."""
    text = resolve_path(context, text)
    combined = context.last_result.stdout + context.last_result.stderr
    assert text in combined, (
        f'Expected output to contain "{text}".\n'
        f"stdout: {context.last_result.stdout}\n"
        f"stderr: {context.last_result.stderr}"
    )


@then("the output should match /{pattern}/")
def step_output_matches(context, pattern):
    """Assert that the combined output matches a regex pattern."""
    import re

    pattern = resolve_path(context, pattern)
    combined = context.last_result.stdout + context.last_result.stderr
    assert re.search(pattern, combined), (
        f"Expected output to match /{pattern}/.\n"
        f"stdout: {context.last_result.stdout}\n"
        f"stderr: {context.last_result.stderr}"
    )


@when("I run lola with no arguments")
def step_run_lola_no_args(context):
    """Invoke lola as a subprocess with no arguments."""
    context.last_result = context.cli.run()


@then('the output should not contain "{text}"')
def step_output_not_contains(context, text):
    """Assert that neither stdout nor stderr contains the given text."""
    text = resolve_path(context, text)
    combined = context.last_result.stdout + context.last_result.stderr
    assert text not in combined, (
        f'Expected output NOT to contain "{text}".\n'
        f"stdout: {context.last_result.stdout}\n"
        f"stderr: {context.last_result.stderr}"
    )
