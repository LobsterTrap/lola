"""
models:
    Data models for lola modules, skills, and installations
"""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import tempfile
from typing import Optional
import yaml

from lola.config import MCPS_FILE, SKILL_FILE
from lola import frontmatter as fm
from lola.exceptions import ValidationError

SKILLS_DIRNAME = "skills"
MODULE_CONTENT_DIRNAME = "module"
LOLA_MODULE_CONTENT_DIRNAME = "lola-module"


@dataclass
class Skill:
    """Represents a skill within a module."""

    name: str
    path: Path
    description: Optional[str] = None

    @classmethod
    def from_path(cls, skill_path: Path) -> "Skill":
        """Load a skill from its directory path."""
        skill_file = skill_path / SKILL_FILE
        description = None

        if skill_file.exists():
            description = fm.get_description(skill_file)

        return cls(name=skill_path.name, path=skill_path, description=description)


@dataclass
class Command:
    """Represents a slash command within a module."""

    name: str
    path: Path
    description: Optional[str] = None
    argument_hint: Optional[str] = None

    @classmethod
    def from_path(cls, command_path: Path) -> "Command":
        """Load a command from its file path."""
        description = None
        argument_hint = None

        if command_path.exists():
            metadata = fm.get_metadata(command_path)
            description = metadata.get("description")
            argument_hint = metadata.get("argument-hint")

        # Command name derived from filename (without .md extension)
        name = command_path.stem

        return cls(
            name=name,
            path=command_path,
            description=description,
            argument_hint=argument_hint,
        )


@dataclass
class Agent:
    """Represents a subagent within a module."""

    name: str
    path: Path
    description: Optional[str] = None
    model: Optional[str] = None

    @classmethod
    def from_path(cls, agent_path: Path) -> "Agent":
        """Load an agent from its file path."""
        description = None
        model = None

        if agent_path.exists():
            metadata = fm.get_metadata(agent_path)
            description = metadata.get("description")
            model = metadata.get("model")

        # Agent name derived from filename (without .md extension)
        name = agent_path.stem

        return cls(
            name=name,
            path=agent_path,
            description=description,
            model=model,
        )


@dataclass
class MCPServer:
    """Represents an MCP server definition within a module."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "MCPServer":
        """Create from a dictionary entry in mcps.json."""
        return cls(
            name=name,
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
        )


INSTRUCTIONS_FILE = "AGENTS.md"


@dataclass
class Module:
    """Represents a lola module."""

    name: str
    path: Path
    content_path: (
        Path  # Path to the directory containing lola content (module/ or root)
    )
    skills: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    mcps: list[str] = field(default_factory=list)
    has_instructions: bool = False
    uses_module_subdir: bool = False  # True if content is in module/ subdirectory
    is_single_skill: bool = (
        False  # True if SKILL.md at content_path root (agentskills.io standard)
    )
    pre_install_hook: Optional[str] = (
        None  # Path to pre-install script (relative to content_path)
    )
    post_install_hook: Optional[str] = (
        None  # Path to post-install script (relative to content_path)
    )

    @classmethod
    def from_path(
        cls, module_path: Path, content_dirname: Optional[str] = None
    ) -> Optional["Module"]:
        """
        Load a module from its directory path.

        Args:
            module_path: Path to the module directory
            content_dirname: Optional custom directory for content
                            "/" = use root, otherwise subdirectory name

        Auto-discovers:
        - skills (folders containing SKILL.md) under skills/<skill_name>/
        - commands (.md files in commands/ folder)
        - agents (.md files in agents/ folder)
        """
        if not module_path.exists() or not module_path.is_dir():
            return None

        content_path, uses_module_subdir = cls._resolve_content_path(
            module_path, content_dirname
        )

        if content_path is None:
            return None

        skills = []
        is_single_skill = False

        # Check for skill bundle (skills/ subdirectory)
        skills_root = content_path / SKILLS_DIRNAME
        if skills_root.exists() and skills_root.is_dir():
            for subdir in skills_root.iterdir():
                if subdir.name.startswith("."):
                    continue
                if subdir.is_dir() and (subdir / SKILL_FILE).exists():
                    skills.append(subdir.name)

        # If no bundle found, check for single skill at root (agentskills.io standard)
        if not skills:
            single_skill_file = content_path / SKILL_FILE
            if single_skill_file.exists() and single_skill_file.is_file():
                metadata = fm.get_metadata(single_skill_file)
                skill_name = module_path.name
                meta_name = metadata.get("name")
                if meta_name and isinstance(meta_name, str):
                    skill_name = meta_name
                skills.append(skill_name)
                is_single_skill = True

        # Auto-discover commands: .md files in commands/
        commands = []
        commands_dir = content_path / "commands"
        if commands_dir.exists() and commands_dir.is_dir():
            for cmd_file in commands_dir.glob("*.md"):
                commands.append(cmd_file.stem)

        # Auto-discover agents: .md files in agents/
        agents = []
        agents_dir = content_path / "agents"
        if agents_dir.exists() and agents_dir.is_dir():
            for agent_file in agents_dir.glob("*.md"):
                agents.append(agent_file.stem)

        # Check for module instructions (AGENTS.md)
        instructions_file = content_path / INSTRUCTIONS_FILE
        has_instructions = (
            instructions_file.exists() and instructions_file.stat().st_size > 0
        )

        # Auto-discover MCP servers from mcps.json
        mcps: list[str] = []
        mcps_file = content_path / MCPS_FILE
        if mcps_file.exists():
            try:
                data = json.loads(mcps_file.read_text())
                mcps = sorted(data.get("mcpServers", {}).keys())
            except (json.JSONDecodeError, OSError):
                pass

        # Auto-discover hooks from lola.yaml
        pre_install_hook = None
        post_install_hook = None
        lola_yaml = content_path / "lola.yaml"
        if lola_yaml.exists():
            try:
                with open(lola_yaml) as f:
                    config = yaml.safe_load(f) or {}
                hooks = config.get("hooks", {})
                pre_install_hook = (
                    hooks.get("pre-install") if isinstance(hooks, dict) else None
                )
                post_install_hook = (
                    hooks.get("post-install") if isinstance(hooks, dict) else None
                )
            except (yaml.YAMLError, OSError):
                pass  # hooks are optional; malformed lola.yaml is non-fatal

        # Only valid if has at least one skill, command, agent, mcp, or instructions
        if (
            not skills
            and not commands
            and not agents
            and not mcps
            and not has_instructions
        ):
            return None

        return cls(
            name=module_path.name,
            path=module_path,
            content_path=content_path,
            skills=sorted(skills),
            commands=sorted(commands),
            agents=sorted(agents),
            mcps=mcps,
            has_instructions=has_instructions,
            uses_module_subdir=uses_module_subdir,
            is_single_skill=is_single_skill,
            pre_install_hook=pre_install_hook,
            post_install_hook=post_install_hook,
        )

    @classmethod
    def _resolve_content_path(
        cls, module_path: Path, content_dirname: Optional[str]
    ) -> tuple[Optional[Path], bool]:
        """
        Resolve content path from module path and optional content dirname.

        Args:
            module_path: Path to the module directory
            content_dirname: Optional custom directory name
                            "/" = use root, otherwise subdirectory name

        Returns:
            (content_path, uses_module_subdir) or (None, False) if invalid
        """
        # Custom content directory specified
        if content_dirname is not None:
            # Root directory requested
            if content_dirname == "/":
                return module_path, False

            # Custom subdirectory path
            custom_subdir = module_path / content_dirname
            if not custom_subdir.exists() or not custom_subdir.is_dir():
                return None, False

            return custom_subdir, True

        # Default discovery: try module/ then fallback to root
        module_subdir = module_path / MODULE_CONTENT_DIRNAME
        if module_subdir.exists() and module_subdir.is_dir():
            return module_subdir, True

        return module_path, False

    def _skills_root_dir(self) -> Path:
        """Get the directory that contains skill folders."""
        if self.is_single_skill:
            return self.content_path
        return self.content_path / SKILLS_DIRNAME

    def get_skill_paths(self) -> list[Path]:
        """Get the full paths to all skills in this module."""
        if self.is_single_skill:
            return [self.content_path]
        return [self.content_path / SKILLS_DIRNAME / skill for skill in self.skills]

    def get_command_paths(self) -> list[Path]:
        """Get the full paths to all commands in this module."""
        commands_dir = self.content_path / "commands"
        return [commands_dir / f"{cmd}.md" for cmd in self.commands]

    def get_agent_paths(self) -> list[Path]:
        """Get the full paths to all agents in this module."""
        agents_dir = self.content_path / "agents"
        return [agents_dir / f"{agent}.md" for agent in self.agents]

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the module structure.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check each skill exists and has SKILL.md with valid frontmatter
        for skill_name, skill_path in zip(self.skills, self.get_skill_paths()):
            if not skill_path.exists():
                errors.append(f"Skill directory not found: {skill_name}")
            elif not (skill_path / SKILL_FILE).exists():
                errors.append(f"Missing {SKILL_FILE} in skill: {skill_name}")
            else:
                # Validate SKILL.md frontmatter
                skill_errors = fm.validate_skill(skill_path / SKILL_FILE)
                for err in skill_errors:
                    errors.append(f"{skill_name}/{SKILL_FILE}: {err}")

        # Check each command exists and has valid frontmatter
        commands_dir = self.content_path / "commands"
        for cmd_name in self.commands:
            cmd_path = commands_dir / f"{cmd_name}.md"
            if not cmd_path.exists():
                errors.append(f"Command file not found: commands/{cmd_name}.md")
            else:
                cmd_errors = fm.validate_command(cmd_path)
                for err in cmd_errors:
                    errors.append(f"commands/{cmd_name}.md: {err}")

        # Check each agent exists and has valid frontmatter
        agents_dir = self.content_path / "agents"
        for agent_name in self.agents:
            agent_path = agents_dir / f"{agent_name}.md"
            if not agent_path.exists():
                errors.append(f"Agent file not found: agents/{agent_name}.md")
            else:
                agent_errors = fm.validate_agent(agent_path)
                for err in agent_errors:
                    errors.append(f"agents/{agent_name}.md: {err}")

        # Check mcps.json if module has MCPs
        if self.mcps:
            mcps_file = self.content_path / MCPS_FILE
            if not mcps_file.exists():
                errors.append(f"MCP file not found: {MCPS_FILE}")
            else:
                mcp_errors = fm.validate_mcps(mcps_file)
                for err in mcp_errors:
                    errors.append(f"{MCPS_FILE}: {err}")

        # Validate hooks if defined
        for hook_type, hook_path in [
            ("pre-install", self.pre_install_hook),
            ("post-install", self.post_install_hook),
        ]:
            if not hook_path:
                continue

            full_path = self.content_path / hook_path
            if not full_path.exists():
                errors.append(f"{hook_type} hook script not found: {hook_path}")
                continue

            try:
                full_path.resolve().relative_to(self.path.resolve())
            except ValueError:
                errors.append(f"{hook_type} hook outside module directory: {hook_path}")

        return len(errors) == 0, errors

    def validate_or_raise(self) -> None:
        """
        Validate the module structure.

        Raises:
            ValidationError: If the module has validation errors.
        """
        is_valid, errors = self.validate()
        if not is_valid:
            raise ValidationError(self.name, errors)


@dataclass
class Marketplace:
    """Represents a marketplace catalog with modules."""

    name: str
    url: str
    enabled: bool = True
    description: str = ""
    version: str = ""
    modules: list[dict] = field(default_factory=list)

    @classmethod
    def from_reference(cls, ref_file: Path) -> "Marketplace":
        """Load marketplace from reference file."""
        with open(ref_file) as f:
            data = yaml.safe_load(f) or {}
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
            enabled=data.get("enabled", True),
        )

    @classmethod
    def from_cache(cls, cache_file: Path) -> "Marketplace":
        """Load marketplace from cache file."""
        with open(cache_file) as f:
            data = yaml.safe_load(f) or {}
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
            version=data.get("version", ""),
            modules=data.get("modules", []),
        )

    @classmethod
    def from_url(cls, url: str, name: str) -> "Marketplace":
        """Load marketplace from URL (http/https) or local file path."""
        from urllib.request import urlopen
        from urllib.error import URLError

        from urllib.parse import urlparse

        parsed = urlparse(url)
        stored_url = url

        if parsed.scheme in ("http", "https"):
            try:
                with urlopen(url, timeout=10) as response:  # nosec B310 - scheme validated above
                    data = yaml.safe_load(response.read()) or {}
            except URLError as e:
                raise ValueError(f"Failed to download marketplace: {e}")
        elif parsed.scheme == "file" or parsed.scheme == "":
            if parsed.scheme == "":
                file_path = Path(url).resolve()
            else:
                file_path = Path(parsed.path)
            if not file_path.exists():
                raise ValueError(f"Marketplace file not found: {file_path}")
            try:
                with open(file_path) as f:
                    data = yaml.safe_load(f) or {}
            except OSError as e:
                raise ValueError(f"Failed to read marketplace file: {e}")
            stored_url = file_path.as_uri()
        else:
            raise ValueError(
                f"Marketplace URL must use http(s) or file/local path, got: {parsed.scheme!r}"
            )

        return cls(
            name=name,
            url=stored_url,
            enabled=True,
            description=data.get("description", ""),
            version=data.get("version", ""),
            modules=data.get("modules", []),
        )

    def validate(self) -> tuple[bool, list[str]]:
        """Validate marketplace structure."""
        errors = []

        if not self.name:
            errors.append("Missing required field: name")
        if not self.url:
            errors.append("Missing required field: url")

        if self.modules and not self.version:
            errors.append("Missing version for marketplace catalog")

        for i, mod in enumerate(self.modules):
            required = ["name", "description", "version", "repository"]
            for field_name in required:
                if field_name not in mod:
                    errors.append(f"Module {i}: missing '{field_name}'")

        return len(errors) == 0, errors

    def to_reference_dict(self) -> dict:
        """Convert to dict for reference file."""
        return {
            "name": self.name,
            "url": self.url,
            "enabled": self.enabled,
        }

    def to_cache_dict(self) -> dict:
        """Convert to dict for cache file."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "url": self.url,
            "enabled": self.enabled,
            "modules": self.modules,
        }


@dataclass(frozen=True)
class ModuleCacheKey:
    """Stable identity for a local module cache copy."""

    module_name: str
    scope: str
    project_path: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "module": self.module_name,
            "scope": self.scope,
            "project_path": self.project_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModuleCacheKey":
        """Create from dictionary."""
        return cls(
            module_name=data.get("module", ""),
            scope=data.get("scope", "project"),
            project_path=data.get("project_path"),
        )


@dataclass(frozen=True)
class InstallationKey:
    """Stable identity for one assistant installation."""

    module_name: str
    assistant: str
    scope: str
    project_path: Optional[str] = None

    @classmethod
    def from_installation(cls, inst: "Installation") -> "InstallationKey":
        """Build a key from an installation record."""
        return cls(
            module_name=inst.module_name,
            assistant=inst.assistant,
            scope=inst.scope,
            project_path=inst.project_path,
        )


@dataclass
class ModuleCache:
    """Represents a local cache copy of a registered module."""

    module_name: str
    scope: str
    path: str
    project_path: Optional[str] = None
    source: Optional[str] = None

    @property
    def key(self) -> ModuleCacheKey:
        """Return this cache's stable key."""
        return ModuleCacheKey(
            module_name=self.module_name,
            scope=self.scope,
            project_path=self.project_path,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        result = {
            "module": self.module_name,
            "scope": self.scope,
            "project_path": self.project_path,
            "path": self.path,
        }
        if self.source:
            result["source"] = self.source
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ModuleCache":
        """Create from dictionary."""
        return cls(
            module_name=data.get("module", ""),
            scope=data.get("scope", "project"),
            project_path=data.get("project_path"),
            path=data.get("path", ""),
            source=data.get("source"),
        )


@dataclass
class RemovalPlan:
    """Registry removal result, including safe cache paths to clean up."""

    removed_installations: list["Installation"] = field(default_factory=list)
    cache_paths_to_remove: list[Path] = field(default_factory=list)


@dataclass
class Installation:
    """Represents an installed module."""

    module_name: str
    assistant: str
    scope: str
    project_path: Optional[str] = None
    version: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    mcps: list[str] = field(default_factory=list)
    skill_sources: dict[str, str] = field(default_factory=dict)
    command_sources: dict[str, str] = field(default_factory=dict)
    agent_sources: dict[str, str] = field(default_factory=dict)
    mcp_sources: dict[str, str] = field(default_factory=dict)
    has_instructions: bool = False
    append_context: Optional[str] = None
    full_install: bool = True
    cache_key: Optional[ModuleCacheKey] = None
    # Legacy v1 field. New registry writes use module_caches/cache_key instead.
    user_symlink_dir: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        result = {
            "module": self.module_name,
            "assistant": self.assistant,
            "scope": self.scope,
            "skills": self.skills,
            "commands": self.commands,
            "agents": self.agents,
            "mcps": self.mcps,
            "has_instructions": self.has_instructions,
        }
        if self.project_path:
            result["project_path"] = self.project_path
        if self.version:
            result["version"] = self.version
        if self.append_context:
            result["append_context"] = self.append_context
        skill_sources = {
            name: source
            for name, source in self.skill_sources.items()
            if name != source
        }
        command_sources = {
            name: source
            for name, source in self.command_sources.items()
            if name != source
        }
        agent_sources = {
            name: source
            for name, source in self.agent_sources.items()
            if name != source
        }
        mcp_sources = {
            name: source for name, source in self.mcp_sources.items() if name != source
        }
        if skill_sources:
            result["skill_sources"] = skill_sources
        if command_sources:
            result["command_sources"] = command_sources
        if agent_sources:
            result["agent_sources"] = agent_sources
        if mcp_sources:
            result["mcp_sources"] = mcp_sources
        # Only emit full_install when False to keep existing YAML clean
        if not self.full_install:
            result["full_install"] = False
        if self.cache_key:
            result["cache_key"] = self.cache_key.to_dict()
        if self.user_symlink_dir and self.cache_key is None:
            result["user_symlink_dir"] = self.user_symlink_dir
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Installation":
        """Create from dictionary."""
        cache_key = None
        if data.get("cache_key"):
            cache_key = ModuleCacheKey.from_dict(data["cache_key"])
        return cls(
            module_name=data.get("module", ""),
            assistant=data.get("assistant", ""),
            scope=data.get("scope", "project"),
            project_path=data.get("project_path"),
            version=data.get("version"),
            skills=data.get("skills", []),
            commands=data.get("commands", []),
            agents=data.get("agents", []),
            mcps=data.get("mcps", []),
            skill_sources=data.get("skill_sources", {}),
            command_sources=data.get("command_sources", {}),
            agent_sources=data.get("agent_sources", {}),
            mcp_sources=data.get("mcp_sources", {}),
            has_instructions=data.get("has_instructions", False),
            append_context=data.get("append_context"),
            full_install=data.get("full_install", True),
            cache_key=cache_key,
            user_symlink_dir=data.get("user_symlink_dir"),
        )


class InstallationRegistry:
    """Manages the installed.yml file."""

    def __init__(self, registry_path: Path):
        self.path = registry_path
        self._installations: list[Installation] = []
        self._module_caches: list[ModuleCache] = []
        self._load()

    def _load(self):
        """Load installations from file."""
        if not self.path.exists():
            self._installations = []
            self._module_caches = []
            return

        with open(self.path, "r") as f:
            data = yaml.safe_load(f) or {}

        version = str(data.get("version", "1.0"))
        if version == "2.0" or "module_caches" in data:
            self._load_v2(data)
        else:
            self._load_v1(data)

    def _load_v2(self, data: dict) -> None:
        """Load v2 registry data."""
        self._module_caches = [
            cache
            for cache in (
                ModuleCache.from_dict(raw) for raw in data.get("module_caches", [])
            )
            if cache.module_name and cache.path
        ]
        self._installations = [
            Installation.from_dict(inst) for inst in data.get("installations", [])
        ]

        # Be forgiving of partially migrated files: attach an installation to
        # its matching cache when the cache exists but the per-install key is
        # missing.
        for inst in self._installations:
            if inst.cache_key is None:
                cache = self._find_cache(
                    ModuleCacheKey(
                        inst.module_name,
                        inst.scope,
                        inst.project_path if inst.scope == "project" else None,
                    )
                )
                if cache:
                    inst.cache_key = cache.key

    def _load_v1(self, data: dict) -> None:
        """Load and normalize legacy v1 registry data into v2 objects."""
        self._installations = []
        self._module_caches = []

        for raw in data.get("installations", []):
            inst = Installation.from_dict(raw)
            cache_path = self._legacy_cache_path(inst)
            if cache_path:
                cache = ModuleCache(
                    module_name=inst.module_name,
                    scope=inst.scope,
                    project_path=inst.project_path if inst.scope == "project" else None,
                    path=str(cache_path),
                )
                self._upsert_cache(cache)
                inst.cache_key = cache.key
            self._installations.append(inst)

    def _legacy_cache_path(self, inst: Installation) -> Path | None:
        """Infer the cache path for legacy records when it is unambiguous."""
        if inst.scope == "project" and inst.project_path:
            return Path(inst.project_path) / ".lola" / "modules" / inst.module_name
        if inst.scope == "user" and inst.user_symlink_dir:
            return Path(inst.user_symlink_dir) / inst.module_name
        return None

    def _save(self):
        """Save installations to file atomically.

        Uses a temporary file and atomic rename to prevent corruption
        if the process is interrupted during write.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "2.0",
            "module_caches": [cache.to_dict() for cache in self._module_caches],
            "installations": [inst.to_dict() for inst in self._installations],
        }

        # Write to a temporary file in the same directory (same filesystem)
        # then atomically replace the target file
        fd, tmp_path_str = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            text=True,
        )
        tmp_path = Path(tmp_path_str)

        try:
            # Write to the temporary file
            with os.fdopen(fd, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

            # Atomically replace the target file
            # On POSIX systems, this is atomic even if target exists
            tmp_path.replace(self.path)
        except Exception:
            # Clean up temporary file on failure
            tmp_path.unlink(missing_ok=True)
            raise

    def _installation_key(self, installation: Installation) -> InstallationKey:
        """Return an installation's stable key."""
        return InstallationKey.from_installation(installation)

    def _cache_key_for(
        self, module_name: str, scope: str, project_path: str | None
    ) -> ModuleCacheKey:
        """Build the cache key for an installation context."""
        return ModuleCacheKey(
            module_name=module_name,
            scope=scope,
            project_path=project_path if scope == "project" else None,
        )

    def _find_cache(self, key: ModuleCacheKey) -> ModuleCache | None:
        """Find a module cache by key."""
        return next((cache for cache in self._module_caches if cache.key == key), None)

    def _upsert_cache(self, cache: ModuleCache) -> None:
        """Add or replace a module cache record."""
        self._module_caches = [
            existing for existing in self._module_caches if existing.key != cache.key
        ]
        self._module_caches.append(cache)

    def add(self, installation: Installation):
        """Add an installation record."""
        self.upsert_installation(installation)

    def upsert_installation(
        self,
        installation: Installation,
        cache_path: Path | None = None,
        source: str | None = None,
    ) -> None:
        """Add or replace an installation and optionally record its cache path."""
        if cache_path is None and installation.cache_key is None:
            cache_path = self.cache_for(
                installation.module_name,
                installation.scope,
                installation.project_path,
            )

        if cache_path is not None:
            cache_key = self._cache_key_for(
                installation.module_name,
                installation.scope,
                installation.project_path,
            )
            installation.cache_key = cache_key
            self._upsert_cache(
                ModuleCache(
                    module_name=installation.module_name,
                    scope=installation.scope,
                    project_path=cache_key.project_path,
                    path=str(cache_path),
                    source=source,
                )
            )

        # Remove any existing installation with same key
        self._installations = [
            inst
            for inst in self._installations
            if not (
                inst.module_name == installation.module_name
                and inst.assistant == installation.assistant
                and inst.scope == installation.scope
                and inst.project_path == installation.project_path
            )
        ]
        self._installations.append(installation)
        self._save()

    def cache_for(
        self,
        module_name: str,
        scope: str,
        project_path: str | None = None,
        current_user_context: str | Path | None = None,
    ) -> Path | None:
        """Return the cache path for a module/scope/location.

        Existing records always win. For new project-scope installs, the cache
        path is derived from the target project. For new user-scope installs,
        callers must provide the current user context; if a legacy user record
        has no cache, this deliberately returns None instead of guessing.
        """
        key = self._cache_key_for(module_name, scope, project_path)
        existing = self._find_cache(key)
        if existing and existing.path:
            return Path(existing.path)

        if scope == "project" and project_path:
            return Path(project_path) / ".lola" / "modules" / module_name
        if scope == "user" and current_user_context is not None:
            return Path(current_user_context) / ".lola" / "modules" / module_name
        return None

    def remaining_installations_for_cache(
        self, cache_key: ModuleCacheKey
    ) -> list[Installation]:
        """Return installations still referencing a cache key."""
        return [inst for inst in self._installations if inst.cache_key == cache_key]

    def remove_installation(self, key: InstallationKey) -> RemovalPlan:
        """Remove one exact installation record."""
        return self.remove_installations([key])

    def remove_installations(self, keys: list[InstallationKey]) -> RemovalPlan:
        """Remove exact installation records and plan safe cache cleanup."""
        key_set = set(keys)
        removed: list[Installation] = []
        kept: list[Installation] = []

        for inst in self._installations:
            if self._installation_key(inst) in key_set:
                removed.append(inst)
            else:
                kept.append(inst)

        self._installations = kept
        plan = RemovalPlan(removed_installations=removed)
        self._append_unreferenced_cache_paths(
            plan, {inst.cache_key for inst in removed if inst.cache_key is not None}
        )
        self._save()
        return plan

    def remove_module(self, module_name: str) -> RemovalPlan:
        """Remove all installation and cache records for a module."""
        removed = [
            inst for inst in self._installations if inst.module_name == module_name
        ]
        self._installations = [
            inst for inst in self._installations if inst.module_name != module_name
        ]
        candidate_keys = {
            cache.key
            for cache in self._module_caches
            if cache.module_name == module_name
        }
        candidate_keys.update(
            inst.cache_key for inst in removed if inst.cache_key is not None
        )

        plan = RemovalPlan(removed_installations=removed)
        self._append_unreferenced_cache_paths(plan, candidate_keys)
        self._save()
        return plan

    def _append_unreferenced_cache_paths(
        self, plan: RemovalPlan, candidate_keys: set[ModuleCacheKey]
    ) -> None:
        """Move cache paths with no remaining references into the removal plan."""
        if not candidate_keys:
            return

        paths: list[Path] = []
        kept_caches: list[ModuleCache] = []
        for cache in self._module_caches:
            if (
                cache.key in candidate_keys
                and not self.remaining_installations_for_cache(cache.key)
            ):
                paths.append(Path(cache.path))
            else:
                kept_caches.append(cache)

        self._module_caches = kept_caches
        seen: set[Path] = set(plan.cache_paths_to_remove)
        for path in paths:
            if path not in seen:
                plan.cache_paths_to_remove.append(path)
                seen.add(path)

    def remove(
        self,
        module_name: str,
        assistant: str | None = None,
        scope: str | None = None,
        project_path: str | None = None,
    ) -> list[Installation]:
        """
        Remove installation records matching the criteria.

        Returns list of removed installations.
        """
        removed = []
        kept = []

        for inst in self._installations:
            matches = inst.module_name == module_name
            if assistant:
                matches = matches and inst.assistant == assistant
            if scope:
                matches = matches and inst.scope == scope
            if project_path:
                matches = matches and inst.project_path == project_path

            if matches:
                removed.append(inst)
            else:
                kept.append(inst)

        self._installations = kept
        plan = RemovalPlan(removed_installations=removed)
        self._append_unreferenced_cache_paths(
            plan, {inst.cache_key for inst in removed if inst.cache_key is not None}
        )
        self._save()
        return removed

    def find(self, module_name: str) -> list[Installation]:
        """Find all installations of a module."""
        return [inst for inst in self._installations if inst.module_name == module_name]

    def all(self) -> list[Installation]:
        """Get all installations."""
        return self._installations.copy()

    def module_caches(self) -> list[ModuleCache]:
        """Get all module cache records."""
        return self._module_caches.copy()
