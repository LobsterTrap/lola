"""Tests for CopilotTarget scope-aware path resolution and file generation."""

from pathlib import Path

from lola.targets.copilot import CopilotTarget


# --- Project scope path tests ---


def test_copilot_skill_path_project_scope():
    target = CopilotTarget()
    path = target.get_skill_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.github/skills")


def test_copilot_command_path_project_scope():
    target = CopilotTarget()
    path = target.get_command_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.github/prompts")


def test_copilot_agent_path_project_scope():
    target = CopilotTarget()
    path = target.get_agent_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.github/agents")


def test_copilot_instructions_path_project_scope():
    target = CopilotTarget()
    path = target.get_instructions_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.github/copilot-instructions.md")


def test_copilot_mcp_path_project_scope():
    target = CopilotTarget()
    path = target.get_mcp_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.vscode/mcp.json")


# --- User scope path tests ---


def test_copilot_skill_path_user_scope():
    target = CopilotTarget()
    path = target.get_skill_path("/home/user/project", "user")
    assert path == Path.home() / ".copilot" / "skills"


def test_copilot_command_path_user_scope():
    target = CopilotTarget()
    path = target.get_command_path("/home/user/project", "user")
    assert path == Path.home() / ".copilot" / "prompts"


def test_copilot_agent_path_user_scope():
    target = CopilotTarget()
    path = target.get_agent_path("/home/user/project", "user")
    assert path == Path.home() / ".copilot" / "agents"


def test_copilot_instructions_path_user_scope():
    target = CopilotTarget()
    path = target.get_instructions_path("/home/user/project", "user")
    assert path == Path.home() / ".copilot" / "copilot-instructions.md"


def test_copilot_mcp_path_user_scope():
    target = CopilotTarget()
    path = target.get_mcp_path("/home/user/project", "user")
    assert path == Path.home() / ".copilot" / "mcp-config.json"


# --- Default scope tests ---


def test_copilot_skill_path_default_scope():
    target = CopilotTarget()
    path = target.get_skill_path("/home/user/project")
    assert path == Path("/home/user/project/.github/skills")


def test_copilot_command_path_default_scope():
    target = CopilotTarget()
    path = target.get_command_path("/home/user/project")
    assert path == Path("/home/user/project/.github/prompts")


def test_copilot_agent_path_default_scope():
    target = CopilotTarget()
    path = target.get_agent_path("/home/user/project")
    assert path == Path("/home/user/project/.github/agents")


def test_copilot_instructions_path_default_scope():
    target = CopilotTarget()
    path = target.get_instructions_path("/home/user/project")
    assert path == Path("/home/user/project/.github/copilot-instructions.md")


def test_copilot_mcp_path_default_scope():
    target = CopilotTarget()
    path = target.get_mcp_path("/home/user/project")
    assert path == Path("/home/user/project/.vscode/mcp.json")


# --- Skill generation tests ---


def test_generate_skill_basic(tmp_path):
    """Generate SKILL.md in skill directory with name + description frontmatter."""
    target = CopilotTarget()
    source = tmp_path / "my-skill"
    source.mkdir()
    (source / "SKILL.md").write_text(
        "---\ndescription: Does the thing\n---\n\nDo the thing.\n"
    )

    dest = tmp_path / "skills"
    result = target.generate_skill(source, dest, "my-skill")

    assert result is True
    output_file = dest / "my-skill" / "SKILL.md"
    assert output_file.exists()
    content = output_file.read_text()
    assert "name: my-skill" in content
    assert "description: Does the thing" in content
    assert "Do the thing." in content


def test_generate_skill_missing_description(tmp_path):
    """Return False if SKILL.md has no description (required by Copilot)."""
    target = CopilotTarget()
    source = tmp_path / "my-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("No frontmatter here.\n")

    dest = tmp_path / "skills"
    result = target.generate_skill(source, dest, "my-skill")
    assert result is False


def test_generate_skill_with_apply_to(tmp_path):
    """Generate SKILL.md preserving applyTo and description frontmatter."""
    target = CopilotTarget()
    source = tmp_path / "tf-skill"
    source.mkdir()
    (source / "SKILL.md").write_text(
        '---\napplyTo: "**/*.tf"\ndescription: Terraform help\n---\n\nTerraform instructions.\n'
    )

    dest = tmp_path / "skills"
    result = target.generate_skill(source, dest, "tf-skill")

    assert result is True
    output_file = dest / "tf-skill" / "SKILL.md"
    content = output_file.read_text()
    assert "name: tf-skill" in content
    assert "description: Terraform help" in content
    assert "applyTo:" in content
    assert "**/*.tf" in content
    assert "Terraform instructions." in content


def test_generate_skill_with_globs_as_apply_to(tmp_path):
    """Generate SKILL.md converting globs to applyTo."""
    target = CopilotTarget()
    source = tmp_path / "py-skill"
    source.mkdir()
    (source / "SKILL.md").write_text(
        '---\nglobs: "**/*.py"\ndescription: Python help\n---\n\nPython instructions.\n'
    )

    dest = tmp_path / "skills"
    result = target.generate_skill(source, dest, "py-skill")

    assert result is True
    output_file = dest / "py-skill" / "SKILL.md"
    content = output_file.read_text()
    assert "applyTo:" in content
    assert "**/*.py" in content


def test_generate_skill_missing_source(tmp_path):
    """Return False if source doesn't exist."""
    target = CopilotTarget()
    source = tmp_path / "nonexistent"
    dest = tmp_path / "skills"

    result = target.generate_skill(source, dest, "nonexistent")
    assert result is False


def test_generate_skill_missing_skill_md(tmp_path):
    """Return False if SKILL.md doesn't exist in source."""
    target = CopilotTarget()
    source = tmp_path / "empty-skill"
    source.mkdir()
    dest = tmp_path / "skills"

    result = target.generate_skill(source, dest, "empty-skill")
    assert result is False


# --- Skill removal tests ---


def test_remove_skill(tmp_path):
    """Remove existing skill directory."""
    target = CopilotTarget()
    dest = tmp_path / "skills"
    skill_dir = dest / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("content")

    result = target.remove_skill(dest, "my-skill")
    assert result is True
    assert not skill_dir.exists()


def test_remove_skill_not_found(tmp_path):
    """Return False if skill directory doesn't exist."""
    target = CopilotTarget()
    dest = tmp_path / "skills"
    dest.mkdir()

    result = target.remove_skill(dest, "missing")
    assert result is False


def test_remove_skill_legacy_instructions(tmp_path):
    """Remove both skill dir and legacy .instructions.md during uninstall."""
    target = CopilotTarget()
    # dest_path is .github/skills, so parent is .github
    dest = tmp_path / ".github" / "skills"
    skill_dir = dest / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("content")
    instructions_dir = tmp_path / ".github" / "instructions"
    instructions_dir.mkdir()
    legacy_file = instructions_dir / "my-skill.instructions.md"
    legacy_file.write_text("old format")

    result = target.remove_skill(dest, "my-skill")
    assert result is True
    assert not skill_dir.exists()
    assert not legacy_file.exists()


# --- Command generation tests ---


def test_generate_command(tmp_path):
    """Generate .prompt.md command file."""
    target = CopilotTarget()
    source = tmp_path / "review.md"
    source.write_text("Review the code.\n")
    dest = tmp_path / "prompts"

    result = target.generate_command(source, dest, "review", "my-module")
    assert result is True
    assert (dest / "review.prompt.md").exists()
    assert (dest / "review.prompt.md").read_text() == "Review the code.\n"


def test_command_filename():
    """Command filename uses .prompt.md extension."""
    target = CopilotTarget()
    assert target.get_command_filename("my-module", "review") == "review.prompt.md"


# --- Agent generation tests ---


def test_generate_agent(tmp_path):
    """Generate .agent.md agent file."""
    target = CopilotTarget()
    source = tmp_path / "reviewer.md"
    source.write_text("---\ndescription: Reviews code\n---\n\nAgent content.\n")
    dest = tmp_path / "agents"

    result = target.generate_agent(source, dest, "reviewer", "my-module")
    assert result is True
    output = dest / "reviewer.agent.md"
    assert output.exists()
    assert "description: Reviews code" in output.read_text()


def test_generate_agent_missing_source(tmp_path):
    """Return False if agent source doesn't exist."""
    target = CopilotTarget()
    source = tmp_path / "missing.md"
    dest = tmp_path / "agents"

    result = target.generate_agent(source, dest, "missing", "my-module")
    assert result is False


def test_agent_filename():
    """Agent filename uses .agent.md extension."""
    target = CopilotTarget()
    assert target.get_agent_filename("my-module", "reviewer") == "reviewer.agent.md"


# --- Remove command/agent tests ---


def test_remove_command(tmp_path):
    """Remove .prompt.md command file."""
    target = CopilotTarget()
    dest = tmp_path / "prompts"
    dest.mkdir()
    (dest / "review.prompt.md").write_text("content")

    result = target.remove_command(dest, "review", "my-module")
    assert result is True
    assert not (dest / "review.prompt.md").exists()


def test_remove_agent(tmp_path):
    """Remove .agent.md agent file."""
    target = CopilotTarget()
    dest = tmp_path / "agents"
    dest.mkdir()
    (dest / "reviewer.agent.md").write_text("content")

    result = target.remove_agent(dest, "reviewer", "my-module")
    assert result is True
    assert not (dest / "reviewer.agent.md").exists()


# --- Target metadata ---


def test_copilot_target_name():
    target = CopilotTarget()
    assert target.name == "copilot"


def test_copilot_supports_agents():
    target = CopilotTarget()
    assert target.supports_agents is True
