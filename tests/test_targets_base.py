"""Tests for AssistantTarget ABC scope parameter support."""

from pathlib import Path

from lola.targets.base import AssistantTarget


class MockTarget(AssistantTarget):
    """Mock target for testing ABC."""

    name = "mock"
    supports_agents = True
    uses_managed_section = False

    def get_skill_path(self, project_path: str, scope: str = "project") -> Path:
        if scope == "user":
            return Path.home() / ".mock" / "skills"
        return Path(project_path) / ".mock" / "skills"

    def get_command_path(self, project_path: str, scope: str = "project") -> Path:
        if scope == "user":
            return Path.home() / ".mock" / "commands"
        return Path(project_path) / ".mock" / "commands"

    def get_agent_path(self, project_path: str, scope: str = "project") -> Path:
        if scope == "user":
            return Path.home() / ".mock" / "agents"
        return Path(project_path) / ".mock" / "agents"

    def get_instructions_path(self, project_path: str, scope: str = "project") -> Path:
        if scope == "user":
            return Path.home() / "MOCK.md"
        return Path(project_path) / "MOCK.md"

    def get_mcp_path(self, project_path: str, scope: str = "project") -> Path:
        if scope == "user":
            return Path.home() / ".mock.json"
        return Path(project_path) / ".mock.json"

    # Minimal stubs for other required methods
    def generate_skill(self, source_path, dest_path, skill_name, project_path=None):
        return True

    def generate_command(self, source_path, dest_dir, cmd_name, module_name):
        return True

    def generate_agent(self, source_path, dest_dir, agent_name, module_name):
        return True

    def generate_instructions(
        self, source: Path | str, dest_path: Path, module_name: str
    ) -> bool:
        return True

    def remove_skill(self, dest_path, skill_name):
        return True

    def remove_instructions(self, dest_path, module_name):
        return True

    def generate_skills_batch(self, dest_file, module_name, skills, project_path):
        return True

    def get_command_filename(self, module_name, cmd_name):
        return f"{module_name}.{cmd_name}.md"

    def get_agent_filename(self, module_name, agent_name):
        return f"{module_name}.{agent_name}.md"

    def generate_mcps(self, mcps, dest_path, module_name):
        return True

    def remove_mcps(
        self, dest_path: Path, module_name: str, mcp_names: list[str] | None = None
    ) -> bool:
        return True

    def remove_command(self, dest_dir, cmd_name, module_name):
        return True

    def remove_agent(self, dest_dir, agent_name, module_name):
        return True


def test_get_skill_path_project_scope():
    target = MockTarget()
    path = target.get_skill_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.mock/skills")


def test_get_skill_path_user_scope():
    target = MockTarget()
    path = target.get_skill_path("/home/user/project", "user")
    assert path == Path.home() / ".mock" / "skills"


def test_get_command_path_project_scope():
    target = MockTarget()
    path = target.get_command_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.mock/commands")


def test_get_command_path_user_scope():
    target = MockTarget()
    path = target.get_command_path("/home/user/project", "user")
    assert path == Path.home() / ".mock" / "commands"
