"""GitHub Copilot target implementation."""

from __future__ import annotations

from pathlib import Path

import lola.config as config
import lola.frontmatter as fm
from .base import (
    BaseAssistantTarget,
    ManagedInstructionsTarget,
    MCPSupportMixin,
    _generate_passthrough_command,
)


class CopilotTarget(MCPSupportMixin, ManagedInstructionsTarget, BaseAssistantTarget):
    """Target for GitHub Copilot (VS Code + Visual Studio).

    Copilot supports:
    - Skills in .copilot/skills/<name>/SKILL.md (with name+description frontmatter)
    - Prompt files in .github/prompts/*.prompt.md
    - Agents in .github/agents/*.agent.md
    - Global instructions in .github/copilot-instructions.md
    - MCP servers in .github/copilot/mcp.json
    """

    name = "copilot"
    supports_agents = True
    INSTRUCTIONS_FILE = "copilot-instructions.md"

    def get_skill_path(self, project_path: str, scope: str = "project") -> Path:
        if scope == "user":
            return Path.home() / ".copilot" / "skills"
        return Path(project_path) / ".github" / "skills"

    def get_command_path(self, project_path: str, scope: str = "project") -> Path:
        if scope == "user":
            return Path.home() / ".copilot" / "prompts"
        return Path(project_path) / ".github" / "prompts"

    def get_agent_path(self, project_path: str, scope: str = "project") -> Path:
        if scope == "user":
            return Path.home() / ".copilot" / "agents"
        return Path(project_path) / ".github" / "agents"

    def get_instructions_path(self, project_path: str, scope: str = "project") -> Path:
        base = Path.home() if scope == "user" else Path(project_path)
        return base / ".github" / self.INSTRUCTIONS_FILE

    def get_mcp_path(self, project_path: str, scope: str = "project") -> Path:
        base = Path.home() if scope == "user" else Path(project_path)
        return base / ".github" / "copilot" / "mcp.json"

    def generate_skill(
        self,
        source_path: Path,
        dest_path: Path,
        skill_name: str,
        project_path: str | None = None,  # noqa: ARG002
    ) -> bool:
        """Generate SKILL.md in .copilot/skills/<name>/ directory.

        Copilot skills use a directory-per-skill structure with
        name + description in YAML frontmatter.
        """
        if not source_path.exists():
            return False

        skill_file = source_path / config.SKILL_FILE
        if not skill_file.exists():
            return False

        content = skill_file.read_text()
        frontmatter, body = fm.parse(content)

        description = frontmatter.get("description")
        if not description:
            return False

        skill_dir = dest_path / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Build Copilot-compatible frontmatter (requires name + description)
        import yaml

        copilot_fm: dict = {
            "name": skill_name,
            "description": description,
        }
        if frontmatter.get("applyTo"):
            copilot_fm["applyTo"] = frontmatter["applyTo"]
        elif frontmatter.get("globs"):
            copilot_fm["applyTo"] = frontmatter["globs"]

        fm_str = yaml.dump(
            copilot_fm, default_flow_style=False, sort_keys=False
        ).rstrip()
        output = f"---\n{fm_str}\n---\n{body}"

        dest_file = skill_dir / "SKILL.md"
        dest_file.write_text(output)
        return True

    def remove_skill(self, dest_path: Path, skill_name: str) -> bool:
        """Remove a skill's directory."""
        import shutil

        removed = False
        skill_dir = dest_path / skill_name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            removed = True
        # Legacy cleanup: old .instructions.md format
        legacy_file = (
            dest_path.parent / "instructions" / f"{skill_name}.instructions.md"
        )
        if legacy_file.exists():
            legacy_file.unlink()
            removed = True
        return removed

    def generate_command(
        self,
        source_path: Path,
        dest_dir: Path,
        cmd_name: str,
        module_name: str,
    ) -> bool:
        filename = self.get_command_filename(module_name, cmd_name)
        return _generate_passthrough_command(source_path, dest_dir, filename)

    def get_command_filename(self, module_name: str, cmd_name: str) -> str:  # noqa: ARG002
        """Copilot uses .prompt.md extension for commands."""
        return f"{cmd_name}.prompt.md"

    def generate_agent(
        self,
        source_path: Path,
        dest_dir: Path,
        agent_name: str,
        module_name: str,
    ) -> bool:
        """Generate agent file with .agent.md extension.

        Copilot agents use YAML frontmatter with fields like:
        - description: when to use this agent
        - tools: list of tools the agent can use
        """
        if not source_path.exists():
            return False
        dest_dir.mkdir(parents=True, exist_ok=True)

        filename = self.get_agent_filename(module_name, agent_name)
        content = source_path.read_text()

        (dest_dir / filename).write_text(content)
        return True

    def get_agent_filename(self, module_name: str, agent_name: str) -> str:  # noqa: ARG002
        """Copilot uses .agent.md extension for agents."""
        return f"{agent_name}.agent.md"

    def remove_command(
        self,
        dest_dir: Path,
        cmd_name: str,
        module_name: str,
    ) -> bool:
        """Delete command file (.prompt.md)."""
        filename = self.get_command_filename(module_name, cmd_name)
        cmd_file = dest_dir / filename
        if cmd_file.exists():
            cmd_file.unlink()
        # Legacy cleanup
        legacy_file = dest_dir / f"{module_name}.{cmd_name}.prompt.md"
        if legacy_file.exists():
            legacy_file.unlink()
        return True

    def remove_agent(
        self,
        dest_dir: Path,
        agent_name: str,
        module_name: str,
    ) -> bool:
        """Delete agent file (.agent.md)."""
        filename = self.get_agent_filename(module_name, agent_name)
        agent_file = dest_dir / filename
        if agent_file.exists():
            agent_file.unlink()
        # Legacy cleanup
        legacy_file = dest_dir / f"{module_name}.{agent_name}.agent.md"
        if legacy_file.exists():
            legacy_file.unlink()
        return True
